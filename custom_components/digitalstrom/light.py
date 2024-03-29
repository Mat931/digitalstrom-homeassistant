import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_XY_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.channel import DigitalstromOutputChannel
from .const import CONF_DSUID, DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform."""
    client = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["client"]
    apartment = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["apartment"]
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
        color_temp_channel: DigitalstromOutputChannel = None,
        hue_channel: DigitalstromOutputChannel = None,
        saturation_channel: DigitalstromOutputChannel = None,
        x_channel: DigitalstromOutputChannel = None,
        y_channel: DigitalstromOutputChannel = None,
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

        color_modes = []
        if self.dimmable:
            if self.x_channel is not None and self.y_channel is not None:
                color_modes.append(ColorMode.XY)
            elif self.hue_channel is not None and self.saturation_channel is not None:
                color_modes.append(ColorMode.HS)
            if self.color_temp_channel is not None:
                color_modes.append(ColorMode.COLOR_TEMP)
            if len(color_modes) == 0:
                color_modes.append(ColorMode.BRIGHTNESS)
        else:
            color_modes.append(ColorMode.ONOFF)
        self._attr_supported_color_modes = set(color_modes)
        self._attr_color_mode = color_modes[0]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""

        self.device.output_channels_clear_prepared_values()
        binary_light = True

        if (brightness := kwargs.get(ATTR_BRIGHTNESS)) is not None:
            self.brightness_channel.prepare_value(brightness / 255 * 100)
            binary_light = False

        if (color_temp_k := kwargs.get(ATTR_COLOR_TEMP_KELVIN)) is not None:
            self.color_temp_channel.prepare_value(1000000.0 / color_temp_k)
            binary_light = False

        if (xy_color := kwargs.get(ATTR_XY_COLOR)) is not None:
            color_x, color_y = xy_color
            self.x_channel.prepare_value(color_x)
            self.y_channel.prepare_value(color_y)
            binary_light = False

        if (hs_color := kwargs.get(ATTR_HS_COLOR)) is not None:
            hue, saturation = hs_color
            self.hue_channel.prepare_value(hue)
            self.saturation_channel.prepare_value(saturation)
            binary_light = False

        if binary_light:
            self.brightness_channel.prepare_value(100)

        await self.device.output_channels_set_prepared_values()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.brightness_channel.set_value(0)

    async def async_update(self, **kwargs: Any) -> None:
        await self.brightness_channel.get_value()

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        if self.brightness_channel.last_value is None:
            return None
        return self.brightness_channel.last_value > 0

    @property
    def brightness(self) -> int:
        """Return the brightness of a device."""
        if self.brightness_channel.last_value is None:
            return None
        return self.brightness_channel.last_value * 2.55
