import copy
import threading
import time

import pygame

from . import mapping
from .output import Gamepad
from .sources import CrsfSource, HidSource, hid_devices

TICK = 0.004
RETRY = 1.0


class Engine(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.alive = True
        self.profile = mapping.blank_profile()
        self.target = None
        self.source = None
        self.devices = []
        self.values = {}
        self.axes, self.buttons = mapping.apply(self.profile, {})
        self.output = Gamepad()
        self.want_output = False
        self.error = ""
        self.calibration = None
        self.rescan = True
        self.retry_at = 0.0

    def set_target(self, target):
        with self.lock:
            self.target = target
            self.retry_at = 0.0
            self.error = ""

    def set_profile(self, profile):
        with self.lock:
            self.profile = mapping.normalize_profile(profile)
            return copy.deepcopy(self.profile)

    def get_profile(self):
        with self.lock:
            return copy.deepcopy(self.profile)

    def set_output(self, enabled):
        with self.lock:
            self.want_output = bool(enabled)
            if enabled and self.error in ("driver", "module"):
                self.error = ""

    def begin_calibration(self):
        with self.lock:
            self.calibration = {}

    def end_calibration(self):
        with self.lock:
            measured = self.calibration or {}
            self.calibration = None
            profile = copy.deepcopy(self.profile)
            for key, (low, high) in measured.items():
                if high - low > 0.2:
                    profile["cal"][key] = [low, high]
            self.profile = mapping.normalize_profile(profile)
            return copy.deepcopy(self.profile)

    def reset_calibration(self):
        with self.lock:
            self.calibration = None
            self.profile["cal"] = {}
            return copy.deepcopy(self.profile)

    def snapshot(self):
        with self.lock:
            source = self.source
            return {
                "values": self.values,
                "axes": self.axes,
                "buttons": self.buttons,
                "devices": self.devices,
                "target": self.target,
                "source": {"kind": source.kind, "id": source.id, "name": source.name, "signal": source.signal()} if source else None,
                "output": self.output.active,
                "error": self.error,
                "calibrating": self.calibration is not None,
            }

    def stop(self):
        self.alive = False
        self.join(2)

    def run(self):
        pygame.display.init()
        pygame.joystick.init()
        self.ready.set()
        while self.alive:
            self.step()
            time.sleep(TICK)
        self.output.stop()
        self.drop_source()
        pygame.quit()

    def step(self):
        for event in pygame.event.get():
            if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                self.rescan = True
        if self.rescan:
            self.rescan = False
            devices = hid_devices()
            with self.lock:
                self.devices = devices
            if self.source and self.source.kind == "hid" and all(d["id"] != self.source.id for d in devices):
                self.drop_source()
        self.sync_source()
        self.sync_output()
        values = {}
        if self.source:
            try:
                values = self.source.read()
            except Exception:
                self.drop_source()
        with self.lock:
            profile = self.profile
            if self.calibration is not None:
                for key, value in values.items():
                    low, high = self.calibration.get(key, (value, value))
                    self.calibration[key] = (min(low, value), max(high, value))
        axes, buttons = mapping.apply(profile, values)
        if self.output.active:
            try:
                self.output.send(axes, buttons)
            except Exception:
                self.output.stop()
                with self.lock:
                    self.want_output = False
                    self.error = "output"
        with self.lock:
            self.values = values
            self.axes = axes
            self.buttons = buttons

    def drop_source(self):
        source = self.source
        with self.lock:
            self.source = None
        if source:
            try:
                source.close()
            except Exception:
                pass

    def sync_source(self):
        with self.lock:
            target = self.target
            devices = self.devices
        current = self.source
        if current and (
            target is None
            or current.kind != target["kind"]
            or current.id != target["id"]
            or (current.kind == "crsf" and current.baud != target.get("baud"))
        ):
            self.drop_source()
            current = None
        now = time.monotonic()
        if current or target is None or now < self.retry_at:
            return
        self.retry_at = now + RETRY
        try:
            if target["kind"] == "hid":
                device = next((d for d in devices if d["id"] == target["id"]), None)
                if device is None:
                    return
                source = HidSource(device)
            else:
                source = CrsfSource(target["id"], target["baud"])
        except Exception:
            with self.lock:
                self.error = "open"
            return
        with self.lock:
            self.source = source
            if self.error == "open":
                self.error = ""

    def sync_output(self):
        with self.lock:
            wanted = self.want_output
        if wanted and not self.output.active:
            try:
                self.output.start()
            except OSError:
                self.fail_output("module")
            except Exception:
                self.fail_output("driver")
        elif not wanted and self.output.active:
            self.output.stop()

    def fail_output(self, error):
        self.output.device = None
        with self.lock:
            self.want_output = False
            self.error = error
