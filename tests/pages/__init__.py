from ..shared_mocks import mock_context


def create_ctx(mocker, btn_seq, touch_seq=None):
    """Helper to create mocked context obj"""
    from krux.context import Context

    ctx: Context = mock_context(mocker)
    ctx.power_manager.battery_charge_remaining.return_value = 1
    ctx.input.wait_for_button = mocker.MagicMock(side_effect=btn_seq)
    ctx.input.wait_for_fastnav_button = ctx.input.wait_for_button
    ctx.display.qr_offset = mocker.MagicMock(return_value=250)

    if touch_seq:
        ctx.input.touch = mocker.MagicMock(
            current_index=mocker.MagicMock(side_effect=touch_seq)
        )
    return ctx
