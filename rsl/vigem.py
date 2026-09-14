import ctypes
import struct
import threading
from ctypes import Structure, c_short, c_ubyte, c_uint, c_ushort, c_void_p
from pathlib import Path

ERROR_NONE = 0x20000000
ARCH = "x64" if struct.calcsize("P") == 8 else "x86"
LIBRARY = Path(__file__).resolve().parent / "bin" / ARCH / "ViGEmClient.dll"

XUSB_BUTTONS = {
    "up": 0x0001,
    "down": 0x0002,
    "left": 0x0004,
    "right": 0x0008,
    "start": 0x0010,
    "back": 0x0020,
    "ls": 0x0040,
    "rs": 0x0080,
    "lb": 0x0100,
    "rb": 0x0200,
    "guide": 0x0400,
    "a": 0x1000,
    "b": 0x2000,
    "x": 0x4000,
    "y": 0x8000,
}


class XusbReport(Structure):
    _fields_ = [
        ("wButtons", c_ushort),
        ("bLeftTrigger", c_ubyte),
        ("bRightTrigger", c_ubyte),
        ("sThumbLX", c_short),
        ("sThumbLY", c_short),
        ("sThumbRX", c_short),
        ("sThumbRY", c_short),
    ]


class Ds4Report(Structure):
    _fields_ = [
        ("bThumbLX", c_ubyte),
        ("bThumbLY", c_ubyte),
        ("bThumbRX", c_ubyte),
        ("bThumbRY", c_ubyte),
        ("wButtons", c_ushort),
        ("bSpecial", c_ubyte),
        ("bTriggerL", c_ubyte),
        ("bTriggerR", c_ubyte),
    ]


SIGNATURES = {
    "vigem_alloc": ((), c_void_p),
    "vigem_free": ((c_void_p,), None),
    "vigem_connect": ((c_void_p,), c_uint),
    "vigem_disconnect": ((c_void_p,), None),
    "vigem_target_x360_alloc": ((), c_void_p),
    "vigem_target_ds4_alloc": ((), c_void_p),
    "vigem_target_free": ((c_void_p,), None),
    "vigem_target_add": ((c_void_p, c_void_p), c_uint),
    "vigem_target_remove": ((c_void_p, c_void_p), c_uint),
    "vigem_target_x360_update": ((c_void_p, c_void_p, XusbReport), c_uint),
    "vigem_target_ds4_update": ((c_void_p, c_void_p, Ds4Report), c_uint),
}


class VigemError(Exception):
    pass


_library = None
_lock = threading.Lock()


def library():
    global _library
    with _lock:
        if _library is None:
            dll = ctypes.CDLL(str(LIBRARY))
            for name, (arguments, result) in SIGNATURES.items():
                function = getattr(dll, name)
                function.argtypes = arguments
                function.restype = result
            _library = dll
        return _library


class Target:
    allocate = ""
    update = ""

    def __init__(self):
        self.dll = library()
        self.client = self.dll.vigem_alloc()
        self.target = None
        if not self.client:
            raise VigemError("alloc")
        error = self.dll.vigem_connect(self.client)
        if error != ERROR_NONE:
            self.dll.vigem_free(self.client)
            raise VigemError(f"connect {error:#x}")
        target = getattr(self.dll, self.allocate)()
        error = self.dll.vigem_target_add(self.client, target)
        if error != ERROR_NONE:
            self.dll.vigem_target_free(target)
            self.dll.vigem_disconnect(self.client)
            self.dll.vigem_free(self.client)
            raise VigemError(f"add {error:#x}")
        self.target = target

    def send(self, report):
        error = getattr(self.dll, self.update)(self.client, self.target, report)
        if error != ERROR_NONE:
            raise VigemError(f"update {error:#x}")

    def close(self):
        if self.target is None:
            return
        self.dll.vigem_target_remove(self.client, self.target)
        self.dll.vigem_target_free(self.target)
        self.dll.vigem_disconnect(self.client)
        self.dll.vigem_free(self.client)
        self.target = None


class Xbox360(Target):
    allocate = "vigem_target_x360_alloc"
    update = "vigem_target_x360_update"


class DualShock4(Target):
    allocate = "vigem_target_ds4_alloc"
    update = "vigem_target_ds4_update"
