from . import create_ctx


def test_load_file_with_no_sd(m5stickv, mocker):
    from krux.pages.utils import Utils

    mocker.patch(
        "krux.sd_card.SDHandler.dir_exists",
        mocker.MagicMock(return_value=False),
    )
    ctx = create_ctx(mocker, None)
    utils = Utils(ctx)
    file_name, data = utils.load_file(prompt=False)

    assert file_name == ""
    assert data is None
