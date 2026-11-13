"""C6 Zigbee Stick: an ESP32-C6 with esp-coordinator firmware, run by Zigbee2MQTT."""

from __future__ import annotations

import json

from homeassistant.components import mqtt, persistent_notification, usb
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.hassio import is_hassio

from .const import (
    ADAPTER,
    CONF_DEVICE,
    CONF_FIRMWARE,
    CONF_SERIAL,
    DOMAIN,
    LOGGER,
    REPLUG_DELAY,
    USB_PID,
    USB_VID,
    Z2M_CONFIG_TEMPLATE,
)
from . import zboss
from .z2m import async_base_topic, async_restart_z2m


def _watch_firmware(hass: HomeAssistant, entry: ConfigEntry, device_id: str) -> None:
    """Keep the firmware version current from Zigbee2MQTT's retained bridge/info message."""
    ieee = zboss.ieee_from_mac(entry.data.get(CONF_SERIAL))

    @callback
    def _bridge_info(msg: mqtt.ReceiveMessage) -> None:
        try:
            coordinator = json.loads(msg.payload).get("coordinator") or {}
        except (ValueError, AttributeError):
            return
        if coordinator.get("type") != ADAPTER:
            return
        if ieee and str(coordinator.get("ieee_address", "")).lower() != ieee:
            return  # another coordinator
        version = (coordinator.get("meta") or {}).get("revision")
        if version and version != entry.data.get(CONF_FIRMWARE):
            hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_FIRMWARE: version})
            dr.async_get(hass).async_update_device(device_id, sw_version=version)

    async def _subscribe() -> None:
        if not hass.config_entries.async_entries("mqtt") or not await mqtt.async_wait_for_mqtt_client(hass):
            return
        topic = f"{await async_base_topic(hass)}/bridge/info"
        entry.async_on_unload(await mqtt.async_subscribe(hass, topic, _bridge_info))

    entry.async_create_background_task(hass, _subscribe(), f"{DOMAIN}_firmware")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Register the stick as a device and watch for it being plugged back in."""
    serial = entry.data.get(CONF_SERIAL)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
        manufacturer="Espressif",
        model="ESP32-C6 Zigbee coordinator (ZBOSS)",
        name="C6 Zigbee Stick",
        sw_version=entry.data.get(CONF_FIRMWARE),
        serial_number=serial,
    )
    _watch_firmware(hass, entry, device.id)

    if not is_hassio(hass):
        persistent_notification.async_create(
            hass,
            "Home Assistant is not managing apps here, so set up Zigbee2MQTT yourself "
            "with this `configuration.yaml` (add your MQTT settings):\n\n```yaml\n"
            + Z2M_CONFIG_TEMPLATE.format(port=entry.data[CONF_DEVICE])
            + "```",
            title="C6 Zigbee Stick",
            notification_id=f"{DOMAIN}_{entry.entry_id}_manual",
        )
        return True

    pending: list = []
    state = {"gone": False}

    def _ours(device: usb.USBDevice) -> bool:
        return (
            device.vid.upper() == USB_VID
            and device.pid.upper() == USB_PID
            and (serial is None or device.serial_number == serial)
        )

    @callback
    def _restart(_now) -> None:
        pending.clear()
        LOGGER.info("C6 Zigbee Stick is back, restarting Zigbee2MQTT")
        hass.async_create_task(async_restart_z2m(hass))

    @callback
    def _port_event(added: set[usb.USBDevice], removed: set[usb.USBDevice]) -> None:
        # The first scan after Home Assistant starts reports every present device as added:
        # only a stick that actually went away and came back needs Zigbee2MQTT restarted.
        if any(_ours(d) for d in removed):
            state["gone"] = True
        if state["gone"] and any(_ours(d) for d in added):
            state["gone"] = False
            # Zigbee2MQTT gives up when the stick disappears; bring it back once it has booted.
            if not pending:
                pending.append(async_call_later(hass, REPLUG_DELAY, _restart))

    entry.async_on_unload(usb.async_register_port_event_callback(hass, _port_event))

    @callback
    def _cancel() -> None:
        for cancel in pending:
            cancel()

    entry.async_on_unload(_cancel)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Nothing runs inside Home Assistant itself; Zigbee2MQTT is left as it is."""
    persistent_notification.async_dismiss(hass, f"{DOMAIN}_{entry.entry_id}_manual")
    return True
