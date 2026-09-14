from . import mapping
from .sources import serial_ports

LANGUAGES = ("ru", "en")
DEFAULT_BAUD = 420000


def clean_target(target):
    if not isinstance(target, dict) or target.get("kind") not in ("hid", "crsf") or not target.get("id"):
        return None
    try:
        baud = int(target.get("baud") or DEFAULT_BAUD)
    except (TypeError, ValueError):
        baud = DEFAULT_BAUD
    return {"kind": target["kind"], "id": str(target["id"]), "baud": baud}


class Api:
    def __init__(self, engine, store, installer):
        self._engine = engine
        self._store = store
        self._installer = installer

    def boot(self):
        settings = self._store.settings()
        name = settings.get("profile") or ""
        data = self._store.load(name) if name else None
        if data is None:
            name = ""
            data = mapping.preset(2, "a")
        profile = self._engine.set_profile(data)
        target = clean_target(settings.get("source"))
        if target:
            self._engine.set_target(target)
        lang = settings.get("lang") if settings.get("lang") in LANGUAGES else ""
        return {"lang": lang, "profile": profile, "name": name, "profiles": self._store.profiles(), "source": target}

    def state(self):
        state = self._engine.snapshot()
        state["driver"] = self._installer.status()
        return state

    def install_driver(self):
        self._installer.start()

    def ports(self):
        return serial_ports()

    def connect(self, target):
        target = clean_target(target)
        if target is None:
            return False
        self._engine.set_target(target)
        self._store.update(source=target)
        return True

    def disconnect(self):
        self._engine.set_target(None)
        self._store.update(source=None)

    def set_profile(self, profile):
        self._engine.set_profile(profile)

    def preset(self, mode, kind):
        profile = mapping.preset(1 if mode == 1 else 2, "c" if kind == "crsf" else "a")
        profile["cal"] = self._engine.get_profile()["cal"]
        return self._engine.set_profile(profile)

    def load_profile(self, name):
        data = self._store.load(name)
        if data is None:
            return None
        self._store.update(profile=name)
        return self._engine.set_profile(data)

    def save_profile(self, name, profile):
        profile = self._engine.set_profile(profile)
        saved = self._store.save(name, profile)
        if saved:
            self._store.update(profile=saved)
        return {"name": saved, "profiles": self._store.profiles()}

    def delete_profile(self, name):
        self._store.delete(name)
        if self._store.settings().get("profile") == name:
            self._store.update(profile="")
        return self._store.profiles()

    def start(self):
        self._engine.set_output(True)

    def stop(self):
        self._engine.set_output(False)

    def calibrate_begin(self):
        self._engine.begin_calibration()

    def calibrate_end(self):
        return self._engine.end_calibration()

    def calibrate_reset(self):
        return self._engine.reset_calibration()

    def set_lang(self, lang):
        if lang in LANGUAGES:
            self._store.update(lang=lang)
