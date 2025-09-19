from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .api.device import DigitalstromDevice
from .const import DOMAIN


class DigitalstromEntity(Entity):
    """Define a base digitalSTROM entity."""

    def __init__(self, device: DigitalstromDevice, entity_identifier: str):
        """Initialize the entity."""
        self.device = device
        self._attr_unique_id: str = f"{self.device.dsuid}_{entity_identifier}"
        self.entity_id = f"{DOMAIN}.{self._attr_unique_id}"
        self._attr_should_poll = False
        self._has_state = False

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.device.get_parent().register_availability_callback(
                self.availability_callback
            )
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        zone_name = ""
        if (self.device.zone_id is not None) and (
            zone := self.device.apartment.zones.get(self.device.zone_id)
        ):
            zone_name = zone.name
        parent_device = self.device.get_parent()
        device_name = parent_device.name
        if len(device_name) == 0:
            for n in parent_device.unique_device_names:
                if len(n) > 0:
                    device_name = n
                    break
        di = DeviceInfo(
            identifiers={(DOMAIN, parent_device.dsuid)},
            name=device_name,
            manufacturer=parent_device.manufacturer,
            model=parent_device.hw_info,
            # sw_version=parent_device.sw_version,
            suggested_area=zone_name,
        )
        if parent_device.meter_dsuid is not None:
            di["via_device"] = (DOMAIN, parent_device.meter_dsuid)
        return di

    @property
    def available(self) -> bool:
        return self.device.get_parent().available

    def availability_callback(self, available: bool) -> None:
        if not self.enabled:
            return
        self.async_write_ha_state()
