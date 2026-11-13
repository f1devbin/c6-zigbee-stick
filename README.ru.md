# C6 Zigbee Stick: Zigbee-координатор на ESP32-C6 для Home Assistant

[🇬🇧 English](README.md)

Zigbee-координатор для Home Assistant из обычной платы **ESP32-C6** за 5 минут, без терминала и ручной правки конфигов.

1. **Прошить** плату из браузера: <https://f1devbin.github.io/c6-zigbee-stick/ru/>
2. **Поставить** интеграцию «C6 Zigbee Stick» через HACS (один раз).
3. **Вставить** стик в компьютер с Home Assistant и нажать «Добавить» на карточке «Обнаружено: C6 Zigbee Stick».

Интеграция сама установит и запустит Zigbee2MQTT (и брокер Mosquitto, если MQTT ещё нет), пропишет порт и тип адаптера и будет поднимать Zigbee2MQTT заново, если стик переподключить.

## Зачем нужна интеграция

Заводские стики (Sonoff, SMLIGHT, ConBee) Home Assistant узнаёт по названию в USB-описании. У ESP32-C6 USB встроен в чип, и его описание прошивкой не меняется: любая C6 выглядит как «Espressif USB JTAG/serial debug unit» (`303a:1001`), будь в ней ESPHome или что-то ещё. Поэтому интеграция откликается на любую C6, но сначала «спрашивает» её по протоколу ZBOSS (команда версии модуля). Не ответила как координатор — интеграция молча пропускает плату.

## Что понадобится

- Плата ESP32-C6 с разъёмом USB (тот, что ведёт прямо в чип; на платах с двумя разъёмами он подписан USB, а не UART/COM). Подойдут ESP32-C6-DevKitC-1, Seeed XIAO ESP32-C6 и аналоги.
- Home Assistant OS или Supervised 2026.11 и новее. На Container/Core интеграция найдёт стик и покажет готовый `configuration.yaml` для Zigbee2MQTT, но ставить Zigbee2MQTT придётся самому.
- Chrome или Edge на компьютере для прошивки.

## Как это устроено

| Часть | Где | Что делает |
|---|---|---|
| Прошивка | [esp-coordinator](https://github.com/tostmann/esp-coordinator) v1.5.80, без изменений, в `docs/firmware` | Zigbee-стек ZBOSS от Espressif, протокол NCP по USB |
| Прошивальщик | `docs/` → GitHub Pages, [ESP Web Tools](https://esphome.github.io/esp-web-tools/) | Прошивка из браузера одной кнопкой |
| Интеграция | `custom_components/c6_zigbee_stick` | Находит стик по USB, проверяет протокол, настраивает и перезапускает Zigbee2MQTT, показывает версию прошивки |
| Zigbee2MQTT | официальное приложение | Работает с адаптером `zboss`, публикует устройства в Home Assistant |

При настройке интеграция:

- добавляет репозиторий приложений Zigbee2MQTT, если его нет;
- ставит и запускает Mosquitto, если в Home Assistant нет MQTT;
- ставит Zigbee2MQTT, прописывает в настройках приложения `serial.port` (путь `/dev/serial/by-id/…`) и `serial.adapter: zboss`, включает автозапуск и сторожа;
- создаёт `zigbee2mqtt/configuration.yaml`, только если его ещё нет (канал 20, мощность 20 дБм, ключи сети генерируются). Существующий файл не трогает.

Если Zigbee2MQTT уже работает с другим адаптером, интеграция его не перехватывает и сообщает об этом.

## Ограничения

- Поддержка адаптера `zboss` в Zigbee2MQTT пока **экспериментальная**: нельзя сменить канал без повторного сопряжения устройств, нет резервной копии сети средствами Zigbee2MQTT, нет install-кодов и touchlink. Подробно — в [документации Zigbee2MQTT](https://www.zigbee2mqtt.io/guide/adapters/zboss.html).
- Встроенный в Home Assistant ZHA этот протокол не поддерживает, поэтому используется Zigbee2MQTT.
- Если Home Assistant работает в виртуальной машине, USB-устройство нужно пробросить в неё с автоматическим переподключением (в Proxmox — «Use USB Vendor/Device ID»; в libvirt — правило udev).

## Разработка

```bash
python -m pytest -q tests      # проверка протокола ZBOSS, Home Assistant не нужен
python tools/build_site.py     # пересобрать страницы прошивальщика (docs/) после правки текста
```

## Лицензия

MIT. Прошивка esp-coordinator — MIT (andryblack, tostmann), см. `docs/firmware/LICENSE-esp-coordinator.txt`; в её составе ESP-IDF и Zigbee SDK от Espressif под их лицензиями.
