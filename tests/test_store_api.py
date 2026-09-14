import os
import tempfile
import unittest
from unittest import mock

from rsl import mapping
from rsl.api import Api, clean_target
from rsl.engine import Engine
from rsl.store import Store


class FakeInstaller:
    def __init__(self):
        self.started = 0

    def status(self):
        return {"stage": "installed", "progress": 0.0, "error": ""}

    def start(self):
        self.started += 1


class TempAppData(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patcher = mock.patch.dict(os.environ, {"APPDATA": folder.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.store = Store()


class StoreTest(TempAppData):
    def test_settings_roundtrip(self):
        self.assertEqual(self.store.settings(), {})
        self.store.update(lang="ru")
        self.store.update(profile="Мой пульт")
        self.assertEqual(self.store.settings(), {"lang": "ru", "profile": "Мой пульт"})

    def test_corrupt_settings(self):
        self.store.file.write_text("{not json", "utf-8")
        self.assertEqual(self.store.settings(), {})
        self.store.file.write_text("[1, 2]", "utf-8")
        self.assertEqual(self.store.settings(), {})

    def test_profiles_save_load_delete(self):
        self.assertEqual(self.store.save("TX16S", {"x": 1}), "TX16S")
        self.assertEqual(self.store.save("boxer", {"x": 2}), "boxer")
        self.assertEqual(self.store.profiles(), ["boxer", "TX16S"])
        self.assertEqual(self.store.load("TX16S"), {"x": 1})
        self.store.delete("TX16S")
        self.store.delete("missing")
        self.assertEqual(self.store.profiles(), ["boxer"])
        self.assertIsNone(self.store.load("TX16S"))

    def test_names_are_sanitized(self):
        self.assertEqual(self.store.save('..\\..\\evil:*?"<>|', {}), "evil")
        self.assertTrue((self.store.folder / "evil.json").exists())
        self.assertIsNone(self.store.save("   ", {}))
        self.assertIsNone(self.store.load(""))
        self.assertEqual(len(self.store.save("x" * 200, {})), 64)


class ApiTest(TempAppData):
    def setUp(self):
        super().setUp()
        self.engine = Engine()
        self.installer = FakeInstaller()
        self.api = Api(self.engine, self.store, self.installer)

    def test_clean_target(self):
        self.assertIsNone(clean_target(None))
        self.assertIsNone(clean_target({"kind": "usb", "id": "x"}))
        self.assertIsNone(clean_target({"kind": "hid", "id": ""}))
        self.assertEqual(clean_target({"kind": "crsf", "id": "COM3", "baud": "bad"}), {"kind": "crsf", "id": "COM3", "baud": 420000})
        self.assertEqual(clean_target({"kind": "hid", "id": 5, "baud": 115200}), {"kind": "hid", "id": "5", "baud": 115200})

    def test_first_boot_uses_mode2(self):
        data = self.api.boot()
        self.assertEqual(data["lang"], "")
        self.assertEqual(data["name"], "")
        self.assertIsNone(data["source"])
        self.assertEqual(data["profile"], mapping.normalize_profile(mapping.preset(2, "a")))

    def test_boot_restores_settings(self):
        self.store.save("TX16S", mapping.preset(1, "c"))
        self.store.update(lang="en", profile="TX16S", source={"kind": "crsf", "id": "COM7", "baud": 416666})
        data = self.api.boot()
        self.assertEqual(data["lang"], "en")
        self.assertEqual(data["name"], "TX16S")
        self.assertEqual(data["profile"]["axes"]["ly"]["in"], "c1")
        self.assertEqual(self.engine.target, {"kind": "crsf", "id": "COM7", "baud": 416666})

    def test_boot_ignores_deleted_profile(self):
        self.store.update(profile="gone", lang="de")
        data = self.api.boot()
        self.assertEqual(data["name"], "")
        self.assertEqual(data["lang"], "")

    def test_connect_and_disconnect(self):
        self.assertFalse(self.api.connect({"kind": "nope"}))
        self.assertTrue(self.api.connect({"kind": "hid", "id": "guid:0"}))
        self.assertEqual(self.store.settings()["source"]["id"], "guid:0")
        self.api.disconnect()
        self.assertIsNone(self.engine.target)
        self.assertIsNone(self.store.settings()["source"])

    def test_preset_keeps_calibration(self):
        profile = mapping.blank_profile()
        profile["cal"] = {"c2": [-0.8, 0.9]}
        self.api.set_profile(profile)
        result = self.api.preset(1, "crsf")
        self.assertEqual(result["cal"], {"c2": [-0.8, 0.9]})
        self.assertEqual(result["axes"]["ry"]["in"], "c2")

    def test_save_load_delete_profile(self):
        profile = mapping.preset(2, "c")
        profile["axes"]["lx"]["dz"] = 0.1
        saved = self.api.save_profile("Boxer", profile)
        self.assertEqual(saved, {"name": "Boxer", "profiles": ["Boxer"]})
        self.assertEqual(self.store.settings()["profile"], "Boxer")
        self.api.set_profile(mapping.blank_profile())
        self.assertAlmostEqual(self.api.load_profile("Boxer")["axes"]["lx"]["dz"], 0.1)
        self.assertIsNone(self.api.load_profile("missing"))
        self.assertEqual(self.api.delete_profile("Boxer"), [])
        self.assertEqual(self.store.settings()["profile"], "")

    def test_calibration_flow(self):
        self.api.calibrate_begin()
        self.assertTrue(self.api.state()["calibrating"])
        self.engine.calibration = {"a0": (-0.7, 0.6), "b0": (1.0, 1.0)}
        profile = self.api.calibrate_end()
        self.assertEqual(profile["cal"], {"a0": [-0.7, 0.6]})
        self.assertFalse(self.api.state()["calibrating"])
        self.assertEqual(self.api.calibrate_reset()["cal"], {})

    def test_state_and_driver(self):
        state = self.api.state()
        for key in ("values", "axes", "buttons", "devices", "target", "source", "output", "error", "calibrating", "driver"):
            self.assertIn(key, state)
        self.api.install_driver()
        self.assertEqual(self.installer.started, 1)

    def test_language(self):
        self.api.set_lang("en")
        self.api.set_lang("fr")
        self.assertEqual(self.store.settings()["lang"], "en")


if __name__ == "__main__":
    unittest.main()
