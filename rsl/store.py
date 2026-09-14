import json
import os
import threading
from pathlib import Path

FORBIDDEN = set('<>:"/\\|?*')


class Store:
    def __init__(self):
        self.root = Path(os.environ.get("APPDATA") or Path.home()) / "RadioSetLink"
        self.folder = self.root / "profiles"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.file = self.root / "settings.json"
        self.lock = threading.Lock()

    def settings(self):
        try:
            data = json.loads(self.file.read_text("utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def update(self, **values):
        with self.lock:
            data = self.settings()
            data.update(values)
            self.file.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

    def profiles(self):
        return sorted((path.stem for path in self.folder.glob("*.json")), key=str.lower)

    def path(self, name):
        clean = "".join(c for c in str(name or "") if c not in FORBIDDEN and ord(c) >= 32).strip(" .")[:64]
        return self.folder / f"{clean}.json" if clean else None

    def load(self, name):
        path = self.path(name)
        if path is None:
            return None
        try:
            return json.loads(path.read_text("utf-8"))
        except (OSError, ValueError):
            return None

    def save(self, name, profile):
        path = self.path(name)
        if path is None:
            return None
        path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), "utf-8")
        return path.stem

    def delete(self, name):
        path = self.path(name)
        if path is not None:
            path.unlink(missing_ok=True)
