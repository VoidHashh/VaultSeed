# The MIT License (MIT)

# Copyright (c) 2021-2024 Krux contributors

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import time
from binascii import hexlify
from ..display import DEFAULT_PADDING, FONT_HEIGHT, BOTTOM_PROMPT_LINE
from ..krux_settings import t, Settings
from ..encryption import QR_CODE_ITER_MULTIPLE
from krux import kef
from ..themes import theme
from . import (
    Page,
    Menu,
    MENU_CONTINUE,
    ESC_KEY,
    LETTERS,
    UPPERCASE_LETTERS,
    NUM_SPECIAL_1,
    NUM_SPECIAL_2,
    DIGITS,
)

# Override constants for KEF envelope operations
OVERRIDE_ITERATIONS = 1
OVERRIDE_VERSION = 2
OVERRIDE_MODE = 3
OVERRIDE_LABEL = 4

ENCRYPTION_KEY_MAX_LEN = 200


def decrypt_kef(ctx, data):
    """finds kef-envelope and returns data fully decrypted, else ValueError"""
    from binascii import unhexlify
    from krux.baseconv import base_decode, hint_encodings

    # nothing to decrypt or declined raises ValueError here,
    # so callers can `except ValueError: pass`, then treat original data.
    # If user decides to decrypt and fails with wrong key, then
    # `KeyError("Failed to decrypt")` raised by `KEFEnvelope.unseal_ui()`
    # will bubble up to caller.
    err = "Not decrypted"  # intentionally vague

    # if data is str, assume encoded, look for kef envelope
    kef_envelope = None
    if isinstance(data, str):
        encodings = hint_encodings(data)
        for encoding in encodings:
            as_bytes = None
            if encoding in ("hex", "HEX"):
                try:
                    as_bytes = unhexlify(data)
                except:
                    continue
            elif encoding == 32:
                try:
                    as_bytes = base_decode(data, 32)
                except:
                    continue
            elif encoding == 64:
                try:
                    as_bytes = base_decode(data, 64)
                except:
                    continue
            elif encoding == 43:
                try:
                    as_bytes = base_decode(data, 43)
                except:
                    continue

            if as_bytes:
                kef_envelope = KEFEnvelope(ctx)
                if kef_envelope.parse(as_bytes):
                    break
                kef_envelope = None
                del as_bytes

    # kef_envelope may already be parsed, else do so or fail early
    if kef_envelope is None:
        if not isinstance(data, bytes):
            raise ValueError(err)

        kef_envelope = KEFEnvelope(ctx)
        if not kef_envelope.parse(data):
            raise ValueError(err)

    # unpack as many kef_envelopes as there may be
    while True:
        data = kef_envelope.unseal_ui()
        if data is None:
            # fail if not unsealed
            raise ValueError(err)
        # we may have unsealed another envelope
        kef_envelope = KEFEnvelope(ctx)
        if not kef_envelope.parse(data):
            return data
    raise ValueError(err)


def prompt_for_text_update(
    ctx,
    dflt_value,
    dflt_prompt=None,
    dflt_affirm=True,
    prompt_highlight_prefix="",
    title=None,
    keypads=None,
    esc_prompt=False,
):
    """Clears screen, prompts question, allows for keypad input"""
    if dflt_value:
        if dflt_prompt:
            dflt_prompt += " " + dflt_value
        else:
            dflt_prompt = t("Use current value?") + " " + dflt_value
    ctx.display.clear()
    if dflt_value and dflt_prompt:
        ctx.display.draw_centered_text(
            dflt_prompt, highlight_prefix=prompt_highlight_prefix
        )
        dflt_answer = Page(ctx).prompt("", BOTTOM_PROMPT_LINE)
        if dflt_affirm == dflt_answer:
            return dflt_value
    if not isinstance(keypads, list) or keypads is None:
        keypads = [LETTERS, UPPERCASE_LETTERS, NUM_SPECIAL_1, NUM_SPECIAL_2]
    value = Page(ctx).capture_from_keypad(
        title, keypads, starting_buffer=dflt_value, esc_prompt=esc_prompt
    )
    if isinstance(value, str):
        return value
    return dflt_value


