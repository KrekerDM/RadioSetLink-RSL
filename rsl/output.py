from .vigem import XUSB_BUTTONS, Xbox360, XusbReport


def thumb(value):
    return int(round(max(-1.0, min(1.0, value)) * 32767))


def trigger(value):
    return int(round(max(0.0, min(1.0, value)) * 255))


def report(axes, buttons):
    return XusbReport(
        wButtons=sum(bit for key, bit in XUSB_BUTTONS.items() if buttons.get(key)),
        bLeftTrigger=trigger(axes["lt"]),
        bRightTrigger=trigger(axes["rt"]),
        sThumbLX=thumb(axes["lx"]),
        sThumbLY=thumb(axes["ly"]),
        sThumbRX=thumb(axes["rx"]),
        sThumbRY=thumb(axes["ry"]),
    )


class Gamepad:
    def __init__(self):
        self.device = None
        self.last = None

    @property
    def active(self):
        return self.device is not None

    def start(self):
        self.device = Xbox360()
        self.last = None

    def send(self, axes, buttons):
        current = report(axes, buttons)
        state = bytes(current)
        if state == self.last:
            return
        self.device.send(current)
        self.last = state

    def stop(self):
        if self.device is None:
            return
        try:
            self.device.send(XusbReport())
        finally:
            self.device.close()
            self.device = None
            self.last = None
