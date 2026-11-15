Новое оформление. Работа с пультом, драйвером и профилями не менялась,
профили из 1.1.0 подхватываются.

## Изменено

- Фон ровный тёмно-серый вместо чёрного, заголовки крупные и обычного веса.
- Шрифты Golos Text и PT Mono вместо Jost и Cascadia Mono, оба вшиты в
  программу.
- Жёлтого акцента больше нет. Цвет остался один, коралловый, и помечает только
  отклонение: нет сигнала, ошибку, отсутствующий драйвер. Включённое состояние
  и нажатые кнопки показаны светлой заливкой.
- Надписи набраны обычным регистром, а не строчными. Кнопки геймпада подписаны
  A, B, X, Y, LB и RB, как на контроллере.
- В ряду модулей под шапкой нет значков, остались названия и числа.
- Цифры внутри названий вроде TX16S или PS4 Controller набраны тем же шрифтом,
  что и буквы. Моноширинным шрифтом идут только отдельные числа.

Худший контраст текста 4.94:1 при норме WCAG AA 4.5:1.

## Установка

Скачайте `RadioSetLink.exe` и запустите, Python и библиотеки не нужны. Профили
и настройки хранятся в `%APPDATA%\RadioSetLink`.

Windows SmartScreen может предупредить о неизвестном издателе, потому что
сборка не подписана сертификатом. «Подробнее» → «Выполнить в любом случае».

Нужны Windows 10 или 11, 64 бита, и Microsoft Edge WebView2 Runtime, в
Windows 11 он уже есть.

---
## English

A new look. Radio, driver and profile handling did not change, and profiles
from 1.1.0 carry over.

## Changed

- A flat dark grey background instead of black, with large headings in regular
  weight.
- Golos Text and PT Mono instead of Jost and Cascadia Mono, both bundled.
- The yellow accent is gone. One colour is left, coral, and it marks only a
  deviation: no signal, an error, a missing driver. An enabled state and pressed
  buttons take a light fill.
- Text keeps its normal case instead of lower case everywhere. The gamepad
  buttons read A, B, X, Y, LB and RB, as on the controller.
- The module row under the header has no icons, only names and numbers.
- Digits inside names such as TX16S or PS4 Controller use the same face as the
  letters. Only free-standing numbers are set in the monospaced face.

Worst text contrast 4.94:1 against the WCAG AA 4.5:1 minimum.

## Install

Download `RadioSetLink.exe` and run it, no Python or libraries needed. Profiles
and settings live in `%APPDATA%\RadioSetLink`.

Windows SmartScreen may warn about an unknown publisher, because the build is
not code signed. More info → Run anyway.

Requires Windows 10 or 11, 64-bit, and the Microsoft Edge WebView2 Runtime,
which Windows 11 already has.
