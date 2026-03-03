import gc
from .display import display, Display
from .input import Input
from .camera import Camera
from .light import Light
from .kboard import kboard


class VaultState:
    """State for unlocked vault data in RAM."""

    def __init__(self, cipher, manifest, version, iterations):
        self.cipher = cipher
        self.manifest = manifest
        self.version = version
        self.iterations = iterations

    def clear(self):
        """Clear sensitive data."""
        self.cipher = None
        self.manifest = None
        gc.collect()


class Context:
    """Singleton with global runtime state."""

    def __init__(self):
        self.display = display
        self.input = Input()
        self.camera = Camera()
        self.light = Light() if kboard.has_light else None
        self.power_manager = None
        self.vault = None
        self.tc_code_enabled = False

    def clear(self):
        """Clear sensitive state."""
        if self.vault:
            self.vault.clear()
        self.vault = None
        gc.collect()

    def is_unlocked(self):
        """Returns True when vault is unlocked."""
        return self.vault is not None and self.vault.cipher is not None

    def is_logged_in(self):
        """Backward-compatible alias for old menu code."""
        return self.is_unlocked()


ctx = Context()
