import ctypes
import time
import unittest

from rsl import mapping
from rsl.driver import installed
from rsl.engine import Engine
from rsl.output import report, thumb, trigger
from rsl.vigem import Ds4Report, DualShock4

TIMEOUT = 5.0


class XinputState(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", ctypes.c_uint),
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


XINPUT = ctypes.WinDLL("xinput1_4")


def xinput(index):
    state = XinputState()
    return state if XINPUT.XInputGetState(index, ctypes.byref(state)) == 0 else None


def connected():
    return {index for index in range(4) if xinput(index)}


def wait_for(predicate, timeout=TIMEOUT):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        result = predicate()
        if result:
            return result
        time.sleep(0.02)
    return predicate()


class ReportTest(unittest.TestCase):
    def test_scaling(self):
        self.assertEqual(thumb(1.0), 32767)
        self.assertEqual(thumb(-1.0), -32767)
        self.assertEqual(thumb(5.0), 32767)
        self.assertEqual(trigger(0.5), 128)
        self.assertEqual(trigger(-1.0), 0)

    def test_buttons_bitmask(self):
        axes = dict.fromkeys(mapping.AXES, 0.0)
        buttons = dict.fromkeys(mapping.BUTTONS, False)
        buttons.update(a=True, up=True, guide=True)
        self.assertEqual(report(axes, buttons).wButtons, 0x1000 | 0x0001 | 0x0400)


@unittest.skipUnless(installed(), "ViGEmBus is not installed")
class EndToEndTest(unittest.TestCase):
    def setUp(self):
        self.radio = DualShock4()
        self.addCleanup(self.radio.close)
        self.state = Ds4Report(bThumbLX=128, bThumbLY=128, bThumbRX=128, bThumbRY=128, wButtons=0x8)
        self.radio.send(self.state)
        self.engine = Engine()
        self.engine.start()
        self.addCleanup(self.engine.stop)
        self.assertTrue(self.engine.ready.wait(TIMEOUT))

    def push(self, **fields):
        for key, value in fields.items():
            setattr(self.state, key, value)
        self.radio.send(self.state)

    def radio_device(self):
        return next((d for d in self.engine.snapshot()["devices"] if "xbox" not in d["name"].lower()), None)

    def settle(self, check):
        return wait_for(lambda: check(self.engine.snapshot()["values"]))

    def moved(self, before, after):
        return max(after, key=lambda key: abs(after[key] - before.get(key, after[key])))

    def test_radio_to_xbox(self):
        device = wait_for(self.radio_device)
        self.assertIsNotNone(device, self.engine.snapshot()["devices"])
        self.engine.set_target({"kind": "hid", "id": device["id"], "baud": 420000})
        self.assertTrue(wait_for(lambda: self.engine.snapshot()["source"]))
        self.assertTrue(self.settle(lambda values: len(values) >= 4))

        rest = dict(self.engine.snapshot()["values"])
        self.push(bThumbLX=255)
        self.settle(lambda values: any(abs(values[k] - rest[k]) > 0.8 for k in values if k.startswith("a")))
        roll = self.moved(rest, self.engine.snapshot()["values"])
        self.push(bThumbLX=128)
        self.settle(lambda values: abs(values[roll] - rest[roll]) < 0.1)

        self.push(bThumbLY=0)
        self.settle(lambda values: any(abs(values[k] - rest[k]) > 0.8 for k in values if k.startswith("a") and k != roll))
        throttle = self.moved(rest, self.engine.snapshot()["values"])
        self.push(bThumbLY=128)
        self.settle(lambda values: abs(values[throttle] - rest[throttle]) < 0.1)

        self.push(wButtons=0x8 | 0x20)
        self.settle(lambda values: any(values[k] > 0 for k in values if k.startswith("b")))
        switch = next(k for k, v in self.engine.snapshot()["values"].items() if k.startswith("b") and v > 0)
        self.push(wButtons=0x8)

        self.assertNotEqual(roll, throttle)
        profile = mapping.blank_profile()
        profile["axes"]["rx"]["in"] = roll
        profile["axes"]["ly"]["in"] = throttle
        profile["axes"]["ly"]["inv"] = True
        profile["axes"]["rt"]["in"] = roll
        profile["buttons"]["a"]["in"] = switch
        self.engine.set_profile(profile)

        before = connected()
        self.engine.set_output(True)
        pad = wait_for(lambda: next(iter(connected() - before), None))
        self.assertIsNotNone(pad, "virtual Xbox 360 pad did not appear in XInput")
        self.assertEqual(self.engine.snapshot()["error"], "")

        self.push(bThumbLX=255, bThumbLY=0, wButtons=0x8 | 0x20)
        state = wait_for(lambda: (s := xinput(pad)) and s.sThumbRX > 30000 and s.sThumbLY > 30000 and s.wButtons & 0x1000 and s)
        self.assertTrue(state, vars_of(xinput(pad)))
        self.assertEqual(state.bRightTrigger, 255)

        self.push(bThumbLX=0, bThumbLY=255, wButtons=0x8)
        state = wait_for(lambda: (s := xinput(pad)) and s.sThumbRX < -30000 and s.sThumbLY < -30000 and not s.wButtons & 0x1000 and s)
        self.assertTrue(state, vars_of(xinput(pad)))
        self.assertEqual(state.bRightTrigger, 0)

        self.engine.set_output(False)
        self.assertTrue(wait_for(lambda: pad not in connected()))


def vars_of(state):
    return {name: getattr(state, name) for name, _ in XinputState._fields_} if state else None


if __name__ == "__main__":
    unittest.main()
