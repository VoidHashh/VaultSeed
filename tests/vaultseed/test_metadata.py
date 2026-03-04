from krux import metadata


def test_metadata_fields():
    assert isinstance(metadata.VERSION, str)
    assert hasattr(metadata, "SIGNER_PUBKEY")
