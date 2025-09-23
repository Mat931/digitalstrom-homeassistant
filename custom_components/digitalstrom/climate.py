import logging
from datetime import timedelta
from typing import Any

import async_timeout
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_SLEEP,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_TENTHS, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api.apartment import DigitalstromApartment
from .api.exceptions import InvalidAuth
from .api.zone import DigitalstromZone
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

PRESET_OFF = "off"
PRESET_HOLIDAY = "holiday"
PRESET_PASSIVE_COOLING = "passive_cooling"
PRESET_PASSIVE_COOLING_OFF = "passive_cooling_off"

ID_TO_PRESET: dict[int | None, str] = {
    0: PRESET_OFF,
    1: PRESET_COMFORT,
    2: PRESET_ECO,
    3: PRESET_AWAY,
    4: PRESET_SLEEP,
    5: PRESET_HOLIDAY,
    6: PRESET_PASSIVE_COOLING,
    7: PRESET_PASSIVE_COOLING_OFF,
    9: PRESET_OFF,
    10: PRESET_COMFORT,
    11: PRESET_ECO,
    12: PRESET_AWAY,
    13: PRESET_SLEEP,
    14: PRESET_HOLIDAY,
}

PRESET_TO_SCENE: dict[str, int] = {
    PRESET_OFF: 0,
    PRESET_COMFORT: 1,
    PRESET_ECO: 2,
    PRESET_AWAY: 3,
    PRESET_SLEEP: 4,
    PRESET_HOLIDAY: 5,
    PRESET_PASSIVE_COOLING: 6,
    PRESET_PASSIVE_COOLING_OFF: 7,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate platform."""
    apartment = hass.data[DOMAIN][config_entry.unique_id]["apartment"]
    coordinator = DigitalstromClimateCoordinator(hass, apartment)
    await coordinator.async_config_entry_first_refresh()
    climate_entities = []
    for zone in apartment.zones.values():
        if zone.climate_control_mode == 1:
            climate_entities.append(DigitalstromClimateEntity(coordinator, zone))
        elif zone.climate_control_mode != 0 and zone.climate_control_mode is not None:
            _LOGGER.debug(
                f"Zone '{zone.name}' has temperature control mode {zone.climate_control_mode}. Only PID mode (1) is supported."
            )
    _LOGGER.debug("Adding %i climate entities", len(climate_entities))
    async_add_entities(climate_entities)


class DigitalstromClimateCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass: HomeAssistant, apartment: DigitalstromApartment):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Digitalstrom Climate",
            update_interval=timedelta(seconds=60),
        )
        self.apartment = apartment

    async def _async_update_data(self) -> None:
        try:
            async with async_timeout.timeout(10):
                await self.apartment.get_zone_climate_data()
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err


class DigitalstromClimateEntity(CoordinatorEntity, ClimateEntity):
    def __init__(
        self, coordinator: DigitalstromClimateCoordinator, zone: DigitalstromZone
    ):
        super().__init__(coordinator)
        self.zone = zone
        self._attr_has_entity_name = True
        self._attr_translation_key = "zone_climate"
        self._attr_unique_id: str = (
            f"{self.zone.apartment.dsuid}_zone{self.zone.zone_id}_climate"
        )
        self.entity_id = f"{DOMAIN}.{self.zone.apartment.dsuid}_zone{self.zone.zone_id}"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_max_temp = 35
        self._attr_min_temp = 3
        self._attr_precision = PRECISION_TENTHS
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )
        self._attr_preset_modes = [
            PRESET_COMFORT,
            PRESET_ECO,
            PRESET_AWAY,
            PRESET_SLEEP,
            PRESET_HOLIDAY,
            PRESET_PASSIVE_COOLING,
        ]
        self._enable_turn_on_off_backwards_compatibility = False
        self._target_climate_operation_mode: int | None = None

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return current operation ie. heat, cool, idle."""
        if self.zone.climate_operation_mode in [0, 7, 9]:
            return HVACMode.OFF
        if self.zone.climate_operation_mode in [1, 2, 3, 4, 5]:
            return HVACMode.HEAT
        if self.zone.climate_operation_mode in [6, 8, 10, 11, 12, 13, 14]:
            return HVACMode.COOL
        return None

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation."""
        if self.zone.control_value == 0:
            return HVACAction.IDLE
        if self.zone.climate_operation_mode in [1, 2, 3, 4, 5]:
            return HVACAction.HEATING
        return HVACAction.COOLING

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode."""
        return ID_TO_PRESET.get(self.zone.climate_operation_mode, None)

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.zone.current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self.zone.target_temperature

    def _get_new_climate_operation_mode(
        self, old_climate_operation_mode: int | None, hvac_mode: HVACMode
    ) -> int | None:
        """Calculate new climate operation mode using hvac_mode."""
        if hvac_mode == HVACMode.OFF:
            if old_climate_operation_mode in [6, 7]:
                return 7
            else:
                return 0
        elif hvac_mode == HVACMode.HEAT:
            if old_climate_operation_mode in [10, 11, 12, 13, 14]:
                return old_climate_operation_mode - 9
            elif old_climate_operation_mode not in [1, 2, 3, 4, 5]:
                return 2
        elif hvac_mode == HVACMode.COOL:
            if old_climate_operation_mode in [1, 2, 3, 4, 5]:
                return old_climate_operation_mode + 9
            elif old_climate_operation_mode not in [6, 10, 11, 12, 13, 14]:
                return 6 if old_climate_operation_mode == 7 else 11
        return old_climate_operation_mode

    async def _async_set_climate_operation_mode(
        self, climate_operation_mode: int | None
    ) -> None:
        """Set climate operation mode."""
        self._target_climate_operation_mode = climate_operation_mode
        if climate_operation_mode is None:
            return
        await self.zone.call_scene(climate_operation_mode, 48)
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature (and operation mode if set)."""
        _LOGGER.debug(
            f"async_set_temperature {kwargs} ({self.zone.climate_operation_mode})"
        )
        if self._target_climate_operation_mode is None:
            self._target_climate_operation_mode = self.zone.climate_operation_mode
        new_climate_operation_mode = self._target_climate_operation_mode
        if ATTR_HVAC_MODE in kwargs:
            new_climate_operation_mode = self._get_new_climate_operation_mode(
                self._target_climate_operation_mode, kwargs[ATTR_HVAC_MODE]
            )
        if ATTR_TEMPERATURE in kwargs:
            await self.zone.set_target_temperature(
                kwargs[ATTR_TEMPERATURE], new_climate_operation_mode
            )
            _LOGGER.debug(
                f"set target temperature done ({self.zone.climate_operation_mode})"
            )
        await self._async_set_climate_operation_mode(new_climate_operation_mode)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new operation mode."""
        _LOGGER.debug(
            f"async_set_hvac_mode {hvac_mode} ({self.zone.climate_operation_mode})"
        )
        new_climate_operation_mode = self._get_new_climate_operation_mode(
            self.zone.climate_operation_mode, hvac_mode
        )
        await self._async_set_climate_operation_mode(new_climate_operation_mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        _LOGGER.debug(
            f"async_set_preset_mode {preset_mode} ({self.zone.climate_operation_mode})"
        )
        if preset_mode not in PRESET_TO_SCENE:
            return
        if self.zone.climate_operation_mode is None:
            return
        scene_id = PRESET_TO_SCENE[preset_mode]
        if self.zone.climate_operation_mode >= 9 and scene_id <= 5:
            scene_id += 9
        await self._async_set_climate_operation_mode(scene_id)

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        _LOGGER.debug(f"async_turn_on ({self.zone.climate_operation_mode})")
        if self.zone.climate_operation_mode == 7:
            await self.async_set_preset_mode(PRESET_PASSIVE_COOLING)
        elif self.zone.climate_operation_mode in [0, 9]:
            await self.async_set_preset_mode(PRESET_ECO)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        _LOGGER.debug(f"async_turn_off ({self.zone.climate_operation_mode})")
        if self.zone.climate_operation_mode in [6, 7]:
            await self.async_set_preset_mode(PRESET_PASSIVE_COOLING_OFF)
        else:
            await self.async_set_preset_mode(PRESET_OFF)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.enabled:
            return
        self._target_climate_operation_mode = self.zone.climate_operation_mode
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{self.zone.apartment.dsuid}_zone{self.zone.zone_id}",
                )
            },
            name=self.zone.name,
            model="Zone",
            manufacturer="digitalSTROM",
            suggested_area=self.zone.name,
            via_device=(DOMAIN, self.zone.apartment.dsuid),
        )
