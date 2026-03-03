"""Secret type detection helpers."""

from .bip39 import k_mnemonic_is_valid
from embit.wordlists.bip39 import WORDLIST

BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
HEX_CHARS = "0123456789abcdefABCDEF"


def detect_secret_type(text):
    """Detect secret type from plaintext text."""
    if text is None:
        return "text"
    text = text.strip()
    if not text:
        return "text"

    words = text.split()
    if len(words) in (12, 24):
        if all(word in WORDLIST for word in words):
            if k_mnemonic_is_valid(text):
                return "bip39-{}".format(len(words))
            return "bip39-invalid"

    if text.startswith("nsec1") and len(text) >= 63:
        data = text[5:]
        if data and all(ch in BECH32_CHARSET for ch in data):
            return "nsec"

    if text.startswith("npub1") and len(text) >= 63:
        data = text[5:]
        if data and all(ch in BECH32_CHARSET for ch in data):
            return "npub"

    if len(text) in (32, 64) and all(ch in HEX_CHARS for ch in text):
        return "hex"

    return "text"


def type_label(secret_type):
    """Return UI label for a secret type id."""
    labels = {
        "bip39-12": "BIP39 (12 words)",
        "bip39-24": "BIP39 (24 words)",
        "bip39-invalid": "BIP39 (bad checksum)",
        "nsec": "Nostr nsec",
        "npub": "Nostr npub (public!)",
        "hex": "Hex key",
        "text": "Text/Password",
    }
    return labels.get(secret_type, "Text/Password")


def type_warning(secret_type):
    """Return warning text for risky/invalid secret types."""
    warnings = {
        "npub": "This is a PUBLIC key, not private. Store anyway?",
        "bip39-invalid": "Checksum is invalid. This mnemonic may have errors.",
    }
    return warnings.get(secret_type)
