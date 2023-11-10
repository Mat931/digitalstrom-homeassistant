# -*- coding: UTF-8 -*-

from homeassistant.exceptions import HomeAssistantError


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidCertificate(HomeAssistantError):
    """Error to indicate the server certificate is invalid."""


class InvalidFingerprint(HomeAssistantError):
    """Error to indicate the fingerprint format is invalid."""


class ServerError(HomeAssistantError):
    """Error to indicate the server returned unexpected data."""
