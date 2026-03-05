import pytest


@pytest.fixture
def tdata(mocker):
    from collections import namedtuple

    TEST_DATA_B58 = "UUucvki6KWyS35DhetbWPw1DiaccbHKywScF96E8VUwEnN1gss947UasRfkNxtrkzCeHziHyMCuoiQ2mSYsbYXuV3YwYBZwFh1c6xtBAEK1aDgPwMgqf74xTzf3m4KH4iUU5nHTqroDpoRZR59meafTCUBChZ5NJ8MoUdKE6avyYdSm5kUb4npmFpMpJ9S3qd2RedHMoQFRiXK3jwdH81emAEsFYSW3Kb7caPcWjkza4S4EEWWbaggofGFmxE5gNNg4A4LNC2ZUGLsALZffNvg3yh3qg6rFxhkiyzWc44kx9Khp6Evm1j4Njh8kjifkngLTPFtX3uWNLAB1XrvpPMx6kkkhr7RnFVrA4JsDp5BwVGAXBoSBLTqweFevZ5"
    TEST_DATA_BBQR = b'psbt\xff\x01\x00R\x02\x00\x00\x00\x01\x9a\x9b\xe1\xca)\x10\\\x97t<\x0f\xd1\xeey\xc0\xe6\r"\x8aa\xc8\xec\xbft\xf9\xe7\xcf\xfa\x01\x19\x0c{\x01\x00\x00\x00\x00\xfd\xff\xff\xff\x01!&\x00\x00\x00\x00\x00\x00\x16\x00\x14\xae\xcd\x1e\xdc>\xffe\xaa \x9d\x02\x15\xe7=p\x90]\xc1hlX\x0b+\x00'

    TEST_PARTS_FORMAT_NONE = [TEST_DATA_B58]
    TEST_PARTS_FORMAT_PMOFN = [
        "p2of3 4iUU5nHTqroDpoRZR59meafTCUBChZ5NJ8MoUdKE6avyYdSm5kUb4npmFpMpJ9S3qd2RedHMoQFRiXK3jwdH81emAEsFYSW3Kb7caPcWjkza4S4EEWWbaggofGFmxE5",
        "p1of3 UUucvki6KWyS35DhetbWPw1DiaccbHKywScF96E8VUwEnN1gss947UasRfkNxtrkzCeHziHyMCuoiQ2mSYsbYXuV3YwYBZwFh1c6xtBAEK1aDgPwMgqf74xTzf3m4KH",
        "p3of3 gNNg4A4LNC2ZUGLsALZffNvg3yh3qg6rFxhkiyzWc44kx9Khp6Evm1j4Njh8kjifkngLTPFtX3uWNLAB1XrvpPMx6kkkhr7RnFVrA4JsDp5BwVGAXBoSBLTqweFevZ5",
    ]

    return namedtuple("TestData", ["TEST_DATA_B58", "TEST_DATA_BBQR", "TEST_PARTS_FORMAT_NONE", "TEST_PARTS_FORMAT_PMOFN"])(
        TEST_DATA_B58, TEST_DATA_BBQR, TEST_PARTS_FORMAT_NONE, TEST_PARTS_FORMAT_PMOFN,
    )


def test_init(mocker, m5stickv):
    from krux.qr import QRPartParser
    parser = QRPartParser()
    assert isinstance(parser, QRPartParser)
    assert parser.parts == {}
    assert parser.total == -1
    assert parser.format is None


def test_parser(mocker, m5stickv, tdata):
    from krux.qr import QRPartParser, FORMAT_NONE, FORMAT_PMOFN

    cases = [
        (FORMAT_NONE, tdata.TEST_PARTS_FORMAT_NONE),
        (FORMAT_PMOFN, tdata.TEST_PARTS_FORMAT_PMOFN),
    ]
    for fmt, parts in cases:
        parser = QRPartParser()
        for i, part in enumerate(parts):
            parser.parse(part)
            assert parser.format == fmt
            assert parser.total_count() == len(parts)
            assert parser.parsed_count() == i + 1
            if i < len(parts) - 1:
                assert not parser.is_complete()
        assert parser.is_complete()
        res = parser.result()
        assert isinstance(res, str)
        assert res == tdata.TEST_DATA_B58


def test_detect_plaintext_qr(mocker, m5stickv):
    from krux.qr import detect_format
    detect_format("process swim repair fit artist rebuild remove vanish city opinion hawk coconut")


def test_find_min_num_parts(m5stickv):
    from krux.qr import find_min_num_parts
    with pytest.raises(ValueError) as raised_ex:
        find_min_num_parts("", 10, "format unknown")
    assert raised_ex.type is ValueError
    assert raised_ex.value.args[0] == "Invalid format type"
