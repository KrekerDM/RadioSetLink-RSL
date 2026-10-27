import ctypes
import math
import os
import sys
import tempfile
import threading
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT))
os.environ["APPDATA"] = tempfile.mkdtemp()
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import webview
from PIL import Image

from rsl import driver, mapping
from rsl.api import Api
from rsl.app import ICON, UI
from rsl.engine import Engine
from rsl.store import Store
from rsl.vigem import Ds4Report, DualShock4

TITLE = "RadioSetLink"
PW_RENDERFULLCONTENT = 2

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.FindWindowW.restype = ctypes.c_void_p
user32.GetWindowDC.restype = ctypes.c_void_p
user32.GetWindowDC.argtypes = (ctypes.c_void_p,)
user32.ReleaseDC.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
user32.PrintWindow.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint)
user32.GetWindowRect.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
user32.GetClientRect.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
user32.ClientToScreen.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.CreateCompatibleDC.argtypes = (ctypes.c_void_p,)
gdi32.CreateCompatibleBitmap.restype = ctypes.c_void_p
gdi32.CreateCompatibleBitmap.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
gdi32.SelectObject.restype = ctypes.c_void_p
gdi32.SelectObject.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
gdi32.GetDIBits.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint)
gdi32.DeleteObject.argtypes = (ctypes.c_void_p,)
gdi32.DeleteDC.argtypes = (ctypes.c_void_p,)


class BitmapHeader(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def grab():
    hwnd = user32.FindWindowW(None, TITLE)
    outer = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(outer))
    inner = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(inner))
    origin = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(origin))
    width, height = outer.right - outer.left, outer.bottom - outer.top
    window_dc = user32.GetWindowDC(hwnd)
    memory = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    gdi32.SelectObject(memory, bitmap)
    user32.PrintWindow(hwnd, memory, PW_RENDERFULLCONTENT)
    header = BitmapHeader(biSize=ctypes.sizeof(BitmapHeader), biWidth=width, biHeight=-height, biPlanes=1, biBitCount=32)
    pixels = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(memory, bitmap, 0, height, pixels, ctypes.byref(header), 0)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(memory)
    user32.ReleaseDC(hwnd, window_dc)
    image = Image.frombuffer("RGB", (width, height), pixels, "raw", "BGRX", 0, 1)
    left, top = origin.x - outer.left, origin.y - outer.top
    return image.crop((left, top, left + inner.right, top + inner.bottom))


class Radio(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.device = DualShock4()
        self.report = Ds4Report(bThumbLX=128, bThumbLY=128, bThumbRX=128, bThumbRY=128, wButtons=0x8)
        self.device.send(self.report)
        self.alive = True

    def run(self):
        phase = 0.0
        report = self.report
        while self.alive:
            phase += 0.02
            report.bThumbLX = int(128 + 90 * math.sin(phase * 1.3))
            report.bThumbLY = int(128 + 110 * math.cos(phase * 0.7))
            report.bThumbRX = int(128 + 100 * math.sin(phase * 2.1))
            report.bThumbRY = int(128 + 80 * math.cos(phase * 1.7))
            report.bTriggerR = int(127 + 127 * math.sin(phase))
            report.wButtons = 0x8 | (0x20 if math.sin(phase * 0.9) > 0.3 else 0) | (0x40 if math.cos(phase * 0.6) > 0.5 else 0)
            self.device.send(report)
            time.sleep(0.016)

    def close(self):
        self.alive = False
        self.join(1)
        self.device.close()


def wait_for_device(engine):
    end = time.monotonic() + 10
    while time.monotonic() < end:
        devices = [d for d in engine.snapshot()["devices"] if "xbox" not in d["name"].lower()]
        if devices:
            return devices[0]
        time.sleep(0.05)
    raise RuntimeError("virtual DualShock 4 did not appear")


def demo_profile():
    profile = mapping.preset(2, "a")
    profile["axes"]["ly"]["inv"] = True
    profile["axes"]["ry"]["inv"] = True
    profile["axes"]["rt"]["in"] = "a5"
    profile["axes"]["lx"]["dz"] = 0.03
    profile["axes"]["rx"]["expo"] = 0.3
    for key, index in (("a", 0), ("b", 1), ("x", 2), ("y", 3), ("lb", 9)):
        profile["buttons"][key]["in"] = f"b{index}"
    return profile


def main():
    radio = Radio()
    radio.start()
    engine = Engine()
    engine.start()
    engine.ready.wait(5)
    device = wait_for_device(engine)

    store = Store()
    store.save("TX16S", demo_profile())
    store.save("Boxer", mapping.preset(1, "c"))
    store.update(lang="ru", profile="TX16S", source={"kind": "hid", "id": device["id"], "baud": 420000})

    installer = driver.Installer()
    window = webview.create_window(TITLE, str(UI), js_api=Api(engine, store, installer), width=1200, height=800)
    detected = driver.installed

    def shot(name):
        time.sleep(0.8)
        image = grab()
        image.save(DOCS / name, optimize=True)
        print(f"{name}: {image.width}x{image.height}")

    def social():
        image = Image.open(DOCS / "screenshot-main.png")
        width = image.width
        height = width // 2
        image.crop((0, 0, width, height)).resize((1280, 640), Image.LANCZOS).save(DOCS / "social-preview.png", optimize=True)
        print("social-preview.png: 1280x640")

    def scenario():
        time.sleep(5)
        engine.set_output(True)
        time.sleep(1.5)
        for lang, suffix in (("ru", ""), ("en", "-en")):
            window.evaluate_js(f"document.querySelector('[data-lang={lang}]').click()")
            window.evaluate_js("document.querySelector('.sheet').scrollTop = 0")
            shot(f"screenshot-main{suffix}.png")
            window.evaluate_js("document.querySelector('.sheet').scrollTop = document.getElementById('axes').offsetTop - document.querySelector('.sheet').offsetTop")
            shot(f"screenshot-mapping{suffix}.png")
            window.evaluate_js("document.querySelector('.sheet').scrollTop = 0")
            engine.set_output(False)
            driver.installed = lambda: False
            installer.stage = "missing"
            window.evaluate_js("openDriver(true)")
            shot(f"screenshot-driver{suffix}.png")
            driver.installed = detected
            installer.stage = "installed"
            window.evaluate_js("openDriver(false)")
            engine.set_output(True)
            time.sleep(0.5)
        social()
        window.destroy()

    threading.Thread(target=scenario, daemon=True).start()
    webview.start(icon=str(ICON))
    engine.stop()
    radio.close()


if __name__ == "__main__":
    main()
