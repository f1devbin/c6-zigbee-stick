"""Constants for C6 Zigbee Stick."""

import logging

DOMAIN = "c6_zigbee_stick"
LOGGER = logging.getLogger(__package__)

# ESP32-C6 built-in USB-Serial/JTAG. Fixed in silicon, so every C6 board looks like this;
# the ZBOSS probe tells our coordinator apart from other ESP32 firmware.
USB_VID = "303A"
USB_PID = "1001"

CONF_DEVICE = "device"  # /dev/serial/by-id/... path
CONF_SERIAL = "serial_number"
CONF_FIRMWARE = "firmware"

ADAPTER = "zboss"

Z2M_NAME = "Zigbee2MQTT"
Z2M_SLUG = "45df7312_zigbee2mqtt"  # app slug from the official repository below
Z2M_REPOSITORY = "https://github.com/zigbee2mqtt/hassio-zigbee2mqtt"
Z2M_DEFAULT_DATA_PATH = "/config/zigbee2mqtt"

MQTT_NAME = "Mosquitto broker"
MQTT_SLUG = "core_mosquitto"

# Written only when Zigbee2MQTT has no configuration yet, so it starts without its
# onboarding page. MQTT is left out on purpose: the app takes it from the broker app.
Z2M_CONFIG_TEMPLATE = """\
# Created by the C6 Zigbee Stick integration. Edit freely; it is never overwritten.
homeassistant:
  enabled: true
frontend:
  enabled: true
serial:
  port: {port}
  adapter: zboss
advanced:
  channel: 20
  transmit_power: 20
  network_key: GENERATE
  pan_id: GENERATE
  ext_pan_id: GENERATE
"""

# Seconds to let a re-plugged stick boot before Zigbee2MQTT opens it again.
REPLUG_DELAY = 5
