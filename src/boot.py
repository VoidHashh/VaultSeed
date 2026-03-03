"""Entry point for Vault firmware.
Flow: splash -> check updates -> unlock vault -> vault home -> shutdown
"""

import sys
import time
import gc
import os

from krux.power import power_manager

MIN_SPLASH_WAIT_TIME = 1000


def draw_splash():
    from krux.display import display, SPLASH

    display.initialize_lcd()
    display.clear()
    display.draw_centered_text(SPLASH)


def check_for_updates():
    try:
        os.stat("/sd/firmware.bin")
    except OSError:
        return

    from krux import firmware

    if firmware.upgrade():
        power_manager.shutdown()

    try:
        sys.modules.pop("krux.firmware")
    except KeyError:
        pass
    try:
        del sys.modules["krux"].firmware
    except:
        pass
    del firmware


def tc_code_verification(ctx_pin):
    from krux.krux_settings import Settings, TC_CODE_PATH

    try:
        if not (os.stat(TC_CODE_PATH)[0] & 0x4000) == 0:
            raise OSError
    except OSError:
        return True

    ctx_pin.tc_code_enabled = True

    if not Settings().security.boot_flash_hash:
        return True

    from krux.pages.tc_code_verification import TCCodeVerification

    pin_verification_page = TCCodeVerification(ctx_pin)
    pin_hash = pin_verification_page.capture(return_hash=True)
    if not pin_hash:
        return False

    from krux.pages.flash_tools import FlashHash

    flash_hash = FlashHash(ctx_pin, pin_hash)
    flash_hash.generate()

    try:
        sys.modules.pop("krux.pages.flash_tools")
    except KeyError:
        pass
    try:
        del sys.modules["krux"].pages.flash_tools
    except:
        pass

    try:
        sys.modules.pop("krux.pages.tc_code_verification")
    except KeyError:
        pass
    try:
        del sys.modules["krux"].pages.tc_code_verification
    except:
        pass
    return True


def vault_unlock(ctx_vu):
    from krux.pages.vault_pages.vault_unlock import VaultUnlock

    result = VaultUnlock(ctx_vu).run()
    try:
        sys.modules.pop("krux.pages.vault_pages.vault_unlock")
    except KeyError:
        pass
    return result


def vault_home(ctx_vh):
    from krux.pages.vault_pages.vault_home import VaultHome

    if not ctx_vh.is_unlocked():
        return True

    while True:
        status = VaultHome(ctx_vh).run()
        if status != 0:
            break

    try:
        sys.modules.pop("krux.pages.vault_pages.vault_home")
    except KeyError:
        pass

    return status != 2


preimport_ticks = time.ticks_ms()
draw_splash()
check_for_updates()
gc.collect()

from krux.context import ctx
from krux.auto_shutdown import auto_shutdown

ctx.power_manager = power_manager
auto_shutdown.add_ctx(ctx)

postimport_ticks = time.ticks_ms()
if preimport_ticks + MIN_SPLASH_WAIT_TIME > postimport_ticks:
    time.sleep_ms(preimport_ticks + MIN_SPLASH_WAIT_TIME - postimport_ticks)

if not tc_code_verification(ctx):
    power_manager.shutdown()

while True:
    if not vault_unlock(ctx):
        break
    gc.collect()
    if not vault_home(ctx):
        break
    ctx.clear()
    gc.collect()

ctx.clear()
power_manager.shutdown()
