import board
import binascii
from .settings import (
    SettingsNamespace,
    CategorySetting,
    NumberSetting,
    SD_PATH,
    FLASH_PATH,
    MAIN_TXT,
    TEST_TXT,
)
from .kboard import kboard

TC_CODE_PATH = "/flash/tcc"
TC_CODE_PBKDF2_ITERATIONS = 100000

DEFAULT_LOCALE = "en-US"


def t(slug):
    """Translate slug according to current locale."""
    if not locale_control.translation:
        return slug
    slug_id = binascii.crc32(slug.encode("utf-8"))
    try:
        index = locale_control.reference.index(slug_id)
    except:
        return slug
    return locale_control.translation[index]


class LocaleControl:
    """Manage active locale and translation arrays."""

    def __init__(self):
        self.reference = None
        self.translation = None
        self.locales = []
        self.update_locales()

    def update_locales(self):
        from .translations import available_languages

        self.locales = [DEFAULT_LOCALE]
        self.locales.extend(available_languages)

    def load_locale(self, locale):
        if locale == DEFAULT_LOCALE:
            self.reference = None
            self.translation = None
            return

        module_path = "krux.translations.{}".format(locale[:2])
        translation_module = __import__(module_path)
        for part in module_path.split(".")[1:]:
            translation_module = getattr(translation_module, part)

        self.translation = getattr(translation_module, "translation_array")
        if self.reference is None:
            from .translations import ref_array

            self.reference = ref_array


locale_control = LocaleControl()


class ButtonsSettings(SettingsNamespace):
    """Buttons debounce settings."""

    namespace = "settings.buttons"
    debounce = NumberSetting(int, "debounce", 100, [100, 500])

    def label(self, attr):
        return {
            "debounce": t("Buttons Debounce"),
        }[attr]


class TouchSettings(SettingsNamespace):
    """Touch threshold settings."""

    namespace = "settings.touchscreen"
    default_th = 40 if kboard.is_wonder_k else 22
    threshold = NumberSetting(int, "threshold", default_th, [10, 200])

    def label(self, attr):
        return {
            "threshold": t("Touch Threshold"),
        }[attr]


class DisplayAmgSettings(SettingsNamespace):
    """Custom display settings for Maix Amigo."""

    namespace = "settings.display_amg"
    flipped_x_coordinates = CategorySetting("flipped_x", True, [False, True])
    inverted_colors = CategorySetting("inverted_colors", True, [False, True])
    bgr_colors = CategorySetting("bgr_colors", True, [False, True])
    lcd_type = CategorySetting("lcd_type", 0, [0, 1])

    def label(self, attr):
        return {
            "flipped_x": t("Mirror X Coordinates"),
            "inverted_colors": t("Inverted Colors"),
            "bgr_colors": t("BGR Colors"),
            "lcd_type": t("LCD Type"),
        }[attr]


class DisplaySettings(SettingsNamespace):
    """Generic display settings."""

    namespace = "settings.display"
    if kboard.can_control_brightness:
        default_brightness = "1" if kboard.is_m5stickv else "3"
        brightness = CategorySetting(
            "brightness", default_brightness, ["1", "2", "3", "4", "5"]
        )
    if kboard.can_flip_orientation:
        flipped_orientation = CategorySetting(
            "flipped_orientation", False, [False, True]
        )

    def label(self, attr):
        options = {}
        if kboard.can_control_brightness:
            options["brightness"] = t("Brightness")
        if kboard.can_flip_orientation:
            options["flipped_orientation"] = t("Rotate 180")
        return options[attr]


class HardwareSettings(SettingsNamespace):
    """Hardware related settings."""

    namespace = "settings.hardware"

    def __init__(self):
        self.buttons = ButtonsSettings()
        if board.config["krux"]["display"].get("touch", False):
            self.touch = TouchSettings()
        if kboard.is_amigo:
            self.display = DisplayAmgSettings()
        elif kboard.can_flip_orientation or kboard.can_control_brightness:
            self.display = DisplaySettings()

    def label(self, attr):
        hardware_menu = {
            "buttons": t("Buttons"),
        }
        if board.config["krux"]["display"].get("touch", False):
            hardware_menu["touchscreen"] = t("Touchscreen")
        if kboard.is_amigo:
            hardware_menu["display_amg"] = t("Display")
        elif kboard.can_flip_orientation or kboard.can_control_brightness:
            hardware_menu["display"] = t("Display")
        return hardware_menu[attr]


class PersistSettings(SettingsNamespace):
    """Persistence location settings."""

    namespace = "settings.persist"
    location = CategorySetting("location", FLASH_PATH, [FLASH_PATH, SD_PATH])

    def label(self, attr):
        return {
            "location": t("Location"),
        }[attr]


class SecuritySettings(SettingsNamespace):
    """Security settings."""

    namespace = "settings.security"
    boot_flash_hash = CategorySetting("boot_flash_hash", False, [False, True])

    def label(self, attr):
        return {
            "boot_flash_hash": t("TC Flash Hash at Boot"),
        }[attr]


class AppearanceSettings(SettingsNamespace):
    """Appearance and locale settings."""

    DARK_THEME_NAME = "Dark"
    LIGHT_THEME_NAME = "Light"
    ORANGE_THEME_NAME = "Orange"
    GREEN_THEME_NAME = "CypherPunk"
    PINK_THEME_NAME = "CypherPink"

    namespace = "settings.appearance"
    theme = CategorySetting(
        "theme",
        DARK_THEME_NAME,
        [
            DARK_THEME_NAME,
            LIGHT_THEME_NAME,
            ORANGE_THEME_NAME,
            GREEN_THEME_NAME,
            PINK_THEME_NAME,
        ],
    )
    screensaver_time = NumberSetting(int, "screensaver_time", 5, [0, 30])
    locale = CategorySetting("locale", DEFAULT_LOCALE, locale_control.locales)

    def label(self, attr):
        return {
            "theme": t("Theme"),
            "screensaver_time": t("Screensaver Time"),
            "locale": t("Locale"),
        }[attr]


class Settings(SettingsNamespace):
    """Top-level settings namespace."""

    namespace = "settings"

    def __init__(self):
        self.appearance = AppearanceSettings()
        self.hardware = HardwareSettings()
        self.security = SecuritySettings()
        self.persist = PersistSettings()

    def is_flipped_orientation(self):
        return hasattr(Settings().hardware, "display") and getattr(
            Settings().hardware.display, "flipped_orientation", False
        )

    def label(self, attr):
        return {
            "appearance": t("Appearance"),
            "hardware": t("Hardware"),
            "security": t("Security"),
            "persist": t("Persist"),
        }[attr]


locale_control.load_locale(Settings().appearance.locale)
