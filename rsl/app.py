from pathlib import Path

import webview

from .api import Api
from .driver import Installer
from .engine import Engine
from .store import Store

UI = Path(__file__).resolve().parent / "ui" / "index.html"
ICON = UI.parent / "logo.ico"


def main():
    engine = Engine()
    engine.start()
    engine.ready.wait(5)
    api = Api(engine, Store(), Installer())
    webview.create_window(
        "RadioSetLink",
        str(UI),
        js_api=api,
        width=1280,
        height=840,
        min_size=(1040, 680),
        background_color="#080B12",
    )
    try:
        webview.start(icon=str(ICON))
    finally:
        engine.set_output(False)
        engine.stop()
