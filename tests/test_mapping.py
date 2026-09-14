import unittest

from rsl import mapping


def profile_with(axes=None, buttons=None, cal=None):
    profile = mapping.blank_profile()
    for key, cfg in (axes or {}).items():
        profile["axes"][key].update(cfg)
    for key, cfg in (buttons or {}).items():
        profile["buttons"][key].update(cfg)
    profile["cal"] = cal or {}
    return mapping.normalize_profile(profile)


class NormalizeTest(unittest.TestCase):
    def test_garbage_gives_blank_profile(self):
        for data in (None, [], "x", 5, {"axes": "bad", "buttons": 3, "cal": []}):
            self.assertEqual(mapping.normalize_profile(data), mapping.blank_profile())

    def test_values_are_clamped_and_typed(self):
        profile = mapping.normalize_profile({
            "axes": {"lx": {"in": "a0", "inv": 1, "dz": 9, "expo": "nan"}, "ly": {"dz": -1, "expo": "0.4"}},
            "buttons": {"a": {"in": "b0", "when": "sideways"}, "b": {"when": "low"}},
            "cal": {"a0": [-0.9, 0.8], "a1": [0.5, 0.5], "a2": "bad", "a3": [1]},
        })
        self.assertEqual(profile["axes"]["lx"], {"in": "a0", "inv": True, "dz": 0.5, "expo": 0.0})
        self.assertEqual(profile["axes"]["ly"]["dz"], 0.0)
        self.assertAlmostEqual(profile["axes"]["ly"]["expo"], 0.4)
        self.assertEqual(profile["buttons"]["a"], {"in": "b0", "when": "high"})
        self.assertEqual(profile["buttons"]["b"]["when"], "low")
        self.assertEqual(profile["cal"], {"a0": [-0.9, 0.8]})

    def test_every_output_present(self):
        profile = mapping.normalize_profile({})
        self.assertEqual(tuple(profile["axes"]), mapping.AXES)
        self.assertEqual(tuple(profile["buttons"]), mapping.BUTTONS)


class PresetTest(unittest.TestCase):
    def test_mode2(self):
        axes = mapping.preset(2, "a")["axes"]
        self.assertEqual([axes[k]["in"] for k in ("lx", "ly", "rx", "ry")], ["a3", "a2", "a0", "a1"])

    def test_mode1(self):
        axes = mapping.preset(1, "c")["axes"]
        self.assertEqual([axes[k]["in"] for k in ("lx", "ly", "rx", "ry")], ["c3", "c1", "c0", "c2"])

    def test_switches_on_face_buttons(self):
        buttons = mapping.preset(2, "c")["buttons"]
        self.assertEqual([buttons[k]["in"] for k in ("a", "b", "x", "y")], ["c4", "c5", "c6", "c7"])


class ApplyTest(unittest.TestCase):
    def test_unmapped_outputs_are_neutral(self):
        axes, buttons = mapping.apply(mapping.blank_profile(), {"a0": 1.0})
        self.assertTrue(all(v == 0.0 for v in axes.values()))
        self.assertFalse(any(buttons.values()))

    def test_missing_input_is_neutral(self):
        axes, _ = mapping.apply(profile_with(axes={"lx": {"in": "a9"}}), {"a0": 1.0})
        self.assertEqual(axes["lx"], 0.0)

    def test_stick_passthrough_and_invert(self):
        profile = profile_with(axes={"lx": {"in": "a0"}, "ly": {"in": "a0", "inv": True}})
        axes, _ = mapping.apply(profile, {"a0": 0.6})
        self.assertAlmostEqual(axes["lx"], 0.6)
        self.assertAlmostEqual(axes["ly"], -0.6)

    def test_stick_deadzone_rescales(self):
        profile = profile_with(axes={"lx": {"in": "a0", "dz": 0.2}})
        self.assertEqual(mapping.apply(profile, {"a0": 0.15})[0]["lx"], 0.0)
        self.assertAlmostEqual(mapping.apply(profile, {"a0": 0.6})[0]["lx"], 0.5)
        self.assertAlmostEqual(mapping.apply(profile, {"a0": -1.0})[0]["lx"], -1.0)

    def test_stick_expo_keeps_ends(self):
        profile = profile_with(axes={"lx": {"in": "a0", "expo": 1.0}})
        self.assertAlmostEqual(mapping.apply(profile, {"a0": 0.5})[0]["lx"], 0.125)
        self.assertAlmostEqual(mapping.apply(profile, {"a0": 1.0})[0]["lx"], 1.0)
        self.assertAlmostEqual(mapping.apply(profile, {"a0": -1.0})[0]["lx"], -1.0)

    def test_values_outside_range_are_clamped(self):
        profile = profile_with(axes={"lx": {"in": "a0"}})
        self.assertEqual(mapping.apply(profile, {"a0": 3.0})[0]["lx"], 1.0)

    def test_trigger_from_bipolar_channel(self):
        profile = profile_with(axes={"lt": {"in": "c2"}, "rt": {"in": "c2", "inv": True}})
        axes, _ = mapping.apply(profile, {"c2": -1.0})
        self.assertEqual(axes["lt"], 0.0)
        self.assertEqual(axes["rt"], 1.0)
        axes, _ = mapping.apply(profile, {"c2": 0.0})
        self.assertAlmostEqual(axes["lt"], 0.5)

    def test_trigger_deadzone(self):
        profile = profile_with(axes={"lt": {"in": "c2", "dz": 0.1}})
        self.assertEqual(mapping.apply(profile, {"c2": -0.85})[0]["lt"], 0.0)
        self.assertAlmostEqual(mapping.apply(profile, {"c2": 1.0})[0]["lt"], 1.0)

    def test_button_conditions(self):
        profile = profile_with(buttons={"a": {"in": "c4", "when": "high"}, "b": {"in": "c4", "when": "mid"}, "x": {"in": "c4", "when": "low"}})
        cases = {-1.0: (False, False, True), 0.0: (False, True, False), 1.0: (True, False, False)}
        for value, expected in cases.items():
            _, buttons = mapping.apply(profile, {"c4": value})
            self.assertEqual((buttons["a"], buttons["b"], buttons["x"]), expected, value)

    def test_calibration_stretches_range(self):
        profile = profile_with(axes={"lx": {"in": "a0"}}, cal={"a0": [-0.5, 0.5]})
        self.assertAlmostEqual(mapping.apply(profile, {"a0": 0.5})[0]["lx"], 1.0)
        self.assertAlmostEqual(mapping.apply(profile, {"a0": 0.0})[0]["lx"], 0.0)
        self.assertAlmostEqual(mapping.apply(profile, {"a0": -0.25})[0]["lx"], -0.5)

    def test_calibration_centers_offset_throttle(self):
        profile = profile_with(axes={"ly": {"in": "a2"}}, cal={"a2": [0.0, 1.0]})
        self.assertAlmostEqual(mapping.apply(profile, {"a2": 0.0})[0]["ly"], -1.0)
        self.assertAlmostEqual(mapping.apply(profile, {"a2": 1.0})[0]["ly"], 1.0)


if __name__ == "__main__":
    unittest.main()
