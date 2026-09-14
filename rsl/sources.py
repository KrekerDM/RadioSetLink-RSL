import os
import time

os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import serial
import serial.tools.list_ports

CRSF_ADDRESSES = {0xC8, 0xEA, 0xEC, 0xEE}
CRSF_RC_CHANNELS = 0x16
CRSF_CENTER = 992
CRSF_SPAN = 820
SIGNAL_TIMEOUT = 0.5
VIRTUAL_NAMES = ("xbox", "xinput")


def _crc_table():
    table = []
    for byte in range(256):
        crc = byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0xD5) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
        table.append(crc)
    return table


CRC_TABLE = _crc_table()


def crc8(data):
    crc = 0
    for byte in data:
        crc = CRC_TABLE[crc ^ byte]
    return crc


def hid_devices():
    devices = []
    seen = {}
    for index in range(pygame.joystick.get_count()):
        joystick = pygame.joystick.Joystick(index)
        name = joystick.get_name()
        if any(part in name.lower() for part in VIRTUAL_NAMES):
            continue
        guid = joystick.get_guid()
        copy = seen.get(guid, 0)
        seen[guid] = copy + 1
        devices.append({
            "id": f"{guid}:{copy}",
            "name": name if copy == 0 else f"{name} ({copy + 1})",
            "index": index,
        })
    return devices


def serial_ports():
    ports = []
    for port in sorted(serial.tools.list_ports.comports(), key=lambda p: p.device):
        description = port.description or ""
        name = description if port.device in description else f"{port.device} {description}".strip()
        ports.append({"id": port.device, "name": name})
    return ports


class HidSource:
    kind = "hid"

    def __init__(self, device):
        self.id = device["id"]
        self.name = device["name"]
        self.baud = None
        self.joystick = pygame.joystick.Joystick(device["index"])

    def read(self):
        joystick = self.joystick
        values = {}
        for index in range(joystick.get_numaxes()):
            values[f"a{index}"] = joystick.get_axis(index)
        for index in range(joystick.get_numhats()):
            x, y = joystick.get_hat(index)
            values[f"h{index}x"] = float(x)
            values[f"h{index}y"] = float(y)
        for index in range(joystick.get_numbuttons()):
            values[f"b{index}"] = 1.0 if joystick.get_button(index) else -1.0
        return values

    def signal(self):
        return True

    def close(self):
        pass


class CrsfSource:
    kind = "crsf"

    def __init__(self, port, baud):
        self.id = port
        self.name = port
        self.baud = baud
        self.port = serial.Serial(port, baud, timeout=0)
        self.buffer = bytearray()
        self.values = {}
        self.last = 0.0

    def read(self):
        waiting = self.port.in_waiting
        if waiting:
            self.buffer += self.port.read(waiting)
        buffer = self.buffer
        while len(buffer) >= 4:
            if buffer[0] not in CRSF_ADDRESSES:
                del buffer[0]
                continue
            size = buffer[1]
            if size < 2 or size > 62:
                del buffer[0]
                continue
            if len(buffer) < size + 2:
                break
            frame = bytes(buffer[2:size + 2])
            if crc8(frame[:-1]) != frame[-1]:
                del buffer[0]
                continue
            del buffer[:size + 2]
            if frame[0] == CRSF_RC_CHANNELS and size == 24:
                self._decode(frame[1:23])
        if len(buffer) > 1024:
            buffer.clear()
        return self.values if self.signal() else {}

    def _decode(self, payload):
        bits = int.from_bytes(payload, "little")
        values = {}
        for index in range(16):
            raw = (bits >> (11 * index)) & 0x7FF
            values[f"c{index}"] = max(-1.0, min(1.0, (raw - CRSF_CENTER) / CRSF_SPAN))
        self.values = values
        self.last = time.monotonic()

    def signal(self):
        return time.monotonic() - self.last < SIGNAL_TIMEOUT

    def close(self):
        self.port.close()
