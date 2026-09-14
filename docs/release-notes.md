Первая версия. Программа для Windows, которая превращает пульт дрона или FPV-аппаратуру в геймпад Xbox 360 — для игр и симуляторов, которые не видят пульт напрямую.

## Возможности

- **Два источника** — пульт в режиме USB Joystick (EdgeTX, OpenTX и другие) и приёмник ExpressLRS или Crossfire по CRSF через COM-порт.
- **Раскладка** — шаблоны Mode 2 и Mode 1, назначение канала движением стика, инверсия, мёртвая зона и экспо для каждой оси.
- **Тумблеры как кнопки** — верхнее, среднее или нижнее положение.
- **Калибровка и профили** — крайние положения сохраняются, под каждый пульт свой профиль.
- **Живой просмотр** — каналы пульта рядом с тем, что получает геймпад, индикатор сигнала в шапке.
- **Установка драйвера из программы** — если ViGEmBus нет, программа предложит его поставить: установщик уже внутри exe, перед запуском проверяется его цифровая подпись.
- **Русский и английский** интерфейс.

## Установка

Скачайте `RadioSetLink.exe` и запустите — Python и библиотеки не нужны. Профили и настройки хранятся в `%APPDATA%\RadioSetLink`.

При первом запуске программа проверит драйвер ViGEmBus и, если его нет, предложит установить. Windows попросит права администратора.

Windows SmartScreen может предупредить о неизвестном издателе: сборка не подписана сертификатом. «Подробнее» → «Выполнить в любом случае».

**Требования:** Windows 10 или 11, 64 бита, Microsoft Edge WebView2 Runtime (в Windows 11 уже есть).

---
## English

First release. A Windows app that turns a drone or FPV radio into an Xbox 360 gamepad, for games and simulators that do not see a radio directly.

## Features

- **Two sources** — a radio in USB Joystick mode (EdgeTX, OpenTX and others) and an ExpressLRS or Crossfire receiver over CRSF on a COM port.
- **Mapping** — Mode 2 and Mode 1 presets, assign a channel by moving the stick, invert, deadzone and expo per axis.
- **Switches as buttons** — high, middle or low position.
- **Calibration and profiles** — end points are stored, one profile per radio.
- **Live view** — radio channels next to what the gamepad receives, a signal indicator in the header.
- **Driver setup from the app** — if ViGEmBus is missing, the app offers to install it: the installer is bundled in the exe and its digital signature is checked before it runs.
- **Russian and English** interface.

## Install

Download `RadioSetLink.exe` and run it — no Python or libraries needed. Profiles and settings live in `%APPDATA%\RadioSetLink`.

On first launch the app checks for the ViGEmBus driver and offers to install it if missing. Windows will ask for administrator rights.

Windows SmartScreen may warn about an unknown publisher — the build is not code signed. More info → Run anyway.

**Requirements:** Windows 10 or 11, 64-bit, Microsoft Edge WebView2 Runtime (already part of Windows 11).
