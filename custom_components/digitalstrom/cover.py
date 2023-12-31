import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.exceptions import ServerError
from .const import CONF_DSUID, DOMAIN
from .entity import DigitalstromEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cover platform."""
    client = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["client"]
    apartment = hass.data[DOMAIN][config_entry.data[CONF_DSUID]]["apartment"]
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
    def __init__(self, position_channel, tilt_channel=None):
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
        self.last_value = None
        self.entity_id = f"{DOMAIN}.{self.device.dsuid}_{position_channel.index}"
        self._attr_name = self.device.name
        if position_channel.channel_type == "shadePositionIndoor":
            self._attr_name += " Indoor Cover"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.position_channel.register_update_callback(self.update_callback)
        )

    def update_callback(self, state, raw_state=None):
        pass

    async def async_will_remove_from_hass(self) -> None:
        # self.device.client.unregister_event_callback(self.event_callback)
        pass

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close cover."""
        await self.client.request(
            f"device/setOutputChannelValue?dsuid={self.device.dsuid}&channelvalues={self.position_channel.channel_id}=0&applyNow=1"
        )

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open cover."""
        await self.client.request(
            f"device/setOutputChannelValue?dsuid={self.device.dsuid}&channelvalues={self.position_channel.channel_id}=100&applyNow=1"
        )

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Update the current value."""
        position = kwargs[ATTR_POSITION]
        await self.client.request(
            f"device/setOutputChannelValue?dsuid={self.device.dsuid}&channelvalues={self.position_channel.channel_id}={position}&applyNow=1"
        )

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop cover."""
        await self.client.request(
            f"device/callScene?dsuid={self.device.dsuid}&sceneNumber=15"
        )

    async def async_update(self, **kwargs: Any):
        try:
            result = await self.client.request(
                f"property/getFloating?path=/apartment/zones/zone{self.device.zone_id}/devices/{self.device.dsuid}/status/outputs/{self.position_channel.channel_id}/targetValue"
            )
            self.last_value = result.get("value", None)
        except ServerError:
            self.last_value = None

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover.

        None is unknown, 0 is closed, 100 is fully open.

        return self.device.level"""
        return self.last_value

    @property
    def is_closed(self) -> bool | None:
        """Return true if cover is closed.

        None is unknown.

        Allow small calibration errors (some devices after a long time
        become not well calibrated)."""

        if self.last_value is None:
            return None

        return self.last_value < 5
