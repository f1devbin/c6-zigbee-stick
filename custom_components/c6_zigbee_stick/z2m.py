"""Zigbee2MQTT app (add-on) handling through the Supervisor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohasupervisor.models import AddonBoot, AddonsOptions, StoreAddRepository
import yaml

from homeassistant.components.hassio import AddonError, AddonManager, AddonState
from homeassistant.components.hassio.handler import get_supervisor_client
from homeassistant.core import HomeAssistant
from homeassistant.helpers.hassio import is_hassio

from .const import (
    ADAPTER,
    LOGGER,
    MQTT_NAME,
    MQTT_SLUG,
    Z2M_CONFIG_TEMPLATE,
    Z2M_DEFAULT_DATA_PATH,
    Z2M_NAME,
    Z2M_REPOSITORY,
    Z2M_SLUG,
)

DEFAULT_BASE_TOPIC = "zigbee2mqtt"
DATA_MANAGERS = "c6_zigbee_stick_addon_managers"


class _LenientLoader(yaml.SafeLoader):
    """SafeLoader that reads !secret and other tags as plain values."""


_LenientLoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def _manager(hass: HomeAssistant, name: str, slug: str) -> AddonManager:
    """One AddonManager per app, as Home Assistant requires."""
    managers: dict[str, AddonManager] = hass.data.setdefault(DATA_MANAGERS, {})
    if slug not in managers:
        managers[slug] = AddonManager(hass, LOGGER, name, slug)
    return managers[slug]


def _config_file(hass: HomeAssistant, options: dict[str, Any]) -> Path | None:
    """Zigbee2MQTT's configuration.yaml as seen from Home Assistant, if it is reachable."""
    data_path = options.get("data_path") or Z2M_DEFAULT_DATA_PATH
    if not data_path.startswith("/config/"):
        return None  # e.g. /addon_config, not visible from Home Assistant Core
    return Path(hass.config.path(data_path.removeprefix("/config/"))) / "configuration.yaml"


def _read_section(path: Path | None, section: str) -> dict[str, Any]:
    """One top-level section of Zigbee2MQTT's configuration.yaml ({} if unreadable)."""
    if path is None or not path.exists():
        return {}
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=_LenientLoader) or {}
    except (OSError, yaml.YAMLError):
        return {}
    value = data.get(section) if isinstance(data, dict) else None
    return value if isinstance(value, dict) else {}


async def async_current_serial(hass: HomeAssistant) -> dict[str, Any]:
    """Port and adapter Zigbee2MQTT is set to use ({} when it is not installed or not set).

    App options win over configuration.yaml, as they do inside the app.
    """
    if not is_hassio(hass):
        return {}
    info = await _manager(hass, Z2M_NAME, Z2M_SLUG).async_get_addon_info()
    if info.state == AddonState.NOT_INSTALLED:
        return {}
    from_file = await hass.async_add_executor_job(_read_section, _config_file(hass, info.options), "serial")
    from_options = info.options.get("serial") or {}
    return {**from_file, **{k: v for k, v in from_options.items() if v}}


async def async_base_topic(hass: HomeAssistant) -> str:
    """MQTT base topic of Zigbee2MQTT (its default when it cannot be read)."""
    topic = None
    if is_hassio(hass):
        try:
            info = await _manager(hass, Z2M_NAME, Z2M_SLUG).async_get_addon_info()
        except AddonError:
            info = None
        if info and info.state != AddonState.NOT_INSTALLED:
            topic = (info.options.get("mqtt") or {}).get("base_topic")
            if not topic:
                mqtt = await hass.async_add_executor_job(_read_section, _config_file(hass, info.options), "mqtt")
                topic = mqtt.get("base_topic")
    return topic if isinstance(topic, str) and topic else DEFAULT_BASE_TOPIC


async def _ensure_repository(hass: HomeAssistant) -> None:
    client = get_supervisor_client(hass)
    repos = await client.store.repositories_list()
    if not any(r.source.rstrip("/") == Z2M_REPOSITORY for r in repos):
        LOGGER.info("Adding the Zigbee2MQTT app repository")
        await client.store.add_repository(StoreAddRepository(repository=Z2M_REPOSITORY))


async def _ensure_broker(hass: HomeAssistant) -> None:
    """Install and start Mosquitto unless Home Assistant already talks to some MQTT broker."""
    if hass.config_entries.async_entries("mqtt"):
        return
    broker = _manager(hass, MQTT_NAME, MQTT_SLUG)
    info = await broker.async_get_addon_info()
    if info.state == AddonState.NOT_INSTALLED:
        LOGGER.info("Installing Mosquitto broker")
        await broker.async_install_addon()
        info = await broker.async_get_addon_info()
    if info.state != AddonState.RUNNING:
        await broker.async_start_addon()


def _write_config_if_missing(path: Path, port: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(Z2M_CONFIG_TEMPLATE.format(port=port), encoding="utf-8")
    return True


async def async_setup_z2m(hass: HomeAssistant, port: str) -> None:
    """Make Zigbee2MQTT run on this stick: install what is missing, point it at the port, start.

    Raises AddonError or SupervisorError on failure.
    """
    await _ensure_repository(hass)
    await _ensure_broker(hass)

    z2m = _manager(hass, Z2M_NAME, Z2M_SLUG)
    info = await z2m.async_get_addon_info()
    if info.state == AddonState.NOT_INSTALLED:
        LOGGER.info("Installing Zigbee2MQTT")
        await z2m.async_install_addon()
        info = await z2m.async_get_addon_info()

    options = dict(info.options)
    options["serial"] = {**(options.get("serial") or {}), "port": port, "adapter": ADAPTER}
    await z2m.async_set_addon_options(options)
    # Start with Home Assistant, come back after a crash.
    await get_supervisor_client(hass).addons.set_addon_options(
        Z2M_SLUG, AddonsOptions(boot=AddonBoot.AUTO, watchdog=True)
    )

    path = _config_file(hass, options)
    if path is not None and await hass.async_add_executor_job(_write_config_if_missing, path, port):
        LOGGER.info("Wrote %s", path)

    if info.state == AddonState.RUNNING:
        await z2m.async_restart_addon()
    else:
        await z2m.async_start_addon()


async def async_restart_z2m(hass: HomeAssistant) -> None:
    """Restart Zigbee2MQTT if it is installed (used after the stick is plugged back in)."""
    if not is_hassio(hass):
        return
    z2m = _manager(hass, Z2M_NAME, Z2M_SLUG)
    try:
        info = await z2m.async_get_addon_info()
        if info.state == AddonState.NOT_INSTALLED:
            return
        if info.state == AddonState.RUNNING:
            await z2m.async_restart_addon()
        else:
            await z2m.async_start_addon()
    except AddonError as err:
        LOGGER.warning("Could not restart Zigbee2MQTT: %s", err)
