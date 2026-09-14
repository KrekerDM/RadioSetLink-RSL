import time
import unittest
from unittest import mock

import serial

from rsl import sources


def channels_frame(values):
    bits = 0
    for index, value in enumerate(values):
        bits |= value << (11 * index)
    payload = bytes([sources.CRSF_RC_CHANNELS]) + bits.to_bytes(22, "little")
    return bytes([0xC8, len(payload) + 1]) + payload + bytes([sources.crc8(payload)])


def telemetry_frame():
    payload = bytes([0x14]) + bytes(10)
    return bytes([0xEA, len(payload) + 1]) + payload + bytes([sources.crc8(payload)])


def loop_port(port, baud, timeout):
    return serial.serial_for_url("loop://", baudrate=baud, timeout=timeout)


class CrcTest(unittest.TestCase):
    def test_known_value(self):
        self.assertEqual(sources.crc8(b"123456789"), 0xBC)


class CrsfSourceTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(sources.serial, "Serial", loop_port)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.source = sources.CrsfSource("COM99", 420000)
        self.addCleanup(self.source.close)

    def feed(self, data):
        self.source.port.write(data)
        return self.source.read()

    def test_no_data_means_no_signal(self):
        self.assertEqual(self.source.read(), {})
        self.assertFalse(self.source.signal())

    def test_decodes_sixteen_channels(self):
        raw = [172, 1811, 992, 582, 1402] + [992] * 11
        values = self.feed(channels_frame(raw))
        self.assertEqual(len(values), 16)
        self.assertEqual(values["c0"], -1.0)
        self.assertAlmostEqual(values["c1"], 1.0, places=2)
        self.assertEqual(values["c2"], 0.0)
        self.assertAlmostEqual(values["c3"], -0.5)
        self.assertAlmostEqual(values["c4"], 0.5)
        self.assertTrue(self.source.signal())

    def test_out_of_range_raw_is_clamped(self):
        values = self.feed(channels_frame([0, 2047] + [992] * 14))
        self.assertEqual(values["c0"], -1.0)
        self.assertEqual(values["c1"], 1.0)

    def test_resyncs_after_garbage_and_telemetry(self):
        frame = channels_frame([1811] + [992] * 15)
        values = self.feed(b"\x00\xff\x13\xc8" + telemetry_frame() + frame)
        self.assertAlmostEqual(values["c0"], 1.0, places=2)

    def test_bad_crc_is_ignored(self):
        frame = bytearray(channels_frame([1811] + [992] * 15))
        frame[-1] ^= 0xFF
        self.assertEqual(self.feed(bytes(frame)), {})

    def test_frame_split_across_reads(self):
        frame = channels_frame([172] + [992] * 15)
        self.assertEqual(self.feed(frame[:10]), {})
        self.assertEqual(self.feed(frame[10:])["c0"], -1.0)

    def test_signal_times_out(self):
        self.feed(channels_frame([992] * 16))
        self.source.last = time.monotonic() - sources.SIGNAL_TIMEOUT - 0.1
        self.assertEqual(self.source.read(), {})
        self.assertFalse(self.source.signal())


if __name__ == "__main__":
    unittest.main()
