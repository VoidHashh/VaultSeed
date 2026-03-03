import sys
import board
from .. import Page, Menu, MENU_CONTINUE, MENU_EXIT
from ...secret_types import type_label
from ...krux_settings import t
from ...metadata import VERSION


class VaultHome(Page):
    """Main menu for unlocked vault."""

    def __init__(self, ctx):
        menu_items = [
            (t("View Secrets"), self.view_secrets),
            (t("Add Secret"), self.add_secret),
            (t("Settings"), self.settings),
            (t("Tools"), self.tools),
            (t("About"), self.about),
        ]
        super().__init__(ctx, Menu(ctx, menu_items, back_label=t("Lock"), back_status=self.lock))
        self.ctx = ctx

    def run(self):
        _index, status = self.menu.run_loop()
        return status

    def lock(self):
        self.ctx.clear()
        return MENU_EXIT

    def view_secrets(self):
        secrets = self.ctx.vault.manifest.get("secrets", [])
        if not secrets:
            self.flash_text(t("No secrets stored"))
            return MENU_CONTINUE

        items = [
            (
                "{} ({})".format(s.get("label", s["id"]), type_label(s.get("secret_type", "text"))),
                (lambda secret=s: self._open_secret(secret)),
            )
            for s in secrets
        ]
        Menu(self.ctx, items).run_loop()
        return MENU_CONTINUE

    def _open_secret(self, secret_entry):
        from .vault_view import VaultView

        result = VaultView(self.ctx, secret_entry).run()
        try:
            sys.modules.pop("krux.pages.vault_pages.vault_view")
        except KeyError:
            pass
        return result

    def add_secret(self):
        from .vault_add import VaultAdd

        result = VaultAdd(self.ctx).run()
        try:
            sys.modules.pop("krux.pages.vault_pages.vault_add")
        except KeyError:
            pass
        return result

    def settings(self):
        from ..settings_page import SettingsPage

        SettingsPage(self.ctx).settings()
        return MENU_CONTINUE

    def tools(self):
        from ..tools import Tools

        Tools(self.ctx).run()
        return MENU_CONTINUE

    def about(self):
        count = len(self.ctx.vault.manifest.get("secrets", []))
        self.ctx.display.clear()
        self.ctx.display.draw_hcentered_text(
            "Vault v{}\nSecrets: {}\nDevice: {}".format(
                VERSION,
                count,
                board.config["type"],
            )
        )
        self.ctx.input.wait_for_button()
        return MENU_CONTINUE
