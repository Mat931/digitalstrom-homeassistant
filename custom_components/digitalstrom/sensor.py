import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    DEGREE,
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfMass,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSoundPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api.channel import DigitalstromMeterSensorChannel, DigitalstromSensorChannel
from .api.zone import DigitalstromZone
from .climate import DigitalstromClimateCoordinator
from .const import DOMAIN
from .entity import DigitalstromEntity

if TYPE_CHECKING:
    # Typing helper to avoid runtime import cycles when annotating zone references.
    from .api.zone import DigitalstromZone

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

SENSORS_MAP: dict[int, SensorEntityDescription] = {
    -1: SensorEntityDescription(
        key="unknown",
        name="Unknown sensor",
        translation_key="unknown_sensor",
    ),
    4: SensorEntityDescription(
        key="4",
        name="Active Power",
        translation_key="active_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    5: SensorEntityDescription(
        key="5",
        name="Output Current",
        translation_key="output_current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    6: SensorEntityDescription(
        key="6",
        name="Energy",
        translation_key="energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    9: SensorEntityDescription(
        key="9",
        name="Room Temperature",
        translation_key="room_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    10: SensorEntityDescription(
        key="10",
        name="Outdoor Temperature",
        translation_key="outdoor_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    11: SensorEntityDescription(
        key="11",
        name="Room Brightness",
        translation_key="room_brightness",
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    12: SensorEntityDescription(
        key="12",
        name="Outdoor Brightness",
        translation_key="outdoor_brightness",
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    13: SensorEntityDescription(
        key="13",
        name="Room Relative Humidity",
        translation_key="room_relative_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    14: SensorEntityDescription(
        key="14",
        name="Outdoor Relative Humidity",
        translation_key="outdoor_relative_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    15: SensorEntityDescription(
        key="15",
        name="Air pressure",
        translation_key="air_pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    16: SensorEntityDescription(
        key="16",
        name="Wind gust speed",
        translation_key="wind_gust_speed",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    17: SensorEntityDescription(
        key="17",
        name="Wind gust direction",
        translation_key="wind_gust_direction",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    18: SensorEntityDescription(
        key="18",
        name="Wind speed average",
        translation_key="wind_speed_average",
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    19: SensorEntityDescription(
        key="19",
        name="Wind direction",
        translation_key="wind_direction",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    20: SensorEntityDescription(
        key="20",
        name="Precipitation intensity of last hour",
        translation_key="precipitation_intensity_of_last_hour",
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    21: SensorEntityDescription(
        key="21",
        name="Room Carbon Dioxide Concentration",
        translation_key="room_carbon_dioxide_concentration",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    22: SensorEntityDescription(
        key="22",
        name="Room Carbon Monoxide Concentration",
        translation_key="room_carbon_monoxide_concentration",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    25: SensorEntityDescription(
        key="25",
        name="Sound Pressure Level",
        translation_key="sound_pressure_level",
        native_unit_of_measurement=UnitOfSoundPressure.DECIBEL,
        device_class=SensorDeviceClass.SOUND_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    50: SensorEntityDescription(
        key="50",
        name="Room Temperature Set Point",
        translation_key="room_temperature_set_point",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    51: SensorEntityDescription(
        key="51",
        name="Room Temperature Control Variable",
        translation_key="room_temperature_control_variable",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    64: SensorEntityDescription(
        key="64",
        name="Output Current",
        translation_key="output_current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    65: SensorEntityDescription(
        key="65",
        name="Apparent Power",
        translation_key="apparent_power",
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    66: SensorEntityDescription(
        key="66",
        name="Temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    67: SensorEntityDescription(
        key="67",
        name="Brightness",
        translation_key="brightness",
        native_unit_of_measurement=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    68: SensorEntityDescription(
        key="68",
        name="Relative Humidity",
        translation_key="relative_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    69: SensorEntityDescription(
        key="69",
        name="Generated Active Power",
        translation_key="generated_active_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    70: SensorEntityDescription(
        key="70",
        name="Generated Energy",
        translation_key="generated_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    71: SensorEntityDescription(
        key="71",
        name="Water Quantity",
        translation_key="water_quantity",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    72: SensorEntityDescription(
        key="72",
        name="Water Flow Rate",
        translation_key="water_flow_rate",
        # Conversion from "L/s" to CUBIC_METERS_PER_HOUR: (value * 3.6)
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    73: SensorEntityDescription(
        key="73",
        name="Length",
        translation_key="length",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    74: SensorEntityDescription(
        key="74",
        name="Mass",
        translation_key="mass",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    75: SensorEntityDescription(
        key="75",
        name="Time",
        translation_key="time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    76: SensorEntityDescription(
        key="76",
        name="Sun azimuth",
        translation_key="sun_azimuth",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    77: SensorEntityDescription(
        key="77",
        name="Sun elevation",
        translation_key="sun_elevation",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    apartment = hass.data[DOMAIN][config_entry.unique_id]["apartment"]
    
    sensors = []
    for device in apartment.devices.values():
        for sensor in device.sensors.values():
            sensors.append(DigitalstromSensor(sensor))
    _LOGGER.debug("Adding %i sensors", len(sensors))
    async_add_entities(sensors)
    
    zone_coordinator: DigitalstromClimateCoordinator | None = hass.data[DOMAIN][
        config_entry.unique_id
    ].get("climate_coordinator")
    if zone_coordinator is None:
        # Create a shared climate coordinator for zone state so sensor and climate stay aligned.
        zone_coordinator = DigitalstromClimateCoordinator(hass, apartment)
        hass.data[DOMAIN][config_entry.unique_id]["climate_coordinator"] = (
            zone_coordinator
        )
        await zone_coordinator.async_config_entry_first_refresh()
    else:
        # Refresh existing coordinator to fetch latest control values before adding sensors.
        await zone_coordinator.async_request_refresh()
    zone_sensors: list[DigitalstromZoneControlValueSensor] = []
    for zone in apartment.zones.values():
        if zone.climate_control_mode == 1:
            zone_sensors.append(
                DigitalstromZoneControlValueSensor(zone_coordinator, zone)
            )
    _LOGGER.debug("Adding %i zone sensors", len(zone_sensors))
    async_add_entities(zone_sensors)
    
    circuit_sensors = []
    for circuit in apartment.circuits.values():
        for sensor in circuit.sensors.values():
            circuit_sensors.append(DigitalstromMeterSensor(sensor))
    _LOGGER.debug("Adding %i circuit sensors", len(circuit_sensors))
    async_add_entities(circuit_sensors)

class DigitalstromSensor(SensorEntity, DigitalstromEntity):
    def __init__(self, sensor_channel: DigitalstromSensorChannel):
        super().__init__(sensor_channel.device, f"S{sensor_channel.index}")
        self._attributes: dict[str, Any] = {}
        self._state: float | None = None
        self.channel = sensor_channel
        self.index = sensor_channel.index
        self.set_type(sensor_channel.sensor_type)
        self._attr_suggested_display_precision = 1
        self.entity_id = f"{DOMAIN}.{self.device.dsuid}_{self.index}"

    def set_type(self, sensor_type: int) -> None:
        self.sensor_type = sensor_type
        self.entity_description = SENSORS_MAP.get(sensor_type, SENSORS_MAP[-1])
        self._attr_translation_key = self.entity_description.translation_key
        self._attr_has_entity_name = True
        if self.entity_description.key == "unknown":
            self._attr_translation_placeholders = {"sensor_type": str(sensor_type)}
            self._attr_entity_registry_enabled_default = False
        self._attr_native_unit_of_measurement = (
            self.entity_description.native_unit_of_measurement
        )
        self._attr_device_class = self.entity_description.device_class
        self._attr_state_class = self.entity_description.state_class

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.update_callback(self.channel.last_value)
        self.async_on_remove(
            self.channel.register_update_callback(self.update_callback)
        )

    def update_callback(
        self, state: float | None, raw_state: float | None = None
    ) -> None:
        if not self.enabled:
            return
        if state is None:
            return
        if self.entity_description.key == "72":
            # Water Flow Rate: Convert from L/s to m3/h
            state *= 3.6
        self._state = state
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        # self.device.client.unregister_event_callback(self.event_callback)
        pass

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self._state


class DigitalstromZoneControlValueSensor(
    CoordinatorEntity[DigitalstromClimateCoordinator], SensorEntity
):
    # Sensor entity that surfaces the zone PID control value using sensor map type 51.
    def __init__(
        self, coordinator: DigitalstromClimateCoordinator, zone: DigitalstromZone
    ) -> None:
        super().__init__(coordinator)
        self.zone = zone
        description = SENSORS_MAP[51]
        # Reuse the sensor map description so naming and units stay consistent with type 51.
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = (
            f"{self.zone.apartment.dsuid}_zone{self.zone.zone_id}_control_value"
        )
        self.entity_id = f"{DOMAIN}.{self._attr_unique_id}"
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_suggested_display_precision = 0

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

    @property
    def native_value(self) -> float | None:
        """Return the current control value."""
        return self.zone.control_value

    @callback
    def _handle_coordinator_update(self) -> None:
        if not self.enabled:
            return
        self.async_write_ha_state()


class DigitalstromMeterSensor(SensorEntity):
    def __init__(self, sensor_channel: DigitalstromMeterSensorChannel):
        self.channel = sensor_channel
        # Older objects might miss the explicit `circuit` attribute; fall back to the
        # base channel device reference and ensure the attribute is set for later use.
        circuit = getattr(sensor_channel, "circuit", None) or sensor_channel.device
        # Make sure downstream code sees the circuit attribute even if it was missing.
        setattr(sensor_channel, "circuit", circuit)
        self.circuit = circuit
        self._attr_unique_id: str = f"{self.circuit.dsuid}_{self.channel.index}"
        self.entity_id = f"{DOMAIN}.{self._attr_unique_id}"
        self._attr_should_poll = True
        self._has_state = False
        self._attributes: dict[str, Any] = {}
        self._state: float | None = None
        self.entity_id = f"{DOMAIN}.{self.circuit.dsuid}_{self.channel.index}"
        self._state = None
        self._attr_has_entity_name = True

        if self.channel.index == "power":
            self._attr_translation_key = "meter_power"
            self._attr_native_unit_of_measurement = UnitOfPower.WATT
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 0
        elif self.channel.index == "energy":
            self._attr_translation_key = "meter_energy"
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_suggested_display_precision = 3

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

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self._state

    async def async_update(self, **kwargs: Any) -> None:
        value = await self.channel.get_value()
        if self.channel.index == "energy" and value is not None:
            self._state = value / 3600000
        else:
            self._state = value
