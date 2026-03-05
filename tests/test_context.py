def mock_modules(mocker):
    mocker.patch("krux.context.display", new=mocker.MagicMock())
    mocker.patch("krux.context.Camera", new=mocker.MagicMock())
    mocker.patch("krux.context.Light", new=mocker.MagicMock())
    mocker.patch("krux.context.Input", new=mocker.MagicMock())


def test_init(mocker, m5stickv):
    mock_modules(mocker)
    from krux.context import Context
    c = Context()
    assert isinstance(c, Context)
    assert c.vault is None


def test_clear(mocker, m5stickv):
    mock_modules(mocker)
    from krux.context import Context, VaultState
    c = Context()
    c.vault = VaultState(cipher="fake", manifest={"secrets": []}, version=20, iterations=100000)
    c.clear()
    assert c.vault is None


def test_is_unlocked(mocker, m5stickv):
    mock_modules(mocker)
    from krux.context import Context, VaultState
    c = Context()
    assert c.is_unlocked() == False
    c.vault = VaultState(cipher=None, manifest={"secrets": []}, version=20, iterations=100000)
    assert c.is_unlocked() == False
    c.vault = VaultState(cipher="fake_cipher", manifest={"secrets": []}, version=20, iterations=100000)
    assert c.is_unlocked() == True


def test_is_logged_in_alias(mocker, m5stickv):
    mock_modules(mocker)
    from krux.context import Context, VaultState
    c = Context()
    assert c.is_logged_in() == False
    c.vault = VaultState(cipher="fake_cipher", manifest={"secrets": []}, version=20, iterations=100000)
    assert c.is_logged_in() == True
