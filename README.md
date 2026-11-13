# C6 Zigbee Stick: ESP32-C6 Zigbee coordinator for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Validate](https://github.com/f1devbin/c6-zigbee-stick/actions/workflows/validate.yml/badge.svg)](https://github.com/f1devbin/c6-zigbee-stick/actions/workflows/validate.yml)

[🇷🇺 Русский](README.ru.md)

Turn an ordinary **ESP32-C6** board into a plug-and-play **Zigbee coordinator for Home Assistant** in five minutes: no terminal, no YAML, no manual Zigbee2MQTT setup.

1. **Flash** the board from your browser: **<https://f1devbin.github.io/c6-zigbee-stick/>**
2. **Install** the “C6 Zigbee Stick” integration through HACS (once):

   [![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=f1devbin&repository=c6-zigbee-stick&category=integration)
3. **Plug** the stick into the Home Assistant machine and press “Add” on the “Discovered: C6 Zigbee Stick” card.

The integration installs and starts Zigbee2MQTT (and the Mosquitto broker if there is no MQTT yet), sets the port and adapter type, and restarts Zigbee2MQTT when the stick is plugged back in.

## Why an integration is needed

Home Assistant recognises retail sticks (Sonoff, SMLIGHT, ConBee) by the name in their USB descriptor. The ESP32-C6 has USB built into the chip and firmware cannot change that descriptor: every C6 shows up as “Espressif USB JTAG/serial debug unit” (`303a:1001`), whether it runs ESPHome or anything else. So the integration reacts to any C6, but first asks it for its module version over the ZBOSS protocol. If the board does not answer as a coordinator, it is silently skipped.

## What you need

- An ESP32-C6 board with a USB connector wired to the chip (on two-connector boards it is labelled USB, not UART/COM): ESP32-C6-DevKitC-1, Seeed XIAO ESP32-C6 and similar.
- Home Assistant OS or Supervised 2026.11 or later. On Container/Core the integration still finds the stick and shows a ready `configuration.yaml` for Zigbee2MQTT, but you install Zigbee2MQTT yourself.
- Chrome or Edge on a computer for flashing.

## How it works

| Part | Where | What it does |
|---|---|---|
| Firmware | [esp-coordinator](https://github.com/tostmann/esp-coordinator) v1.5.80, unmodified, in `docs/firmware` | Espressif's ZBOSS Zigbee stack, NCP protocol over USB |
| Flasher | `docs/` → GitHub Pages, [ESP Web Tools](https://esphome.github.io/esp-web-tools/) | One-button flashing from the browser |
| Integration | `custom_components/c6_zigbee_stick` | Finds the stick on USB, checks the protocol, configures and restarts Zigbee2MQTT, shows the firmware version |
| Zigbee2MQTT | official app | Runs the `zboss` adapter and exposes devices to Home Assistant |

During setup the integration:

- adds the Zigbee2MQTT app repository if it is missing;
- installs and starts Mosquitto if Home Assistant has no MQTT;
- installs Zigbee2MQTT, sets the app options `serial.port` (a `/dev/serial/by-id/…` path) and `serial.adapter: zboss`, turns on start at boot and the watchdog;
- creates `zigbee2mqtt/configuration.yaml` only if there is none yet (channel 20, 20 dBm, generated network keys). An existing file is never touched.

If Zigbee2MQTT already runs with another adapter, the integration leaves it alone and says so.

## Limitations

- Zigbee2MQTT's `zboss` adapter support is still **experimental**: changing the channel means re-pairing devices, and there are no Zigbee2MQTT network backups, install codes or touchlink. See the [Zigbee2MQTT docs](https://www.zigbee2mqtt.io/guide/adapters/zboss.html).
- Home Assistant's built-in ZHA does not support this protocol, hence Zigbee2MQTT.
- If Home Assistant runs in a virtual machine, pass the USB device through with automatic re-attach (Proxmox: “Use USB Vendor/Device ID”; libvirt: a udev rule).

## Development

```bash
python -m pytest -q tests      # ZBOSS protocol tests, no Home Assistant needed
python tools/build_site.py     # rebuild the flasher pages (docs/) after changing their text
```

## License

MIT. The esp-coordinator firmware is MIT (andryblack, tostmann), see `docs/firmware/LICENSE-esp-coordinator.txt`; it contains Espressif's ESP-IDF and Zigbee SDK under their licenses.
