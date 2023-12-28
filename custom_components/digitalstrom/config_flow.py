"""Config flow for digitalSTROM integration."""
from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import ssdp, zeroconf
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TOKEN,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api.client import DigitalstromClient
from .api.exceptions import (
    CannotConnect,
    InvalidAuth,
    InvalidCertificate,
    InvalidFingerprint,
)
from .const import (
    CONF_DSUID,
    CONF_SSL,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    result = {}

    ssl = data.get("ssl", True)
    if ssl == "ignore":
        ssl = False
        result["ssl"] = False

    client = DigitalstromClient(
        host=data["host"], port=data["port"], ssl=ssl, loop=hass.loop
    )

    result[CONF_DSUID] = await client.get_system_dsuid()

    if CONF_TOKEN not in data.keys():
        _LOGGER.debug("Requesting app token.")
        result[CONF_TOKEN] = await client.request_app_token(
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
            f"Home Assistant ({hass.config.location_name})",
        )
    else:
        _LOGGER.debug("Testing login.")
        if not await client.test_login():
            raise InvalidAuth

    return result


class DigitalstromConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for digitalSTROM."""

    VERSION = 1

    def __init__(self, *args, **kwargs):
        self._host: str = DEFAULT_HOST
        self._port: int = DEFAULT_PORT
        self._user: str = DEFAULT_USERNAME
        self._password: str = ""
        self._ssl: str | bool | None = None
        self._dsuid: str | None = None
        self._name = "digitalSTROM"
        self._reauth_entry: ConfigEntry | None = None
        super().__init__(*args, **kwargs)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._host = user_input.get(CONF_HOST, self._host)
            self._port = user_input.get(CONF_PORT, self._port)
            self._user = user_input.get(CONF_USERNAME, self._user)
            self._password = user_input.get(CONF_PASSWORD, self._password)
            self._ssl = user_input.get(CONF_SSL, self._ssl)
            self._dsuid = user_input.get(CONF_DSUID, self._dsuid)

            if self._ssl == "":
                self._ssl = None
            if type(self._ssl) is bool and not self._ssl:
                self._ssl = "ignore"
            if self._dsuid == "":
                self._dsuid = None

            if self._dsuid is None:
                try:
                    temp_client = DigitalstromClient(self._host, self._port, False)
                    self._dsuid = await temp_client.get_system_dsuid()
                except CannotConnect:
                    pass

            await self.async_set_unique_id(self._dsuid)
            if not self._reauth_entry:
                self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
                user_input.update(info)
                if self._reauth_entry:
                    entry = self._reauth_entry
                    self.hass.config_entries.async_update_entry(entry, data=user_input)
                    # Reload the config entry to notify of updated config
                    self.hass.async_create_task(
                        self.hass.config_entries.async_reload(entry.entry_id)
                    )

                    return self.async_abort(reason="reauth_successful")

                return self.async_create_entry(title=self._name, data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidCertificate:
                errors["base"] = "invalid_certificate"
            except InvalidFingerprint:
                errors["base"] = "invalid_fingerprint"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        fields: dict[Any, type] = OrderedDict()
        fields[vol.Required(CONF_HOST, default=self._host or vol.UNDEFINED)] = str
        fields[vol.Required(CONF_PORT, default=self._port or vol.UNDEFINED)] = int
        fields[vol.Required(CONF_USERNAME, default=self._user or vol.UNDEFINED)] = str
        fields[
            vol.Required(CONF_PASSWORD, default=self._password or vol.UNDEFINED)
        ] = str
        fields[vol.Optional(CONF_SSL, default=self._ssl or vol.UNDEFINED)] = str

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(fields), errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery."""

        self._name = discovery_info.hostname.removesuffix(".local.")
        self._host = str(discovery_info.ip_address)

        return await self.async_step_discovery_()

    async def async_step_ssdp(self, discovery_info: ssdp.SsdpServiceInfo) -> FlowResult:
        """Handle ssdp discovery."""

        result = urlparse(discovery_info.ssdp_location)

        self._name = discovery_info.upnp.get("friendlyName", "dSS")
        self._host = str(result.netloc).split(":")[0]

        return await self.async_step_discovery_()

    async def async_step_discovery_(self) -> FlowResult:
        """Handle discovery."""
        client = DigitalstromClient(
            host=self._host, port=self._port, ssl=False, loop=self.hass.loop
        )
        dsuid = await client.get_system_dsuid()

        await self.async_set_unique_id(dsuid)
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})

        return await self.async_step_user()

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle a flow initialized by a reauth event."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None
        self._host = entry_data.get(CONF_HOST, self._host)
        self._port = entry_data.get(CONF_PORT, self._port)
        self._user = entry_data.get(CONF_USERNAME, self._user)
        self._password = entry_data.get(CONF_PASSWORD, self._password)
        self._ssl = entry_data.get(CONF_SSL, self._ssl)
        self._dsuid = entry_data.get(CONF_DSUID, self._dsuid)
        self._reauth_entry = entry

        return await self.async_step_user()
