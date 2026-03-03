from . import Page, Menu, MENU_CONTINUE
from ..krux_settings import t


class Tools(Page):
    """Vault tools menu"""

    def __init__(self, ctx):
        super().__init__(
            ctx,
            Menu(
                ctx,
                [
                    (t("Device Tests"), self.device_tests),
                    (t("Flash Tools"), self.flash_tools),
                ],
            ),
        )
        self.ctx = ctx

    def _flash_hash(self):
        from .flash_tools import FlashHash

        if self.ctx.tc_code_enabled:
            from .tc_code_verification import TCCodeVerification

            tc_code_hash = TCCodeVerification(self.ctx).capture(return_hash=True)
            if not tc_code_hash:
                return MENU_CONTINUE
        else:
            self.flash_error(t("Set a tamper check code first"))
            return MENU_CONTINUE

        FlashHash(self.ctx, tc_code_hash).generate()
        return MENU_CONTINUE

    def flash_tools(self):
        from .fill_flash import FillFlash

        submenu_items = [
            (t("Flash Hash"), self._flash_hash),
            (t("Fill with Random"), lambda: FillFlash(self.ctx).fill_flash_with_camera_entropy()),
        ]
        Menu(self.ctx, submenu_items).run_loop()
        return MENU_CONTINUE

    def device_tests(self):
        from .device_tests import DeviceTests

        DeviceTests(self.ctx).run()
        return MENU_CONTINUE

    def run(self):
        _index, status = self.menu.run_loop()
        return status
