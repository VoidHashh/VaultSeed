from .. import (
    Page,
    Menu,
    MENU_CONTINUE,
    MENU_EXIT,
    ESC_KEY,
    LETTERS,
    UPPERCASE_LETTERS,
    NUM_SPECIAL_1,
    NUM_SPECIAL_2,
)
from ...vault import VaultManager
from ...secret_types import detect_secret_type, type_label, type_warning
from ...krux_settings import t


class VaultAdd(Page):
    """Add new secret flow."""

    def __init__(self, ctx):
        super().__init__(ctx, None)
        self.vm = VaultManager()
        self._captured_text = None

    def _menu_scan(self):
        self._captured_text = self._scan_qr()
        return MENU_EXIT

    def _menu_type(self):
        self._captured_text = self._type_text()
        return MENU_EXIT

    def run(self):
        self._captured_text = None
        Menu(
            self.ctx,
            [
                (t("Scan QR Code"), self._menu_scan),
                (t("Type Text"), self._menu_type),
            ],
        ).run_loop()

        text = self._captured_text
        if text in (None, "", ESC_KEY):
            return MENU_CONTINUE

        secret_type = detect_secret_type(text)
        warning = type_warning(secret_type)
        if warning:
            self.ctx.display.clear()
            self.ctx.display.draw_hcentered_text(warning)
            if not self.prompt(t("Store anyway?"), self.ctx.display.height() // 2):
                return MENU_CONTINUE

        label = self._ask_label()
        if label in (None, "", ESC_KEY):
            return MENU_CONTINUE

        preview = text if len(text) <= 20 else text[:20] + "..."
        summary = "Type: {}\nLabel: {}\nPreview: {}\n\nStore this secret?".format(
            type_label(secret_type),
            label,
            preview,
        )
        self.ctx.display.clear()
        self.ctx.display.draw_hcentered_text(summary)
        if not self.prompt("", self.ctx.display.height() // 2):
            return MENU_CONTINUE

        try:
            plaintext = text.encode()
            hash_preview = self.vm.compute_hash_preview(plaintext)
            secret_id = self.vm.next_secret_id(self.ctx.vault.manifest)
            self.vm.save_secret(self.ctx.vault.cipher, secret_id, plaintext)
            manifest = self.vm.add_to_manifest(
                self.ctx.vault.manifest,
                secret_id,
                label,
                secret_type,
                hash_preview,
            )
            self.vm.save_manifest(self.ctx.vault.cipher, manifest)
            self.ctx.vault.manifest = manifest
            self.flash_text(t("Secret stored!"))
        except Exception as e:
            self.flash_error(t("Failed to store secret") + "\n" + repr(e))
        return MENU_CONTINUE

    def _scan_qr(self):
        from ..qr_capture import QRCodeCapture

        data, _fmt = QRCodeCapture(self.ctx).qr_capture_loop()
        if data is None:
            return None
        if isinstance(data, bytes):
            try:
                return data.decode()
            except:
                return data.hex()
        return str(data)

    def _type_text(self):
        text = self.capture_from_keypad(
            t("Secret"),
            [LETTERS, UPPERCASE_LETTERS, NUM_SPECIAL_1, NUM_SPECIAL_2],
        )
        if text == ESC_KEY:
            return None
        return text

    def _ask_label(self):
        label = self.capture_from_keypad(
            t("Label"),
            [LETTERS, UPPERCASE_LETTERS, NUM_SPECIAL_1, NUM_SPECIAL_2],
        )
        if label == ESC_KEY:
            return None
        return label[:20]
