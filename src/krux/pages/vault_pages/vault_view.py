import gc
import time
from .. import Page, Menu, MENU_CONTINUE, MENU_EXIT
from ...vault import VaultManager
from ...secret_types import type_label
from ...krux_settings import t


class VaultView(Page):
    """View/manage one stored secret."""

    def __init__(self, ctx, secret_entry):
        super().__init__(
            ctx,
            Menu(
                ctx,
                [
                    (t("Reveal Secret"), self.reveal_secret),
                    (t("Show as QR"), self.show_as_qr),
                    (t("Delete"), self.delete_secret),
                ],
            ),
        )
        self.secret_entry = secret_entry
        self.vm = VaultManager()

    def run(self):
        self._show_overview()
        _index, status = self.menu.run_loop()
        return status

    def _show_overview(self):
        created = self.secret_entry.get("created_at", 0)
        try:
            tm = time.localtime(created)
            created_txt = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}".format(
                tm[0], tm[1], tm[2], tm[3], tm[4]
            )
        except:
            created_txt = str(created)

        txt = (
            "Label: {}\nType: {}\nCreated: {}\nHash: {}"
            .format(
                self.secret_entry.get("label", ""),
                type_label(self.secret_entry.get("secret_type", "text")),
                created_txt,
                self.secret_entry.get("hash_preview", ""),
            )
        )
        self.ctx.display.clear()
        self.ctx.display.draw_hcentered_text(txt)
        time.sleep_ms(700)

    def reveal_secret(self):
        if not self.prompt(t("Reveal secret on screen?"), self.ctx.display.height() // 2):
            return MENU_CONTINUE

        plaintext = self.vm.load_secret(self.ctx.vault.cipher, self.secret_entry["id"])
        if plaintext is None:
            self.flash_error(t("Failed to decrypt"))
            return MENU_CONTINUE

        try:
            text = plaintext.decode()
        except:
            text = plaintext.hex()

        for remaining in range(30, 0, -1):
            self.ctx.display.clear()
            self.ctx.display.draw_hcentered_text(
                "{}\n\nAuto-hide in: {}s".format(text, remaining)
            )
            if self.ctx.input.wait_for_button(block=False, wait_duration=1000) is not None:
                break

        self.ctx.display.clear()
        del plaintext
        gc.collect()
        return MENU_CONTINUE

    def show_as_qr(self):
        plaintext = self.vm.load_secret(self.ctx.vault.cipher, self.secret_entry["id"])
        if plaintext is None:
            self.flash_error(t("Failed to decrypt"))
            return MENU_CONTINUE

        try:
            payload = plaintext.decode()
        except:
            payload = plaintext

        self.display_qr_codes(payload, title=self.secret_entry.get("label", t("Secret")))
        del plaintext
        gc.collect()
        return MENU_CONTINUE

    def delete_secret(self):
        label = self.secret_entry.get("label", self.secret_entry["id"])
        prompt = "Delete {}? This cannot be undone!".format(label)
        if not self.prompt(prompt, self.ctx.display.height() // 2):
            return MENU_CONTINUE

        try:
            self.vm.delete_secret(self.secret_entry["id"])
            manifest = self.vm.remove_from_manifest(
                self.ctx.vault.manifest, self.secret_entry["id"]
            )
            self.vm.save_manifest(self.ctx.vault.cipher, manifest)
            self.ctx.vault.manifest = manifest
            self.flash_text(t("Secret deleted"))
            return MENU_EXIT
        except Exception as e:
            self.flash_error(t("Delete failed") + "\n" + repr(e))
            return MENU_CONTINUE