class KEFEnvelope(Page):
    """UI to handle KEF-Encryption-Format Envelopes"""

    def __init__(self, ctx):
        super().__init__(ctx, None)
        self.ctx = ctx
        self.__key = None
        self.__iv = None
        self.label = None
        encryption_settings = getattr(Settings(), "encryption", None)
        self.iterations = (
            encryption_settings.pbkdf2_iterations
            if encryption_settings and hasattr(encryption_settings, "pbkdf2_iterations")
            else 100000
        )
        max_delta = self.iterations // 10
        self.iterations += int(time.ticks_ms()) % max_delta
        self.mode_name = (
            encryption_settings.version
            if encryption_settings and hasattr(encryption_settings, "version")
            else "AES-GCM"
        )
        self.mode = kef.MODE_NUMBERS[self.mode_name]
        self.iv_len = kef.MODE_IVS.get(self.mode, 0)
        self.version = None
        self.version_name = None
        self.ciphertext = None

    def parse(self, kef_envelope):
        """parses envelope, from kef.wrap()"""
        if self.ciphertext is not None:
            raise ValueError("KEF Envelope already parsed")
        try:
            self.label, self.version, self.iterations, self.ciphertext = kef.unwrap(
                kef_envelope
            )
        except:
            return False
        self.version_name = kef.VERSIONS[self.version]["name"]
        self.mode = kef.VERSIONS[self.version]["mode"]
        self.mode_name = [k for k, v in kef.MODE_NUMBERS.items() if v == self.mode][0]
        return True

    def input_key_ui(self, creating=True):
        """calls ui to gather master key"""
        ui = EncryptionKey(self.ctx)
        self.__key = ui.encryption_key(creating)
        return bool(self.__key)

    def input_mode_ui(self):
        """implements ui to allow user to select KEF mode-of-operation"""
        self.ctx.display.clear()
        self.ctx.display.draw_centered_text(
            t("Use default Mode?") + " " + self.mode_name, highlight_prefix="?"
        )
        if self.prompt("", BOTTOM_PROMPT_LINE):
            return True
        menu_items = [(k, v) for k, v in kef.MODE_NUMBERS.items() if v is not None]
        idx, _ = Menu(
            self.ctx, [(x[0], lambda: None) for x in menu_items], back_label=None
        ).run_loop()
        self.mode_name, self.mode = menu_items[idx]
        self.iv_len = kef.MODE_IVS.get(self.mode, 0)
        return True

    def input_version_ui(self):
        """implements ui to allow user to select KEF version"""
        self.ctx.display.clear()
        self.ctx.display.draw_centered_text(
            t("Use default Mode?") + " " + self.mode_name, highlight_prefix="?"
        )
        if self.prompt("", BOTTOM_PROMPT_LINE):
            return True
        menu_items = [
            (v["name"], k)
            for k, v in sorted(kef.VERSIONS.items())
            if isinstance(v, dict) and v["mode"] is not None
        ]
        idx, _ = Menu(
            self.ctx, [(x[0], lambda: None) for x in menu_items], back_label=None
        ).run_loop()
        self.version = [v for i, (_, v) in enumerate(menu_items) if i == idx][0]
        self.version_name = kef.VERSIONS[self.version]["name"]
        self.mode = kef.VERSIONS[self.version]["mode"]
        self.mode_name = [k for k, v in kef.MODE_NUMBERS.items() if v == self.mode][0]
        self.iv_len = kef.MODE_IVS.get(self.mode, 0)
        return True

    def input_iterations_ui(self):
        """implements ui to allow user to set key-stretch iterations"""
        curr_value = str(self.iterations)
        dflt_prompt = t("Use default PBKDF2 iter.?")
        title = t("PBKDF2 iter.") + ": 10K - 510K"
        keypads = [DIGITS]
        iterations = prompt_for_text_update(
            self.ctx, curr_value, dflt_prompt, True, "?", title, keypads
        )
        if QR_CODE_ITER_MULTIPLE <= int(iterations) <= 550000:
            self.iterations = int(iterations)
            return True
        return None

    def input_label_ui(
        self,
        dflt_label="",
        dflt_prompt="",
        dflt_affirm=True,
        title=t("Visible Label"),
        keypads=None,
    ):
        """implements ui to allow user to set a KEF label"""
        if dflt_label and not dflt_prompt:
            dflt_prompt = t("Update KEF ID?")
            dflt_affirm = False
        self.label = prompt_for_text_update(
            self.ctx, dflt_label, dflt_prompt, dflt_affirm, "?", title, keypads
        )
        return True

    def input_iv_ui(self):
        """Build IV bytes when the selected mode requires it."""
        if self.iv_len > 0:
            try:
                import urandom

                self.__iv = bytes([urandom.getrandbits(8) for _ in range(self.iv_len)])
            except:
                import os

                self.__iv = os.urandom(self.iv_len)
            return True
        self.__iv = None
        return True

    def public_info_ui(self, kef_envelope=None, prompt_decrypt=False):
        """implements ui to allow user to see public exterior of KEF envelope"""
        if kef_envelope:
            self.parse(kef_envelope)
        elif not self.ciphertext:
            raise ValueError("KEF Envelope not yet parsed")
        try:
            displayable_label = self.label.decode()
        except:
            displayable_label = "0x" + hexlify(self.label).decode()

        public_info = "\n".join(
            [
                t("KEF Encrypted") + " (" + str(len(self.ciphertext)) + " B)",
                self.fit_to_line(displayable_label, t("ID") + ": "),
                t("Version") + ": " + self.version_name,
                t("PBKDF2 iter.") + ": " + str(self.iterations),
            ]
        )
        self.ctx.display.clear()
        if prompt_decrypt:
            return self.prompt(
                public_info + "\n\n" + t("Decrypt?"), self.ctx.display.height() // 2
            )
        self.ctx.display.draw_hcentered_text(public_info)
        self.ctx.input.wait_for_button()
        return True

    def seal_ui(
        self,
        plaintext,
        overrides=None,
        dflt_label_prompt="",
        dflt_label_affirm=True,
    ):
        """implements ui to allow user to seal plaintext inside a KEF envelope"""
        if not isinstance(overrides, list):
            overrides = []
        if self.ciphertext:
            raise ValueError("KEF Envelope already sealed")
        if not (self.__key or self.input_key_ui()):
            return None
        if overrides:
            if OVERRIDE_ITERATIONS in overrides and not self.input_iterations_ui():
                return None
            if OVERRIDE_VERSION in overrides and not self.input_version_ui():
                return None
            if OVERRIDE_MODE in overrides and not self.input_mode_ui():
                return None
        if self.iv_len:
            if not (self.__iv or self.input_iv_ui()):
                return None
        if OVERRIDE_LABEL in overrides or not self.label:
            self.input_label_ui(self.label, dflt_label_prompt, dflt_label_affirm)
        if self.version is None:
            self.version = kef.suggest_versions(plaintext, self.mode_name)[0]
            self.version_name = kef.VERSIONS[self.version]["name"]
        self.ctx.display.clear()
        self.ctx.display.draw_centered_text(t("Processing..."))
        cipher = kef.Cipher(self.__key, self.label, self.iterations)
        self.ciphertext = cipher.encrypt(plaintext, self.version, self.__iv)
        self.__key = None
        self.__iv = None
        return kef.wrap(self.label, self.version, self.iterations, self.ciphertext)

    def unseal_ui(self, kef_envelope=None, prompt_decrypt=True, display_plain=False):
        """implements ui to allow user to unseal a plaintext from a sealed KEF envelope"""
        if kef_envelope:
            if not self.parse(kef_envelope):
                return None
        if not self.ciphertext:
            raise ValueError("KEF Envelope not yet parsed")
        if prompt_decrypt:
            if not self.public_info_ui(prompt_decrypt=prompt_decrypt):
                return None
        if not (self.__key or self.input_key_ui(creating=False)):
            return None
        self.ctx.display.clear()
        self.ctx.display.draw_centered_text(t("Processing..."))
        cipher = kef.Cipher(self.__key, self.label, self.iterations)
        plaintext = cipher.decrypt(self.ciphertext, self.version)
        self.__key = None
        if plaintext is None:
            raise KeyError("Failed to decrypt")
        if display_plain:
            self.ctx.display.clear()
            try:
                self.ctx.display.draw_centered_text(plaintext.decode())
            except:
                self.ctx.display.draw_centered_text("0x" + hexlify(plaintext).decode())
            self.ctx.input.wait_for_button()
        return plaintext


