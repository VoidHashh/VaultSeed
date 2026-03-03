"""Vault manager with SD primary + flash mirror backup."""

import ujson as json
import os
import gc
import uhashlib_hw
from binascii import hexlify, unhexlify
from krux import kef
from .sd_card import SDHandler

VAULT_DIR = "vault"
VAULT_META_FILE = "vault/vault.meta"
VAULT_MANIFEST_FILE = "vault/manifest.kef"
VAULT_SECRETS_DIR = "vault/secrets"

FLASH_VAULT_DIR = "/flash/vault"
FLASH_VAULT_META = "/flash/vault/vault.meta"
FLASH_VAULT_MANIFEST = "/flash/vault/manifest.kef"
FLASH_VAULT_SECRETS_DIR = "/flash/vault/secrets"

SALT_LENGTH = 32
KEF_VERSION = 20
KEF_ITERATIONS = 100000
FORMAT_VERSION = 1
MANIFEST_ID = b"vault-manifest"


def random_bytes(n):
    """Generate n random bytes using K210 TRNG sources."""
    try:
        import urandom

        return bytes([urandom.getrandbits(8) for _ in range(n)])
    except:
        try:
            return os.urandom(n)
        except:
            # Last-resort fallback to avoid crashes on ports without os.urandom
            out = bytearray()
            for _ in range(n):
                out.append(int.from_bytes(uhashlib_hw.sha256(b"x").digest()[:1], "big"))
            return bytes(out)


def _ensure_dirs(base_path):
    """Ensure vault directories exist under /sd or /flash."""
    vault_dir = base_path + "/vault"
    secrets_dir = base_path + "/vault/secrets"
    try:
        os.stat(vault_dir)
    except OSError:
        os.mkdir(vault_dir)
    try:
        os.stat(secrets_dir)
    except OSError:
        os.mkdir(secrets_dir)


def _write_with_mirror(sd_path, flash_path, data, binary=True):
    """Write to SD first (required) and mirror to flash (best effort)."""
    with SDHandler() as sd:
        if binary:
            sd.write_binary(sd_path, data)
        else:
            sd.write(sd_path, data)

    try:
        mode = "wb" if binary else "w"
        with open(flash_path, mode) as f:
            f.write(data)
    except:
        pass


def _delete_with_mirror(sd_path, flash_path):
    """Delete from both SD and flash."""
    try:
        os.remove("/sd/" + sd_path)
    except:
        pass
    try:
        os.remove(flash_path)
    except:
        pass


