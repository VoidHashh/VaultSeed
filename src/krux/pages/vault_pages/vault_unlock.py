import gc
from binascii import unhexlify
from krux import kef
from .. import (
    Page,
    LETTERS,
    UPPERCASE_LETTERS,
    NUM_SPECIAL_1,
    NUM_SPECIAL_2,
    MENU_CONTINUE,
    MENU_EXIT,
    ESC_KEY,
)
from ...vault import VaultManager, KEF_VERSION, KEF_ITERATIONS
from ...context import VaultState
from ...krux_settings import t
from ...display import BOTTOM_PROMPT_LINE
from ...sd_card import SDHandler


class VaultUnlock(Page):
    """Vault unlock/create flow shown at boot."""

    def __init__(self, ctx):
        super().__init__(ctx, None)
        self.vm = VaultManager()

    def run(self):
        while True:
            if not self._check_sd_card():
                return False

            if not self.vm.vault_exists_sd():
                if self.vm.vault_exists_flash():
                    self.ctx.display.clear()
                    if self.prompt(
                        t("Vault found in backup. Restore to SD card?"),
                        self.ctx.display.height() // 2,
                    ):
                        try:
                            self.vm.restore_from_flash()
                            self.flash_text(t("Vault restored"))
                        except Exception as e:
                            self.flash_error(t("Restore failed") + "\n" + repr(e))
                            continue
                    else:
                        return False
                else:
                    self.ctx.display.clear()
                    if self.prompt(
                        t("Create new vault?"), self.ctx.display.height() // 2
                    ):
                        return self._create_new_vault()
                    return False

            if self.vm.vault_exists_sd():
                return self._unlock_existing_vault()

    def _check_sd_card(self):
        """Check SD presence and prompt retry when absent."""
        try:
            with SDHandler():
                return True
        except:
            self.ctx.display.clear()
            self.ctx.display.draw_centered_text(t("Insert SD card"))
            return self.prompt(t("Retry?"), BOTTOM_PROMPT_LINE)

    def _get_passphrase(self, confirm=False):
        """Collect passphrase once, optionally with confirmation."""
        from ..encryption_ui import EncryptionKey

        first = self.capture_from_keypad(
            t("Passphrase"),
            [LETTERS, UPPERCASE_LETTERS, NUM_SPECIAL_1, NUM_SPECIAL_2],
        )
        if first in (ESC_KEY, ""):
            return None

        strength = EncryptionKey(self.ctx).key_strength(first)
        self.flash_text(t("Strength") + ": " + strength)

        if not confirm:
            return first

        second = self.capture_from_keypad(
            t("Confirm passphrase"),
            [LETTERS, UPPERCASE_LETTERS, NUM_SPECIAL_1, NUM_SPECIAL_2],
        )
        if second in (ESC_KEY, ""):
            return None
        if first != second:
            self.flash_error(t("Passphrases do not match"))
            return ""
        return first

    def _derive_key_with_ui(self, passphrase, salt_bytes):
        """Create KEF cipher with visible progress hint."""
        self.ctx.display.clear()
        self.ctx.display.draw_centered_text(t("Deriving key..."))
        cipher = kef.Cipher(passphrase, salt_bytes, KEF_ITERATIONS)
        gc.collect()
        return cipher

    def _create_new_vault(self):
        """Initialize new vault and unlock it."""
        try:
            meta = self.vm.initialize_vault()
        except Exception as e:
            self.flash_error(t("Failed to initialize vault") + "\n" + repr(e))
            return False

        while True:
            passphrase = self._get_passphrase(confirm=True)
            if passphrase == "":
                continue
            if passphrase is None:
                return False

            try:
                salt_bytes = unhexlify(meta["salt"])
                cipher = self._derive_key_with_ui(passphrase, salt_bytes)
                manifest = {"secrets": []}
                self.vm.save_manifest(cipher, manifest)
                self.ctx.vault = VaultState(
                    cipher,
                    manifest,
                    KEF_VERSION,
                    KEF_ITERATIONS,
                )
                gc.collect()
                return True
            except Exception as e:
                self.flash_error(t("Create failed") + "\n" + repr(e))
                return False

    def _unlock_existing_vault(self):
        """Unlock an existing vault from SD."""
        try:
            meta = self.vm.load_meta()
            salt_bytes = unhexlify(meta["salt"])
        except Exception as e:
            self.flash_error(t("Invalid vault metadata") + "\n" + repr(e))
            return False

        attempts = 0
        while attempts < 5:
            passphrase = self._get_passphrase(confirm=False)
            if passphrase is None:
                return False

            cipher = self._derive_key_with_ui(passphrase, salt_bytes)
            manifest = self.vm.load_manifest(cipher)
            if manifest is None:
                attempts += 1
                self.flash_error(t("Wrong passphrase"))
                continue

            self.ctx.vault = VaultState(cipher, manifest, KEF_VERSION, KEF_ITERATIONS)
            gc.collect()
            return True

        self.flash_error(t("Too many attempts"))
        return False