class EncryptionKey(Page):
    """UI to capture an encryption key"""

    def __init__(self, ctx):
        super().__init__(ctx, None)
        self.ctx = ctx

    def key_strength(self, key_string):
        """Check the strength of a key."""

        if isinstance(key_string, bytes):
            key_string = hexlify(key_string).decode()

        if len(key_string) < 8:
            return t("Weak")

        has_upper = has_lower = has_digit = has_special = False

        for c in key_string:
            if "a" <= c <= "z":
                has_lower = True
            elif "A" <= c <= "Z":
                has_upper = True
            elif "0" <= c <= "9":
                has_digit = True
            else:
                has_special = True

            # small optimization: stop if all found
            if has_upper and has_lower and has_digit and has_special:
                break

        # Count how many character types are present
        score = sum([has_upper, has_lower, has_digit, has_special])

        # Add length score to score
        key_len = len(key_string)
        if key_len >= 12:
            score += 1
        if key_len >= 16:
            score += 1
        if key_len >= 20:
            score += 1
        if key_len >= 40:
            score += 1

        set_len = len(set(key_string))
        if set_len < 6:
            score -= 1
        if set_len < 3:
            score -= 1

        # Determine key strength
        if score >= 4:
            return t("Strong")
        if score >= 3:
            return t("Medium")
        return t("Weak")

    def encryption_key(self, creating=False):
        """Loads and returns an encryption key from keypad or QR code"""
        submenu = Menu(
            self.ctx,
            [
                (t("Type Key"), self.load_key),
                (t("Scan Key QR Code"), self.load_qr_encryption_key),
            ],
            back_label=None,
        )
        _, key = submenu.run_loop()

        try:
            # encryption key may have been encrypted
            decrypted = decrypt_kef(self.ctx, key)
            try:
                # no assumed decodings except for utf8
                decrypted = decrypted.decode()
            except:
                pass

            key = decrypted if decrypted else key
        except KeyError:
            self.flash_error(t("Failed to decrypt"))
            return None
        except ValueError:
            # ValueError=not KEF or declined to decrypt
            pass

        while True:
            if key in (None, "", b"", ESC_KEY, MENU_CONTINUE):
                self.flash_error(t("Failed to load"))
                return None

            self.ctx.display.clear()
            offset_y = DEFAULT_PADDING
            displayable = key if isinstance(key, str) else "0x" + hexlify(key).decode()
            key_lines = self.ctx.display.draw_hcentered_text(
                "{} ({}): {}".format(t("Key"), len(key), displayable),
                offset_y,
                highlight_prefix=":",
            )

            if creating:
                strength = self.key_strength(key)
                offset_y += (key_lines + 1) * FONT_HEIGHT
                color = theme.error_color if strength == t("Weak") else theme.fg_color
                self.ctx.display.draw_hcentered_text(
                    "{}: {}".format(t("Strength"), strength),
                    offset_y,
                    color,
                    highlight_prefix=":",
                )

            if self.prompt(t("Proceed?"), BOTTOM_PROMPT_LINE):
                return key

            # user did not confirm to proceed
            if not isinstance(key, str):
                return None
            key = self.load_key(key)

    def load_key(self, data=""):
        """Loads and returns a key from keypad"""
        if not isinstance(data, str):
            raise TypeError("load_key() expected str")
        data = self.capture_from_keypad(
            t("Key"),
            [LETTERS, UPPERCASE_LETTERS, NUM_SPECIAL_1, NUM_SPECIAL_2],
            starting_buffer=data,
        )
        if len(str(data)) > ENCRYPTION_KEY_MAX_LEN:
            raise ValueError("Maximum length exceeded (%s)" % ENCRYPTION_KEY_MAX_LEN)
        return data

    def load_qr_encryption_key(self):
        """Loads and returns a key from a QR code"""

        from .qr_capture import QRCodeCapture

        qr_capture = QRCodeCapture(self.ctx)
        data, _ = qr_capture.qr_capture_loop()
        if data is None:
            return None
        if len(data) > ENCRYPTION_KEY_MAX_LEN:
            raise ValueError("Maximum length exceeded (%s)" % ENCRYPTION_KEY_MAX_LEN)
        return data


