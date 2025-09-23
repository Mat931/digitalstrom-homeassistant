"""Config flow for digitalSTROM integration."""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant.components import ssdp, zeroconf
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TOKEN,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant

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
    IGNORE_SSL_VERIFICATION,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    result: dict[str, Any] = {}

    ssl = data.get(CONF_SSL, True)
    if ssl == IGNORE_SSL_VERIFICATION:
        ssl = False
        result[CONF_SSL] = False

    client = DigitalstromClient(
        host=data[CONF_HOST], port=data[CONF_PORT], ssl=ssl, loop=hass.loop
    )

    app_token_valid = False

    if CONF_TOKEN in data.keys() and data[CONF_TOKEN] is not None:
        _LOGGER.debug("Testing app token.")
        try:
            client.set_app_token(data[CONF_TOKEN])
            session_token = await client.request_session_token()
            assert len(session_token) >= 8  # 64
            app_token_valid = True
            result[CONF_TOKEN] = data[CONF_TOKEN]
        except Exception as e:
            _LOGGER.debug(f"App token invalid: {e}")
            client.set_app_token(None)

    if not app_token_valid:
        _LOGGER.debug("Requesting app token.")
        result[CONF_TOKEN] = await client.request_app_token(
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
            f"Home Assistant ({hass.config.location_name})",
        )
    else:
        _LOGGER.debug("Testing login.")
        if not await client.test_login(data[CONF_USERNAME], data[CONF_PASSWORD]):
            raise InvalidAuth

    return result


class DigitalstromConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for digitalSTROM."""

    VERSION = 1

    def __init__(self, *args: Any, **kwargs: Any):
        self._host: str = DEFAULT_HOST
        self._port: int = DEFAULT_PORT
        self._user: str = DEFAULT_USERNAME
        self._password: str = ""
        self._ssl: str | bool | None = None
        self._token: str | None = None
        self._name = "digitalSTROM"
        self._existing_entry: ConfigEntry | None = None
        super().__init__(*args, **kwargs)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._host = user_input.get(CONF_HOST, self._host)
            self._port = user_input.get(CONF_PORT, self._port)
            self._user = user_input.get(CONF_USERNAME, self._user)
            self._password = user_input.get(CONF_PASSWORD, self._password)
            self._ssl = user_input.get(CONF_SSL, self._ssl)

            if self._ssl == "":
                self._ssl = None
            if type(self._ssl) is bool and not self._ssl:
                self._ssl = IGNORE_SSL_VERIFICATION

            ssl = user_input.get(CONF_SSL, True)
            if ssl == IGNORE_SSL_VERIFICATION:
                ssl = False
            dsuid = None
            try:
                client = DigitalstromClient(self._host, self._port, ssl, self.hass.loop)
                dsuid = await client.get_system_dsuid()
                await self.async_set_unique_id(dsuid)
                user_input[CONF_DSUID] = dsuid
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidCertificate:
                errors["base"] = "invalid_certificate"
            except InvalidFingerprint:
                errors["base"] = "invalid_fingerprint"

            if self._existing_entry is None:
                self._abort_if_unique_id_configured()

            if dsuid is not None:
                try:
                    user_input[CONF_TOKEN] = self._token
                    info = await validate_input(self.hass, user_input)
                    user_input.update(info)
                    if self._existing_entry is not None:
                        self.hass.config_entries.async_update_entry(
                            self._existing_entry, data=user_input
                        )
                        # Reload the config entry to notify of updated config
                        self.hass.async_create_task(
                            self.hass.config_entries.async_reload(
                                self._existing_entry.entry_id
                            )
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
                except Exception as e:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception: {e}")
                    errors["base"] = "unknown"

        fields: dict[Any, type] = OrderedDict()
        fields[vol.Required(CONF_HOST, default=self._host or vol.UNDEFINED)] = str
        fields[vol.Required(CONF_PORT, default=self._port or vol.UNDEFINED)] = int
        fields[vol.Required(CONF_USERNAME, default=self._user or vol.UNDEFINED)] = str
        fields[vol.Required(CONF_PASSWORD, default=self._password or vol.UNDEFINED)] = (
            str
        )
        fields[vol.Optional(CONF_SSL, default=self._ssl or vol.UNDEFINED)] = str

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(fields), errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery."""

        self._name = discovery_info.hostname.removesuffix(".local.")
        self._host = str(discovery_info.ip_address)

        return await self.async_step_discovery_()

    async def async_step_ssdp(
        self, discovery_info: ssdp.SsdpServiceInfo
    ) -> ConfigFlowResult:
        """Handle ssdp discovery."""

        result = urlparse(discovery_info.ssdp_location)

        self._name = discovery_info.upnp.get("friendlyName", "dSS")
        self._host = str(result.netloc).split(":")[0]

        return await self.async_step_discovery_()

    async def async_step_discovery_(self) -> ConfigFlowResult:
        """Handle discovery."""
        client = DigitalstromClient(
            host=self._host, port=self._port, ssl=False, loop=self.hass.loop
        )
        dsuid = await client.get_system_dsuid()

        await self.async_set_unique_id(dsuid)
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})

        return await self.async_step_user()

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a flow initialized by a reauth event."""
        self._existing_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        assert self._existing_entry is not None
        self._host = entry_data.get(CONF_HOST, self._host)
        self._port = entry_data.get(CONF_PORT, self._port)
        self._user = entry_data.get(CONF_USERNAME, self._user)
        self._password = entry_data.get(CONF_PASSWORD, self._password)
        self._ssl = entry_data.get(CONF_SSL, self._ssl)
        if type(self._ssl) is bool and not self._ssl:
            self._ssl = IGNORE_SSL_VERIFICATION
        self._token = entry_data.get(CONF_TOKEN, self._token)
        return await self.async_step_user()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add reconfigure step to allow to reconfigure a config entry."""
        self._existing_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        assert self._existing_entry is not None
        if user_input is None:
            self._host = self._existing_entry.data.get(CONF_HOST, self._host)
            self._port = self._existing_entry.data.get(CONF_PORT, self._port)
            self._user = self._existing_entry.data.get(CONF_USERNAME, self._user)
            self._password = self._existing_entry.data.get(
                CONF_PASSWORD, self._password
            )
            self._ssl = self._existing_entry.data.get(CONF_SSL, self._ssl)
            if type(self._ssl) is bool and not self._ssl:
                self._ssl = IGNORE_SSL_VERIFICATION
        self._token = self._existing_entry.data.get(CONF_TOKEN, self._token)
        return await self.async_step_user(user_input)
