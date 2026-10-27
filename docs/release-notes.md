Новый вид и исправления по итогам проверки. Логика работы с пультом и драйвером
не менялась, профили из 1.0.0 подхватываются.

## Изменено

- **Тема module из стандарта Lodd** — плоский чёрный фон без фотографии и
  стекла, один жёлтый акцент `#ffcc00`, шрифт Jost в начертаниях 200 и 300,
  строчные буквы. Худший контраст текста 5.14:1 при норме WCAG AA 4.5:1.
- **Ряд модулей под шапкой** — источник, профиль, каналы, геймпад, раскладка и
  драйвер с текущими числами. Отклонение вроде «нет сигнала» помечено отдельным
  цветом, щелчок по модулю ведёт к его разделу.
- **Разделы с номерами 01–06** вместо карточек.
- **Шаблон Mode 2 или Mode 1** выбирается в списке и применяется кнопкой. Под
  списком сказано, что остальная раскладка при этом сбрасывается.
- **Удаление профиля** просит второе нажатие в течение 3 секунд.
- **Профиль с несохранёнными правками** помечен словом «изменён».
- **Значение каждой оси** видно числом рядом со столбиком, у мёртвой зоны и
  экспо стоит знак процента.

## Исправлено

- Ошибка запуска геймпада раньше печаталась в разделе 01, вне экрана. Теперь
  она стоит под шапкой.
- Окно драйвера при установленном драйвере писало в заголовке, что драйвер
  нужен.
- Сбой запуска установщика раньше выдавался за ошибку загрузки.

## Установка

Скачайте `RadioSetLink.exe` и запустите, Python и библиотеки не нужны. Профили
и настройки хранятся в `%APPDATA%\RadioSetLink`.

Windows SmartScreen может предупредить о неизвестном издателе, потому что
сборка не подписана сертификатом. «Подробнее» → «Выполнить в любом случае».

Нужны Windows 10 или 11, 64 бита, и Microsoft Edge WebView2 Runtime, в
Windows 11 он уже есть.

---
## English

A new look and fixes from a review pass. Radio and driver handling did not
change, and profiles from 1.0.0 carry over.

## Changed

- **Module theme of the Lodd standard** — a flat black background with no photo
  and no glass, one yellow accent `#ffcc00`, the Jost font in weights 200 and
  300, lower case everywhere. Worst text contrast 5.14:1 against the WCAG AA
  4.5:1 minimum.
- **A row of modules under the header** — source, profile, channels, gamepad,
  mapping and driver with live numbers. Deviations such as "no signal" get their
  own colour, and a click on a module jumps to its section.
- **Numbered sections 01–06** instead of cards.
- **The Mode 2 or Mode 1 preset** is picked from a list and applied with a
  button. The line under it says that the rest of the mapping is reset.
- **Deleting a profile** needs a second click within 3 seconds.
- **A profile with unsaved edits** is marked "changed".
- **Each axis value** shows as a number next to its bar, deadzone and expo
  carry a percent sign.

## Fixed

- A gamepad start error used to print in section 01, off screen. It now sits
  under the header.
- With the driver installed, the driver dialog title still said the driver was
  required.
- A failed installer launch used to be reported as a download error.

## Install

Download `RadioSetLink.exe` and run it, no Python or libraries needed. Profiles
and settings live in `%APPDATA%\RadioSetLink`.

Windows SmartScreen may warn about an unknown publisher, because the build is
not code signed. More info → Run anyway.

Requires Windows 10 or 11, 64-bit, and the Microsoft Edge WebView2 Runtime,
which Windows 11 already has.
