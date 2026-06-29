import logging
from datetime import timedelta
from typing import override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api.apartment import DigitalstromApartment

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)

type DigitalstromConfigEntry = ConfigEntry[DigitalstromApartmentStatusCoordinator]


class DigitalstromApartmentStatusCoordinator(DataUpdateCoordinator[None]):

    config_entry: DigitalstromConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: DigitalstromConfigEntry,
        apartment: DigitalstromApartment,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Digitalstrom Apartment Status",
            update_interval=SCAN_INTERVAL,
            config_entry=entry,
        )
        self.apartment = apartment

    @override
    async def _async_update_data(self) -> None:
        await self.apartment.update_apartment_status()
