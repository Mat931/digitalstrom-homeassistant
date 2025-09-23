import asyncio
import logging
from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.circuit import DigitalstromCircuit
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the update platform."""
    apartment = hass.data[DOMAIN][config_entry.unique_id]["apartment"]
    update_entities = []
    for circuit in apartment.circuits.values():
        update_entities.append(DigitalstromUpdateEntity(circuit))
    _LOGGER.debug("Adding %i update entities", len(update_entities))
    async_add_entities(update_entities)


class DigitalstromUpdateEntity(UpdateEntity):
    """Entity representing the update state."""

    def __init__(self, circuit: DigitalstromCircuit) -> None:
        """Initialize the update entity."""
        self.circuit = circuit
        self._attr_unique_id: str = f"{self.circuit.dsuid}_firmware"
        self.entity_id = f"{DOMAIN}.{self._attr_unique_id}"
        self._attr_name = "Firmware"
        self._attr_has_entity_name = True
        self._attr_device_class = UpdateDeviceClass.FIRMWARE
        self._attr_supported_features = (
            UpdateEntityFeature.INSTALL | UpdateEntityFeature.RELEASE_NOTES
        )
        self._attr_in_progress = False
        self._attr_should_poll = True
        self._attr_installed_version = self.circuit.sw_version

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.circuit.dsuid)},
            name=self.circuit.name,
            manufacturer=self.circuit.manufacturer,
            model=self.circuit.hw_name,
            hw_version=self.circuit.hw_version,
            sw_version=self.circuit.sw_version,
        )

    @property
    def available(self) -> bool:
        return self.circuit.available

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install an update."""
        _LOGGER.debug(f"{self.circuit.name}: Starting update")
        self._attr_in_progress = True
        await self.circuit.install_update()
        while (status := await self.circuit.update_available()) != "ok":
            _LOGGER.debug(
                f"{self.circuit.name}: Received status during update: {status}"
            )
            await asyncio.sleep(10)
        _LOGGER.debug(f"{self.circuit.name}: Update done")
        await self.circuit.apartment.get_circuits()
        self._attr_in_progress = False

    async def async_update(self) -> None:
        """Update entity state.

        Update in_progress, installed_version and latest_version.
        """
        status = await self.circuit.update_available()
        self._attr_installed_version = self.circuit.sw_version
        self._attr_latest_version = (
            "Needs Update" if status == "update" else self.circuit.sw_version
        )

    async def async_release_notes(self) -> str | None:
        """Return the release notes."""
        return f'This will attempt to install an update on the device "{self.circuit.name}".\n\nWarning: Updating devices through Home Assistant is experimental and wasn\'t tested on a real system. If there are any problems with the update process, please open an issue on [GitHub](https://github.com/Mat931/digitalstrom-homeassistant/issues).'
