import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.channel import DigitalstromOutputChannel
from .const import DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cover platform."""
    apartment = hass.data[DOMAIN][config_entry.unique_id]["apartment"]
    covers = []
    for device in apartment.devices.values():
        position_outdoor = None
        angle_outdoor = None
        position_indoor = None
        angle_indoor = None
        for channel in device.output_channels.values():
            if (
                channel.channel_type == "shadePositionOutside"
                and position_outdoor is None
            ):
                position_outdoor = channel
            if (
                channel.channel_type == "shadeOpeningAngleOutside"
                and angle_outdoor is None
            ):
                angle_outdoor = channel
            if (
                channel.channel_type == "shadePositionIndoor"
                and position_indoor is None
            ):
                position_indoor = channel
            if (
                channel.channel_type == "shadeOpeningAngleIndoor"
                and angle_indoor is None
            ):
                angle_indoor = channel
        if position_outdoor is not None:
            covers.append(DigitalstromCover(position_outdoor, angle_outdoor))
        if position_indoor is not None:
            covers.append(DigitalstromCover(position_indoor, angle_indoor))
    _LOGGER.debug("Adding %i covers", len(covers))
    async_add_entities(covers)


class DigitalstromCover(CoverEntity, DigitalstromEntity):
    def __init__(
        self,
        position_channel: DigitalstromOutputChannel,
        tilt_channel: DigitalstromOutputChannel | None = None,
    ):
        super().__init__(position_channel.device, f"O{position_channel.index}")
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
            | CoverEntityFeature.STOP
        )

        self.position_channel = position_channel
        self.tilt_channel = tilt_channel
        self.device = position_channel.device
        self.client = self.device.client
        self._attr_should_poll = True
        self.last_tilt = None
        self.entity_id = f"{DOMAIN}.{self.device.dsuid}_{position_channel.index}"
        self._attr_name = self.device.name
        self.used_channels = [self.position_channel.channel_type]
        if position_channel.channel_type == "shadePositionIndoor":
            self._attr_name += " Indoor Cover"
        if self.tilt_channel is not None:
            self.used_channels.append(self.tilt_channel.channel_type)
            self._attr_supported_features |= (
                CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.STOP_TILT
                | CoverEntityFeature.SET_TILT_POSITION
            )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.position_channel.register_update_callback(self.update_callback)
        )

    def update_callback(self, state: Any, raw_state: Any = None) -> None:
        if not self.enabled:
            return
        self.async_write_ha_state()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open cover."""
        await self.position_channel.set_value(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close cover."""
        await self.position_channel.set_value(0)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop cover."""
        await self.device.call_scene(15)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Update the current value."""
        await self.position_channel.set_value(kwargs[ATTR_POSITION])

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the cover tilt."""
        if self.tilt_channel is not None:
            await self.tilt_channel.set_value(100)

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the cover tilt."""
        if self.tilt_channel is not None:
            await self.tilt_channel.set_value(0)

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        """Stop the cover tilt."""
        if self.tilt_channel is not None:
            await self.device.call_scene(15)

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Move the cover tilt to a specific position."""
        if self.tilt_channel is not None:
            await self.tilt_channel.set_value(kwargs[ATTR_TILT_POSITION])

    async def async_update(self, **kwargs: Any) -> None:
        if self.available:
            await self.device.output_channels_get_values(self.used_channels)

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover.

        None is unknown, 0 is closed, 100 is fully open.
        """
        if self.position_channel.last_value is None:
            return None
        return round(self.position_channel.last_value)

    @property
    def is_closed(self) -> bool | None:
        """Return true if cover is closed.

        None is unknown.

        Allow small calibration errors (some devices after a long time
        become not well calibrated)."""

        if self.position_channel.last_value is None:
            return None

        return self.position_channel.last_value < 5

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Return current position of cover tilt.

        None is unknown, 0 is closed, 100 is fully open.
        """
        if self.tilt_channel is None or self.tilt_channel.last_value is None:
            return None
        return round(self.tilt_channel.last_value)

    @property
    def _fully_open_tilt(self) -> int | None:
        """Return value that represents fully opened tilt."""
        return None if self.tilt_channel is None else 100

    @property
    def _fully_closed_tilt(self) -> int | None:
        """Return value that represents fully closed tilt."""
        return None if self.tilt_channel is None else 0

    @property
    def _tilt_range(self) -> int | None:
        """Return range between fully opened and fully closed tilt."""
        if self._fully_open_tilt is None or self._fully_closed_tilt is None:
            return None
        return self._fully_open_tilt - self._fully_closed_tilt
