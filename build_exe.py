import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from rsl import __version__
from rsl.driver import BUNDLED, URL, trusted

NAME = "RadioSetLink"
DIST = ROOT / "release"
WORK = ROOT / "build"
ICON = ROOT / "rsl" / "ui" / "logo.ico"
EXCLUDES = ("tkinter", "unittest", "pydoc", "numpy", "PIL", "matplotlib", "PySide6", "PyQt5", "PyQt6")

VERSION_INFO = """VSVersionInfo(
  ffi=FixedFileInfo(filevers={numbers}, prodvers={numbers}),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'KrekerDM'),
      StringStruct('FileDescription', 'RadioSetLink'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'RadioSetLink'),
      StringStruct('LegalCopyright', 'MIT License'),
      StringStruct('OriginalFilename', 'RadioSetLink.exe'),
      StringStruct('ProductName', 'RadioSetLink'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def fetch_driver():
    if BUNDLED.exists() and trusted(BUNDLED):
        return True
    print("Скачиваю установщик ViGEmBus")
    BUNDLED.parent.mkdir(parents=True, exist_ok=True)
    partial = BUNDLED.with_suffix(".part")
    with urllib.request.urlopen(URL, timeout=60) as response, open(partial, "wb") as file:
        file.write(response.read())
    partial.replace(BUNDLED)
    if not trusted(BUNDLED):
        BUNDLED.unlink()
        print("У установщика нет действительной подписи Nefarius, сборка остановлена.")
        return False
    return True


def version_file():
    numbers = tuple(int(part) for part in __version__.split(".")) + (0,)
    path = WORK / "version.txt"
    WORK.mkdir(parents=True, exist_ok=True)
    path.write_text(VERSION_INFO.format(numbers=numbers, version=__version__), "utf-8")
    return path


def build(clean):
    separator = ";"
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", NAME,
        "--icon", str(ICON),
        "--version-file", str(version_file()),
        "--distpath", str(DIST),
        "--workpath", str(WORK),
        "--specpath", str(WORK),
        "--add-data", f"{ROOT / 'rsl' / 'ui'}{separator}rsl/ui",
        "--add-data", f"{ROOT / 'rsl' / 'bin'}{separator}rsl/bin",
        "--add-data", f"{BUNDLED.parent}{separator}rsl/drivers",
    ]
    if clean:
        args.append("--clean")
    for module in EXCLUDES:
        args += ["--exclude-module", module]
    args.append(str(ROOT / "main.py"))

    print(f"Собираю {NAME} {__version__}")
    started = time.time()
    result = subprocess.run(args, cwd=ROOT)
    if result.returncode != 0:
        print("\nСборка не удалась.")
        return result.returncode

    exe = DIST / f"{NAME}.exe"
    print(f"\nГотово за {time.time() - started:.0f} с")
    print(f"Результат: {exe}")
    print(f"Размер: {exe.stat().st_size / 1024 / 1024:.0f} МБ")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Сборка RadioSetLink в exe")
    parser.add_argument("--clean", action="store_true", help="очистить кеш PyInstaller перед сборкой")
    args = parser.parse_args()
    if not fetch_driver():
        return 1
    DIST.mkdir(exist_ok=True)
    return build(args.clean)


if __name__ == "__main__":
    sys.exit(main())
