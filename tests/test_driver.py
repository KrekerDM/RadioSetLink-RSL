import sys
import unittest
from pathlib import Path

from rsl import driver


class TrustTest(unittest.TestCase):
    def test_unsigned_file_is_rejected(self):
        self.assertFalse(driver.trusted(Path(__file__)))

    def test_file_from_other_publisher_is_rejected(self):
        self.assertFalse(driver.trusted(Path(sys.executable).parent / "python.exe"))

    @unittest.skipUnless(driver.BUNDLED.exists(), "bundled installer is not downloaded")
    def test_bundled_installer_is_trusted(self):
        self.assertTrue(driver.trusted(driver.BUNDLED))

    def test_quotes_are_escaped(self):
        self.assertEqual(driver.quoted("C:\\it's"), "'C:\\it''s'")


if __name__ == "__main__":
    unittest.main()
