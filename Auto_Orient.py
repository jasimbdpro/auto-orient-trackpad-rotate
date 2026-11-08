import sys, os, time, ctypes, struct, traceback
from ctypes import wintypes as w

# Folder for the log file: next to the .exe when built, next to the script otherwise
if getattr(sys, "frozen", False):
    HERE = os.path.dirname(sys.executable)
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "trackpad_rotate.log")


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(s + "\n")
    except Exception:
        pass
    try:
        if sys.stdout:
            print(s, flush=True)
    except Exception:
        pass


sys.excepthook = lambda t, v, tb: log("".join(traceback.format_exception(t, v, tb)))

# --- options: python trackpad_rotate.py --force 2   (test as if screen is 180 deg)
#              python trackpad_rotate.py --swap      (swap 90 and 270 directions)
FORCE = None
SWAP = "--swap" in sys.argv
if "--force" in sys.argv:
    FORCE = int(sys.argv[sys.argv.index("--force") + 1])

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# --- Prevent two copies from running at the same time ---
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, w.BOOL, w.LPCWSTR]
kernel32.CreateMutexW.restype = ctypes.c_void_p
_mutex = kernel32.CreateMutexW(None, False, "Local\\TrackpadRotateSingleInstance")
if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
    sys.exit(0)

LRESULT, WPARAM, LPARAM = ctypes.c_ssize_t, ctypes.c_size_t, ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, WPARAM, LPARAM)

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, ctypes.c_void_p, w.DWORD]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, WPARAM, LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.PeekMessageW.argtypes = [ctypes.POINTER(w.MSG), ctypes.c_void_p, w.UINT, w.UINT, w.UINT]
user32.PeekMessageW.restype = w.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(w.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(w.MSG)]
user32.GetCursorPos.argtypes = [ctypes.POINTER(w.POINT)]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.EnumDisplaySettingsW.argtypes = [w.LPCWSTR, w.DWORD, ctypes.c_void_p]
kernel32.GetModuleHandleW.argtypes = [w.LPCWSTR]
kernel32.GetModuleHandleW.restype = ctypes.c_void_p

try:
    ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
except Exception:
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", w.POINT), ("mouseData", w.DWORD), ("flags", w.DWORD),
                ("time", w.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


def read_orientation():
    buf = ctypes.create_string_buffer(220)       # DEVMODEW
    struct.pack_into("<H", buf, 68, 220)         # dmSize
    if user32.EnumDisplaySettingsW(None, 0xFFFFFFFF, buf):
        return struct.unpack_from("<I", buf, 84)[0]  # dmDisplayOrientation
    return 0


TRANSFORMS = {
    0: lambda dx, dy: (dx, dy),
    1: lambda dx, dy: (-dy, dx),
    2: lambda dx, dy: (-dx, -dy),
    3: lambda dx, dy: (dy, -dx),
}
if SWAP:
    TRANSFORMS[1], TRANSFORMS[3] = TRANSFORMS[3], TRANSFORMS[1]

orient = [FORCE if FORCE is not None else read_orientation()]
busy = [False]
remapped = [0]


@HOOKPROC
def hook_cb(n, wp, lp):
    try:
        if n >= 0 and wp == 0x0200 and orient[0] in (1, 2, 3) and not busy[0]:
            info = ctypes.cast(lp, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            if not (info.flags & 0x01):          # ignore injected moves
                cur = w.POINT()
                user32.GetCursorPos(ctypes.byref(cur))
                dx, dy = info.pt.x - cur.x, info.pt.y - cur.y
                if dx or dy:
                    ndx, ndy = TRANSFORMS[orient[0]](dx, dy)
                    busy[0] = True
                    try:
                        user32.SetCursorPos(cur.x + ndx, cur.y + ndy)
                    finally:
                        busy[0] = False
                    remapped[0] += 1
                return 1                          # swallow original move
    except Exception:
        log(traceback.format_exc())
    return user32.CallNextHookEx(None, n, wp, lp)


def main():
    log("Starting. orientation =", orient[0] * 90, "deg",
        "(forced)" if FORCE is not None else "(auto)", "| swap =", SWAP)
    hook = user32.SetWindowsHookExW(14, hook_cb, kernel32.GetModuleHandleW(None), 0)
    if not hook:
        log("Hook failed, error", ctypes.get_last_error())
        return
    log("Hook installed. Running. Ctrl+C to stop.")

    msg = w.MSG()
    last_poll = 0
    last_report = 0
    try:
        while True:
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            now = time.time()
            if FORCE is None and now - last_poll > 0.5:
                last_poll = now
                new = read_orientation()
                if new != orient[0]:
                    orient[0] = new
                    log("Orientation changed ->", new * 90, "deg")
            if FORCE is not None and now - last_report > 3 and remapped[0]:
                last_report = now
                log("remapped moves so far:", remapped[0])
            time.sleep(0.002)
    except KeyboardInterrupt:
        pass
    finally:
        user32.UnhookWindowsHookEx(hook)
        log("Stopped.")


if __name__ == "__main__":
    main()
