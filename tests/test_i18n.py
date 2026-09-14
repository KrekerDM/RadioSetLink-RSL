import json
import re
import unittest
from pathlib import Path

UI = Path(__file__).resolve().parent.parent / "rsl" / "ui"


def dictionaries():
    source = (UI / "i18n.js").read_text("utf-8")
    body = source[source.index("{"):source.rindex("}") + 1]
    body = re.sub(r",(\s*[}\]])", r"\1", body)
    body = re.sub(r"^(\s*)(ru|en):", r'\1"\2":', body, flags=re.M)
    return json.loads(body)


class TranslationTest(unittest.TestCase):
    def setUp(self):
        self.i18n = dictionaries()

    def test_languages_have_same_keys(self):
        self.assertEqual(set(self.i18n["ru"]), set(self.i18n["en"]))

    def test_no_duplicate_keys(self):
        source = (UI / "i18n.js").read_text("utf-8")
        for block in re.split(r"^\s*en:\s*\{", source, flags=re.M):
            keys = re.findall(r'^\s*"([^"]+)":', block, flags=re.M)
            self.assertEqual(len(keys), len(set(keys)), [k for k in keys if keys.count(k) > 1])

    def test_placeholders_match(self):
        for key, text in self.i18n["ru"].items():
            self.assertEqual(set(re.findall(r"\{\w+\}", text)), set(re.findall(r"\{\w+\}", self.i18n["en"][key])), key)

    def test_all_used_keys_exist(self):
        html = (UI / "index.html").read_text("utf-8")
        script = (UI / "app.js").read_text("utf-8")
        used = set(re.findall(r'data-i18n="([^"]+)"', html))
        prefixes = {key.split(".")[0] for key in self.i18n["en"]}
        used |= {key for key in re.findall(r'"([a-z]+\.[a-zA-Z]+)"', script) if key.split(".")[0] in prefixes}
        missing = sorted(key for key in used if key not in self.i18n["en"])
        self.assertEqual(missing, [])

    def test_dynamic_keys_exist(self):
        for group, names in {
            "out": ("lx", "ly", "rx", "ry", "lt", "rt", "a", "b", "x", "y", "lb", "rb", "back", "start", "ls", "rs", "up", "down", "left", "right", "guide"),
            "when": ("high", "mid", "low"),
            "err": ("driver", "module", "open", "output"),
            "driver": ("downloading", "verifying", "installing", "installed", "err.download", "err.signature", "err.cancelled", "err.incomplete"),
        }.items():
            for name in names:
                self.assertIn(f"{group}.{name}", self.i18n["en"])


if __name__ == "__main__":
    unittest.main()
