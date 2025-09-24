import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_XY_COLOR,
    DEFAULT_MAX_KELVIN,
    DEFAULT_MIN_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.channel import DigitalstromOutputChannel
from .const import DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform."""
    apartment = hass.data[DOMAIN][config_entry.unique_id]["apartment"]
    lights = []
    for device in apartment.devices.values():
        brightness = None
        color_temp = None
        hue = None
        saturation = None
        color_x = None
        color_y = None
        for channel in device.output_channels.values():
            if channel.channel_type == "brightness" and brightness is None:
                brightness = channel
            if channel.channel_type == "colortemp" and color_temp is None:
                color_temp = channel
            if channel.channel_type == "hue" and hue is None:
                hue = channel
            if channel.channel_type == "saturation" and saturation is None:
                saturation = channel
            if channel.channel_type == "x" and color_x is None:
                color_x = channel
            if channel.channel_type == "y" and color_y is None:
                color_y = channel
        if brightness is not None:
            lights.append(
                DigitalstromLight(
                    brightness, color_temp, hue, saturation, color_x, color_y
                )
            )
    _LOGGER.debug("Adding %i lights", len(lights))
    async_add_entities(lights)


class DigitalstromLight(LightEntity, DigitalstromEntity):
    def __init__(
        self,
        brightness_channel: DigitalstromOutputChannel,
        color_temp_channel: DigitalstromOutputChannel | None = None,
        hue_channel: DigitalstromOutputChannel | None = None,
        saturation_channel: DigitalstromOutputChannel | None = None,
        x_channel: DigitalstromOutputChannel | None = None,
        y_channel: DigitalstromOutputChannel | None = None,
    ):
        super().__init__(brightness_channel.device, f"O{brightness_channel.index}")

        self._attr_name = "Light"
        self.brightness_channel = brightness_channel
        self.color_temp_channel = color_temp_channel
        self.hue_channel = hue_channel
        self.saturation_channel = saturation_channel
        self.x_channel = x_channel
        self.y_channel = y_channel
        self.device = brightness_channel.device
        self.client = self.device.client
        self.dimmable = self.device.output_dimmable
        self._attr_should_poll = True
        self.entity_id = f"{DOMAIN}.{self.device.dsuid}_{brightness_channel.index}"
        self._attr_name = self.device.name
        self._attr_min_color_temp_kelvin = DEFAULT_MIN_KELVIN
        self._attr_max_color_temp_kelvin = DEFAULT_MAX_KELVIN
        self.used_channels = ["brightness"]

        color_modes: list[ColorMode] = []
        if self.dimmable:
            if self.x_channel is not None and self.y_channel is not None:
                color_modes.append(ColorMode.XY)
                self.used_channels.append("x")
                self.used_channels.append("y")
            elif self.hue_channel is not None and self.saturation_channel is not None:
                color_modes.append(ColorMode.HS)
                self.used_channels.append("hue")
                self.used_channels.append("saturation")
            if self.color_temp_channel is not None:
                color_modes.append(ColorMode.COLOR_TEMP)
                self.used_channels.append("colortemp")
            if len(color_modes) == 0:
                color_modes.append(ColorMode.BRIGHTNESS)
        else:
            color_modes.append(ColorMode.ONOFF)
        self._attr_supported_color_modes: set[ColorMode] = set(color_modes)
        self.default_color_mode = color_modes[0]
        self.last_color_mode = color_modes[0]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""

        self.device.output_channels_clear_prepared_values()

        if not self.dimmable:
            self.brightness_channel.prepare_value(100)
        elif (brightness := kwargs.get(ATTR_BRIGHTNESS)) is not None:
            self.brightness_channel.prepare_value(brightness / 2.55)
        elif (
            self.brightness_channel.last_value is None
            or self.brightness_channel.last_value < 1
        ):
            self.brightness_channel.prepare_value(100)

        if (
            color_temp_k := kwargs.get(ATTR_COLOR_TEMP_KELVIN)
        ) is not None and self.color_temp_channel is not None:
            self.color_temp_channel.prepare_value(1000000 / color_temp_k)
            if ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
                self.last_color_mode = ColorMode.COLOR_TEMP

        if (
            (xy_color := kwargs.get(ATTR_XY_COLOR)) is not None
            and self.x_channel is not None
            and self.y_channel is not None
        ):
            color_x, color_y = xy_color
            self.x_channel.prepare_value(color_x)
            self.y_channel.prepare_value(color_y)
            if ColorMode.XY in self._attr_supported_color_modes:
                self.last_color_mode = ColorMode.XY

        if (
            (hs_color := kwargs.get(ATTR_HS_COLOR)) is not None
            and self.hue_channel is not None
            and self.saturation_channel is not None
        ):
            hue, saturation = hs_color
            self.hue_channel.prepare_value(hue)
            self.saturation_channel.prepare_value(saturation)
            if ColorMode.HS in self._attr_supported_color_modes:
                self.last_color_mode = ColorMode.HS

        await self.device.output_channels_set_prepared_values()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.brightness_channel.set_value(0)

    async def async_update(self, **kwargs: Any) -> None:
        if self.available:
            await self.device.output_channels_get_values(self.used_channels)

    @property
    def is_on(self) -> bool | None:
        """Return true if the light is on."""
        if self.brightness_channel.last_value is None:
            return None
        return self.brightness_channel.last_value > 0

    @property
    def brightness(self) -> int | None:
        """Return the brightness of a device."""
        if self.brightness_channel.last_value is None:
            return None
        return round(self.brightness_channel.last_value * 2.55)

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the CT color value in Kelvin."""
        if (
            self.color_temp_channel is None
            or self.color_temp_channel.last_value is None
            or self.color_temp_channel.last_value == 0
        ):
            return None
        return round(1000000 / self.color_temp_channel.last_value)

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hs color."""
        if self.hue_channel is None or self.saturation_channel is None:
            return None
        hue = self.hue_channel.last_value
        saturation = self.saturation_channel.last_value
        if hue is None or saturation is None:
            return None
        return (hue, saturation)

    @property
    def xy_color(self) -> tuple[float, float] | None:
        """Return the xy color value [float, float]."""
        if self.x_channel is None or self.y_channel is None:
            return None
        x = self.x_channel.last_value
        y = self.y_channel.last_value
        if x is None or y is None:
            return None
        if x > 1 or y > 1:
            x = x / 10000
            y = y / 10000
        return (x, y)

    @property
    def color_mode(self) -> str:
        """Return the color mode of the light."""
        if len(self._attr_supported_color_modes) > 1:
            return self.last_color_mode
        return self.default_color_mode
