[Русский](README.md) · **English**

# RadioSetLink

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Input](https://img.shields.io/badge/Input-USB%20HID%20%7C%20CRSF-2EA043)
![Output](https://img.shields.io/badge/Output-Xbox%20360%20via%20ViGEmBus-107C10)
![UI](https://img.shields.io/badge/GUI-pywebview-5C3EE8?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-555555)

A drone or FPV radio as an Xbox 360 gamepad. Plenty of games and simulators do
not see a radio at all or mix up its axes. RadioSetLink reads the radio over USB,
or an ExpressLRS receiver over a COM port, and creates a regular Xbox
controller that any game with gamepad support understands.

![Main window](docs/screenshot-main-en.png)

## What it does

- **USB joystick** — EdgeTX, OpenTX, Radiomaster, Jumper, FrSky and other radios
  in USB Joystick mode.
- **CRSF over a COM port** — an ExpressLRS or Crossfire receiver on a USB-UART
  adapter, 420000 baud by default.
- **Mode 2 and Mode 1 presets** — the standard stick layout in one click.
- **Assign by moving** — press Assign and move the stick or switch, the channel
  is filled in for you.
- **Invert, deadzone and expo** — per axis.
- **Switches as buttons** — high, middle or low position, so a three-position
  switch can press three different buttons.
- **Calibration** — stick end points are stored in the profile, so a throttle
  without a spring still reaches full travel.
- **Profiles** — a separate layout for every radio or game.
- **Live view** — radio channels next to what the virtual gamepad receives.
- **Reconnect** — a radio that was unplugged and plugged back in is picked up
  automatically.
- **Driver setup from the app** — if ViGEmBus is missing, RadioSetLink offers to
  install it.
- **Russian and English** interface, switchable without a restart.

## Quick start

### Ready-made build

Download `RadioSetLink.exe` from [releases](../../releases/latest) and run it.
No Python needed, and the driver installer is already inside.

### From source

```bash
python -m venv .venv
```

```bash
.venv\Scripts\pip install -r requirements.txt
```

```bash
.venv\Scripts\python.exe main.py
```

Needs Python 3.10 or newer and Windows 10 or 11.

## Preparing the radio

**EdgeTX or OpenTX radio.** Plug the radio in and pick "USB Joystick (HID)" in
the menu that appears. Channels CH1–CH8 arrive as axes in AETR order: aileron,
elevator, throttle, rudder, then the switches.

**ExpressLRS receiver.** Wire the receiver to a USB-UART adapter: receiver TX to
adapter RX, 5 V and ground. The receiver has to be bound to the radio. In the
app pick "CRSF over COM port" and the adapter's port.

## Usage

1. Pick the connection type and device, press Connect. The bars under Radio
   channels start moving with the sticks.
2. Press Calibrate, move every stick and switch to its end points, press Done.
3. Apply the Mode 2 or Mode 1 preset. If an axis moves the wrong way, tick
   Invert. Buttons work the same way: Assign, then flick the switch.
4. Save the profile and press Start gamepad. The game will see an Xbox 360
   controller.

![Mapping](docs/screenshot-mapping-en.png)

## ViGEmBus driver

The virtual gamepad is created by the [ViGEmBus](https://github.com/nefarius/ViGEmBus)
driver. If it is missing, a setup dialog opens on start. The app takes the
installer from the build, or when running from source downloads it from the
official releases page, checks the Nefarius Software Solutions digital
signature and runs it with an administrator prompt.

![Driver setup](docs/screenshot-driver-en.png)

## How it works

```
rsl/
  app.py        pywebview window and engine start-up
  api.py        methods the interface calls
  engine.py     polling thread: source → mapping → gamepad
  sources.py    USB joystick through SDL and CRSF over a COM port
  mapping.py    profile, calibration, deadzone, expo, button conditions
  output.py     Xbox 360 report from axes and buttons
  vigem.py      ViGEmClient.dll through ctypes
  driver.py     ViGEmBus detection, download and setup
  store.py      profiles and settings in %APPDATA%\RadioSetLink
  ui/           interface, theme, backdrop, translations, icon
  bin/          ViGEmClient.dll for x64 and x86
tests/          automated tests, including an end-to-end one through XInput
docs/           screenshots, screenshot script, GitHub texts
assets/         icon and backdrop generators
build_exe.py    exe build
```

**Polling.** The engine runs in its own thread with a 4 ms step. Every step it
reads the source, scales all channels to −1…1, applies calibration and the
profile, and sends a report to the virtual gamepad only when something changed.

**CRSF.** The `0x16` channels frame carries 16 values of 11 bits each. The app
finds frame starts in the byte stream, checks CRC8 with polynomial `0xD5` and
skips telemetry and noise. If no frame arrives for 0.5 s, outputs return to
neutral.

**Calibration.** While calibrating, the minimum and maximum of every channel are
recorded, and that span is then stretched over the full range. A throttle
resting at the bottom becomes zero in the middle and one at the top.

## Tests

```bash
.venv\Scripts\python.exe -m unittest discover -s tests -t .
```

The end-to-end test creates a virtual DualShock 4 in place of a radio, runs it
through RadioSetLink and reads the virtual Xbox 360 back through XInput. It is
skipped without ViGEmBus. The screenshots are made the same way, which is why
the device list shows "PS4 Controller".

## Building the exe

```bash
.venv\Scripts\pip install pyinstaller
```

```bash
.venv\Scripts\python.exe build_exe.py
```

The result is `release\RadioSetLink.exe`. The script downloads the ViGEmBus
installer, checks its signature and bundles it into the exe. The icon is
regenerated by `assets\make_icon.py`, the backdrop by `assets\make_backdrop.py`,
screenshots by `docs\make_screenshots.py`.

## Limitations

- Windows only: the virtual gamepad is built on ViGEmBus.
- The output is a single Xbox 360 controller. Games that only understand
  DirectInput or the keyboard will not see it.
- Some online games with anti-cheat reject virtual controllers.
- CRSF needs a receiver on a USB-UART adapter. Modules and radios that expose
  CRSF some other way have not been tested.
- Verified with an end-to-end test on a virtual controller. Reports about real
  radios and receivers are welcome in [issues](../../issues).
- The build is not code signed, so Windows SmartScreen warns about an unknown
  publisher on first launch.

## License

MIT — see [LICENSE](LICENSE).

The look follows the Frostpane design system. `ViGEmClient.dll` comes from [vgamepad](https://github.com/yannbouteiller/vgamepad)
(MIT, `rsl/bin/LICENSE-vgamepad`) and belongs to the
[ViGEm](https://github.com/nefarius/ViGEmClient) project. The ViGEmBus driver
belongs to Nefarius Software Solutions and is not part of this repository.
