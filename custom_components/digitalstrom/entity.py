from homeassistant.helpers.entity import DeviceInfo, Entity

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

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        zone_name = ""
        if zone := self.device.apartment.zones.get(self.device.zone_id):
            zone_name = zone.name
        parent_device = self.device.get_parent()
        device_name = parent_device.name
        if len(device_name) == 0:
            for n in parent_device.unique_device_names:
                if len(n) > 0:
                    device_name = n
                    break
        return DeviceInfo(
            identifiers={(DOMAIN, parent_device.dsuid)},
            name=device_name,
            manufacturer=parent_device.manufacturer,
            model=parent_device.hw_info,
            # sw_version=parent_device.sw_version,
            via_device=(DOMAIN, parent_device.meter_dsuid),
            suggested_area=zone_name,
        )

    @property
    def available(self) -> bool:
        return self.device.available
