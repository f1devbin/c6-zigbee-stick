"""Config flow: the stick is found on USB, checked, and Zigbee2MQTT is set up for it."""

from __future__ import annotations

import asyncio
from os.path import realpath
from typing import Any

from aiohasupervisor import SupervisorError

from homeassistant.components import usb
from homeassistant.components.hassio import AddonError
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.hassio import is_hassio
from homeassistant.helpers.service_info.usb import UsbServiceInfo

from . import zboss
from .const import ADAPTER, CONF_DEVICE, CONF_FIRMWARE, CONF_SERIAL, DOMAIN, LOGGER, USB_PID, USB_VID
from .z2m import async_current_serial, async_setup_z2m

TITLE = "C6 Zigbee Stick"


def _same_port(a: str | None, b: str | None) -> bool:
    """Compare two serial paths, following /dev/serial/by-id links (blocking: run in executor)."""
    if not a or not b:
        return False
    return a == b or realpath(a) == realpath(b)


class C6ZigbeeStickConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for C6 Zigbee Stick."""

    VERSION = 1

    def __init__(self) -> None:
        self._device: str | None = None
        self._serial: str | None = None
        self._firmware: str | None = None
        self._setup_task: asyncio.Task | None = None
        self._error: str | None = None

    async def _async_check(self, device: str, serial: str | None) -> str | None:
        """Probe the port. Returns an abort reason, or None when it is our stick."""
        try:
            version = await self.hass.async_add_executor_job(zboss.probe, device)
        except zboss.PortBusy:
            # Zigbee2MQTT may already be talking to it (set up by hand earlier): adopt it.
            current = await async_current_serial(self.hass)
            if current.get("adapter") == ADAPTER and await self.hass.async_add_executor_job(
                _same_port, current.get("port"), device
            ):
                self._firmware = None  # filled in later from Zigbee2MQTT's bridge/info
            else:
                return "port_busy"
        else:
            if version is None:
                return "not_zboss"
            self._firmware = version.firmware

        current = await async_current_serial(self.hass)
        other = current.get("port")
        if other and not await self.hass.async_add_executor_job(_same_port, other, device):
            # Zigbee2MQTT already runs on another adapter: do not take it over.
            return "z2m_other_adapter"

        self._device = device
        self._serial = serial
        return None

    async def async_step_usb(self, discovery_info: UsbServiceInfo) -> ConfigFlowResult:
        """A matching USB device was plugged in."""
        device = await self.hass.async_add_executor_job(usb.get_serial_by_id, discovery_info.device)
        serial = discovery_info.serial_number or device
        await self.async_set_unique_id(serial)
        self._abort_if_unique_id_configured(updates={CONF_DEVICE: device})

        if reason := await self._async_check(device, discovery_info.serial_number):
            # Silent for USB discovery: other ESP32 boards share this USB id.
            return self.async_abort(reason=reason)

        self.context["title_placeholders"] = {"name": TITLE}
        return await self.async_step_confirm()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Started by hand: look for the stick among the serial ports."""
        ports = await usb.async_scan_serial_ports(self.hass)
        candidates = [
            p
            for p in ports
            if getattr(p, "vid", None) and p.vid.upper() == USB_VID and p.pid.upper() == USB_PID
        ]
        if not candidates:
            return self.async_abort(reason="no_devices_found")

        last_reason = "not_zboss"
        for port in candidates:
            device = await self.hass.async_add_executor_job(usb.get_serial_by_id, port.device)
            serial = port.serial_number or device
            if serial in self._async_current_ids(include_ignore=False):
                continue
            if reason := await self._async_check(device, port.serial_number):
                last_reason = reason
                continue
            await self.async_set_unique_id(serial)
            return await self.async_step_confirm()
        return self.async_abort(reason=last_reason)

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show what was found and what will be done."""
        if user_input is not None:
            if not is_hassio(self.hass):
                return self._async_create()
            return await self.async_step_setup_z2m()

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "device": self._device or "",
                "firmware": self._firmware or "ZBOSS",
            },
        )

    async def async_step_setup_z2m(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Install, configure and start Zigbee2MQTT, with a progress spinner."""
        if not self._setup_task:
            self._setup_task = self.hass.async_create_task(async_setup_z2m(self.hass, self._device))

        if not self._setup_task.done():
            return self.async_show_progress(
                step_id="setup_z2m",
                progress_action="setup_z2m",
                progress_task=self._setup_task,
            )

        try:
            await self._setup_task
        except (AddonError, SupervisorError) as err:
            LOGGER.error("Zigbee2MQTT setup failed: %s", err)
            self._error = str(err)
            return self.async_show_progress_done(next_step_id="setup_failed")
        finally:
            self._setup_task = None
        return self.async_show_progress_done(next_step_id="finish")

    async def async_step_setup_failed(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Zigbee2MQTT could not be set up."""
        return self.async_abort(reason="z2m_setup_failed", description_placeholders={"error": self._error or ""})

    async def async_step_finish(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Everything is running."""
        return self._async_create()

    def _async_create(self) -> ConfigFlowResult:
        return self.async_create_entry(
            title=TITLE,
            data={CONF_DEVICE: self._device, CONF_SERIAL: self._serial, CONF_FIRMWARE: self._firmware},
        )