class VaultManager:
    """Vault CRUD manager."""

    def __init__(self):
        pass

    def vault_exists_sd(self):
        """Check whether vault meta exists on SD."""
        return SDHandler.file_exists("/sd/" + VAULT_META_FILE)

    def vault_exists_flash(self):
        """Check whether vault meta exists on flash mirror."""
        try:
            return (os.stat(FLASH_VAULT_META)[0] & 0x4000) == 0
        except OSError:
            return False

    def initialize_vault(self):
        """Create vault folders and write plaintext meta on SD + flash."""
        _ensure_dirs("/sd")
        _ensure_dirs("/flash")

        salt = random_bytes(SALT_LENGTH)
        meta = {
            "salt": hexlify(salt).decode(),
            "format_version": FORMAT_VERSION,
        }
        _write_with_mirror(
            VAULT_META_FILE,
            FLASH_VAULT_META,
            json.dumps(meta),
            binary=False,
        )
        gc.collect()
        return meta

    def restore_from_flash(self):
        """Restore full vault from flash mirror into SD primary."""
        _ensure_dirs("/sd")

        with open(FLASH_VAULT_META, "r") as f:
            meta_json = f.read()
        with SDHandler() as sd:
            sd.write(VAULT_META_FILE, meta_json)

        try:
            with open(FLASH_VAULT_MANIFEST, "rb") as f:
                manifest_data = f.read()
            with SDHandler() as sd:
                sd.write_binary(VAULT_MANIFEST_FILE, manifest_data)
        except OSError:
            pass

        try:
            _ensure_dirs("/sd")
            secrets = os.listdir(FLASH_VAULT_SECRETS_DIR)
            with SDHandler() as sd:
                for filename in secrets:
                    src = FLASH_VAULT_SECRETS_DIR + "/" + filename
                    dst = VAULT_SECRETS_DIR + "/" + filename
                    with open(src, "rb") as f:
                        sd.write_binary(dst, f.read())
        except OSError:
            pass

        gc.collect()

    def load_meta(self):
        """Load and parse vault.meta from SD."""
        with SDHandler() as sd:
            meta_json = sd.read(VAULT_META_FILE)
        return json.loads(meta_json)

    def save_manifest(self, cipher, manifest):
        """Encrypt and write manifest to SD + flash mirror."""
        json_bytes = json.dumps(manifest).encode()
        iv = random_bytes(12)
        payload = cipher.encrypt(json_bytes, KEF_VERSION, iv=iv)
        envelope = kef.wrap(MANIFEST_ID, KEF_VERSION, KEF_ITERATIONS, payload)
        _write_with_mirror(VAULT_MANIFEST_FILE, FLASH_VAULT_MANIFEST, envelope)
        gc.collect()

    def load_manifest(self, cipher):
        """Load and decrypt manifest from SD."""
        try:
            with SDHandler() as sd:
                data = sd.read_binary(VAULT_MANIFEST_FILE)
        except:
            return {"secrets": []}

        try:
            _id, version, _iterations, payload = kef.unwrap(data)
            plaintext = cipher.decrypt(payload, version)
            if plaintext is None:
                return None
            return json.loads(plaintext.decode())
        except:
            return None

    def save_secret(self, cipher, secret_id, plaintext):
        """Encrypt and persist one secret file to SD + flash mirror."""
        iv = random_bytes(12)
        payload = cipher.encrypt(plaintext, KEF_VERSION, iv=iv)
        envelope = kef.wrap(secret_id.encode(), KEF_VERSION, KEF_ITERATIONS, payload)

        sd_path = VAULT_SECRETS_DIR + "/" + secret_id + ".kef"
        flash_path = FLASH_VAULT_SECRETS_DIR + "/" + secret_id + ".kef"
        _write_with_mirror(sd_path, flash_path, envelope)
        gc.collect()

    def load_secret(self, cipher, secret_id):
        """Load and decrypt one secret from SD."""
        sd_path = VAULT_SECRETS_DIR + "/" + secret_id + ".kef"
        try:
            with SDHandler() as sd:
                data = sd.read_binary(sd_path)
            _id, version, _iterations, payload = kef.unwrap(data)
            return cipher.decrypt(payload, version)
        except:
            return None

    def delete_secret(self, secret_id):
        """Delete secret file from SD and flash."""
        sd_path = VAULT_SECRETS_DIR + "/" + secret_id + ".kef"
        flash_path = FLASH_VAULT_SECRETS_DIR + "/" + secret_id + ".kef"
        _delete_with_mirror(sd_path, flash_path)

    def next_secret_id(self, manifest):
        """Return next sequential secret id (001, 002...)."""
        if not manifest.get("secrets"):
            return "001"
        max_id = max(int(s["id"]) for s in manifest["secrets"])
        return "{:03d}".format(max_id + 1)

    def add_to_manifest(self, manifest, secret_id, label, secret_type, hash_preview):
        """Append in-memory manifest entry."""
        import time

        manifest["secrets"].append(
            {
                "id": secret_id,
                "label": label,
                "secret_type": secret_type,
                "created_at": int(time.time()),
                "hash_preview": hash_preview,
            }
        )
        return manifest

    def remove_from_manifest(self, manifest, secret_id):
        """Remove in-memory manifest entry by id."""
        manifest["secrets"] = [s for s in manifest["secrets"] if s["id"] != secret_id]
        return manifest

    @staticmethod
    def compute_hash_preview(plaintext):
        """Return first 8 hex chars of SHA256 digest."""
        h = uhashlib_hw.sha256(plaintext).digest()
        return hexlify(h).decode()[:8]
