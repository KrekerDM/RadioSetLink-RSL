import os
import subprocess
import tempfile
import threading
import urllib.request
import winreg
from pathlib import Path

VERSION = "1.22.0"
FILENAME = f"ViGEmBus_{VERSION}_x64_x86_arm64.exe"
URL = f"https://github.com/nefarius/ViGEmBus/releases/download/v{VERSION}/{FILENAME}"
BUNDLED = Path(__file__).resolve().parent / "drivers" / FILENAME
SERVICE_KEY = r"SYSTEM\CurrentControlSet\Services\ViGEmBus"
SYSTEM_FILE = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "ViGEmBus.sys"
PUBLISHER = "CN=Nefarius Software Solutions e.U."
NO_WINDOW = 0x08000000
BUSY = ("downloading", "verifying", "installing")


class InstallError(Exception):
    pass


def installed():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, SERVICE_KEY):
            return SYSTEM_FILE.exists()
    except OSError:
        return False


def powershell(command):
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        creationflags=NO_WINDOW,
    )


def quoted(path):
    return "'" + str(path).replace("'", "''") + "'"


def trusted(path):
    command = f"$s = Get-AuthenticodeSignature -LiteralPath {quoted(path)}; \"$($s.Status)|$($s.SignerCertificate.Subject)\""
    status, _, subject = powershell(command).stdout.strip().partition("|")
    return status == "Valid" and subject.startswith(PUBLISHER)


class Installer:
    def __init__(self):
        self.lock = threading.Lock()
        self.stage = "installed" if installed() else "missing"
        self.progress = 0.0
        self.error = ""

    def status(self):
        with self.lock:
            if self.stage in ("missing", "failed") and installed():
                self.stage = "installed"
            return {"stage": self.stage, "progress": self.progress, "error": self.error}

    def start(self):
        with self.lock:
            if self.stage in BUSY or self.stage == "installed":
                return
            self.stage = "downloading"
            self.progress = 0.0
            self.error = ""
        threading.Thread(target=self.run, daemon=True).start()

    def set_stage(self, stage):
        with self.lock:
            self.stage = stage

    def run(self):
        try:
            path = BUNDLED if BUNDLED.exists() else self.download()
            self.set_stage("verifying")
            if not trusted(path):
                raise InstallError("signature")
            self.set_stage("installing")
            result = powershell(f"Start-Process -FilePath {quoted(path)} -Verb RunAs -Wait")
            if result.returncode != 0:
                raise InstallError("cancelled")
            if not installed():
                raise InstallError("incomplete")
            self.set_stage("installed")
        except InstallError as error:
            self.fail(str(error))
        except OSError:
            self.fail("download")

    def download(self):
        folder = Path(tempfile.gettempdir()) / "RadioSetLink"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / FILENAME
        partial = folder / f"{FILENAME}.part"
        with urllib.request.urlopen(URL, timeout=30) as response, open(partial, "wb") as file:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while chunk := response.read(65536):
                file.write(chunk)
                done += len(chunk)
                if total:
                    with self.lock:
                        self.progress = done / total
        partial.replace(target)
        return target

    def fail(self, error):
        with self.lock:
            self.stage = "installed" if installed() else "failed"
            self.error = error
