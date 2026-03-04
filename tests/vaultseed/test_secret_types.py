from krux.secret_types import detect_secret_type, type_label, type_warning


def test_detect_hex_32():
    assert detect_secret_type("a" * 32) == "hex"


def test_detect_hex_64():
    assert detect_secret_type("A" * 64) == "hex"


def test_detect_nsec():
    text = "nsec1" + ("q" * 58)
    assert detect_secret_type(text) == "nsec"


def test_detect_npub():
    text = "npub1" + ("q" * 58)
    assert detect_secret_type(text) == "npub"


def test_detect_text_default():
    assert detect_secret_type("not-a-secret-type") == "text"


def test_type_labels_and_warnings():
    assert type_label("bip39-12") == "BIP39 (12 words)"
    assert type_label("unknown") == "Text/Password"
    assert type_warning("npub") == "This is a PUBLIC key, not private. Store anyway?"
    assert type_warning("text") is None
