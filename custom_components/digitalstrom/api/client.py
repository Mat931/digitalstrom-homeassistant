import asyncio
import binascii
import json
import re
import socket
import time

import aiohttp

from .const import EVENT_LISTENER_TIMEOUT, SESSION_TOKEN_TIMEOUT, SSL_FINGERPRINT_REGEX
from .exceptions import (
    CannotConnect,
    InvalidAuth,
    InvalidCertificate,
    InvalidFingerprint,
    ServerError,
)


class DigitalstromClient:
    def __init__(
        self,
        host: str,
        port: int,
        ssl: str | bool | None = None,
        loop: asyncio.AbstractEventLoop = None,
    ):
        # ssl:
        #  False -> Ignore server certificate
        #  True, None -> Verify server certificate
        #  str -> Verify server certificate using fingerprint
        self.host = host
        self.port = port
        self.ssl = None
        self.last_request = None
        self.last_event = None
        self._loop = loop
        self._app_token = None
        self._session_token = None
        self._ws = None
        self._event_callbacks = []
        if type(ssl) is bool:
            self.ssl = None if ssl else False
        elif type(ssl) is str:
            ssl_clean = re.sub(SSL_FINGERPRINT_REGEX, "", ssl)
            if len(ssl_clean) != 64:
                raise InvalidFingerprint(
                    f"Invalid fingerprint length: expected 64 hex characters, got {len(ssl_clean)}"
                )
            self.ssl = aiohttp.Fingerprint(binascii.unhexlify(ssl_clean))

    async def _request_raw(self, url: str, cookies: dict = None) -> dict:
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(family=socket.AF_INET, ssl=self.ssl),
            cookies=cookies,
            loop=self._loop,
        ) as session:
            try:
                async with session.get(
                    url=f"https://{self.host}:{self.port}/json/{url}"
                ) as response:
                    if response.status not in [200, 403, 500]:
                        raise ServerError(
                            f"Unexpected status code received: {response.status}"
                        )
                    try:
                        data = await response.json()
                    except json.decoder.JSONDecodeError as e:
                        raise ServerError(f"Failed to decode JSON: {e}") from None
                    if (is_ok := data.get("ok")) and is_ok:
                        if result := data.get("result"):
                            return result
                        return {}
                    elif message := data.get("message"):
                        if (
                            "authentication failed" in message.lower()
                            or response.status == 403
                        ):
                            raise InvalidAuth(message)
                        else:
                            raise ServerError(f"Error message received: {message}")
                    raise ServerError(f"Unexpected JSON structure received: {data}")

            except aiohttp.client_exceptions.ServerFingerprintMismatch as e:
                raise InvalidCertificate(e) from None
            except aiohttp.client_exceptions.ClientConnectorCertificateError as e:
                raise InvalidCertificate(e) from None
            except aiohttp.ClientError as e:
                raise CannotConnect(e) from None

    async def _request_session_token(self) -> str:
        data = await self._request_raw(
            f"system/loginApplication?loginToken={self._app_token}"
        )
        return data["token"]

    async def request_app_token(
        self, username: str, password: str, application_name: str = "Home Assistant"
    ) -> str:
        # Register a new app token
        self._app_token = None
        data = await self._request_raw(
            f"system/requestApplicationToken?applicationName={application_name}"
        )
        if app_token := data.get("applicationToken"):
            data = await self._request_raw(
                f"system/login?user={username}&password={password}"
            )
            if token := data.get("token"):
                await self._request_raw(
                    f"system/enableToken?applicationToken={app_token}&token={token}"
                )
                self._app_token = app_token
                return app_token

    async def test_login(self, username: str, password: str) -> bool:
        # Check if the username and password are correct
        data = await self._request_raw(
            f"system/login?user={username}&password={password}"
        )
        return "token" in data.keys()

    def set_app_token(self, app_token: str):
        # Re-use the app token from a previous login, returned by request_app_token
        self._app_token = app_token

    async def get_system_dsuid(self) -> str:
        # Get the dSUID for identifying the system without requiring a login
        data = await self._request_raw("system/getDSID")
        return data["dSUID"]

    async def request(self, url: str) -> dict:
        # Send an authenticated request to the server
        # Previous login via request_app_token or set_app_token is required
        if (self.last_request is None) or (
            self.last_request < time.time() - SESSION_TOKEN_TIMEOUT
        ):
            self._session_token = await self._request_session_token()
        self.last_request = time.time()
        data = await self._request_raw(url, dict(token=self._session_token))
        return data

    def register_event_callback(self, callback: callable):
        # Register an event callback
        self._event_callbacks.append(callback)

    def unregister_event_callback(self, callback: callable):
        # Unregister an event callback
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    async def start_event_listener(self):
        # Start the event listener
        # Previous login via request_app_token or set_app_token is required
        if self._ws is not None:
            await self.stop_event_listener()
        self._ws = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(family=socket.AF_INET, ssl=self.ssl),
            cookies=dict(token=await self._request_session_token()),
            loop=self._loop,
        )
        try:
            async with self._ws.ws_connect(
                url=f"wss://{self.host}:{self.port}/websocket"
            ) as ws:
                async for msg in ws:
                    try:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            self.last_event = time.time()
                            event = json.loads(msg.data)
                            if event.get("name"):
                                for callback in self._event_callbacks:
                                    await callback(event)
                        else:
                            if msg.tp == aiohttp.MsgType.closed:
                                break
                            elif msg.tp == aiohttp.MsgType.error:
                                break
                    except Exception as e:
                        pass
        except aiohttp.ClientError as e:
            raise CannotConnect(e) from None

    async def stop_event_listener(self):
        # Stop the event listener
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    def event_listener_connected(self):
        # Check if the event listener is connected
        return (
            (self._ws is not None)
            and (not self._ws.closed)
            and (
                (self.last_event is None)
                or (self.last_event > time.time() - EVENT_LISTENER_TIMEOUT)
            )
        )

    async def event_listener_watchdog(self, time):
        # Restart the event listener if it's not running
        if not self.event_listener_connected():
            try:
                await self.start_event_listener()
            except CannotConnect:
                pass
