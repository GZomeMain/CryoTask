import os
import sys
import ctypes
import traceback

# High DPI Fix
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

from src.cryotask.ui.web_window import launch_web_gui
from src.cryotask.utils.helpers import is_admin, run_as_admin

def main():
    if not is_admin():
        # MB_YESNO (0x04) | MB_ICONWARNING (0x30) = 0x34
        # IDYES = 6
        res = ctypes.windll.user32.MessageBoxW(
            None, 
            "CryoTask requires Administrator privileges to manage process memory and suspend processes.\n\nWould you like to restart as Administrator?", 
            "Administrator Permission Required", 
            0x34
        )
        if res == 6:
            run_as_admin()
        sys.exit(0)

    try:
        launch_web_gui()
    except Exception as e:
        traceback.print_exc()
        print(f"Error: {e}")
        input("Press Enter to close...")

if __name__ == "__main__":
    main()
