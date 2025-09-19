import ast
import asyncio
import json
import secrets
import ssl
from datetime import datetime, timedelta

from aiohttp import WSMsgType, web
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

import apartment

HOST = "0.0.0.0"
PORT = 8080
CERT_PATH = "cert.pem"
KEY_PATH = "key.pem"
DS_USER = "dssadmin"
DS_PASSWORD = "password"
DS_USER_TOKEN = "test_user_token"
DS_SYSTEM_DSUID = "TEST_SYSTEM_DSUID"
ENABLE_AUTH_CHECKS = False

APP_TOKENS: dict[str, dict[str, str | bool]] = {}
SESSION_TOKENS: dict[str, dict[str, str | float]] = {}
connected_ws = set()
ap = apartment.Apartment()


def validate_and_get_app_token(session_token):
    if session_token not in SESSION_TOKENS.keys():
        return None
    last_activity = SESSION_TOKENS[session_token]["last_activity"]
    if datetime.now() > last_activity + timedelta(seconds=60):
        print(f"Deleting expired session token {session_token}")
        del SESSION_TOKENS[session_token]
        return None
    SESSION_TOKENS[session_token]["last_activity"] = datetime.now()
    return SESSION_TOKENS[session_token]["app_token"]


@web.middleware
async def auth_middleware(request, handler):
    UNAUTHENTICATED_PATHS = [
        "/json/system/getDSID",
        "/json/system/requestApplicationToken",
        "/json/system/login",
        "/json/system/enableToken",
        "/json/system/loginApplication",
        "/send_event",
    ]
    if request.path in UNAUTHENTICATED_PATHS:
        return await handler(request)

    if ENABLE_AUTH_CHECKS:
        session_token = request.cookies.get("token")
        if (app_token := validate_and_get_app_token(session_token)) is None:
            return web.json_response({"message": "authentication failed"}, status=403)
        request["app_token"] = app_token

    return await handler(request)


# JSON API handlers
async def get_dsid(request):
    return web.json_response({"ok": True, "result": {"dSUID": DS_SYSTEM_DSUID}})


async def request_application_token(request):
    app_name = request.query.get("applicationName")
    app_token = secrets.token_hex(32)
    print(f"Creating new app token {app_token} for app '{app_name}'")
    APP_TOKENS[app_token] = {"app_name": app_name, "enabled": False}
    return web.json_response({"ok": True, "result": {"applicationToken": app_token}})


async def login(request):
    user = request.query.get("user")
    if not (user == DS_USER and request.query.get("password") == DS_PASSWORD):
        print(f"Login as user '{user}' failed")
        return web.json_response(
            {"message": "invalid username or password"}, status=403
        )
    print(f"Login as user '{user}' successful")
    return web.json_response({"ok": True, "result": {"token": DS_USER_TOKEN}})


async def enable_token(request):
    app_token = request.query.get("applicationToken")
    user_token = request.query.get("token")
    if app_token not in APP_TOKENS.keys():
        return web.json_response({"message": "invalid application token"}, status=403)
    if not user_token == DS_USER_TOKEN:
        return web.json_response({"message": "invalid token"}, status=403)
    print(f"Enabling app token {app_token} for user {user_token}")
    APP_TOKENS[app_token]["enabled"] = True
    return web.json_response({"ok": True, "result": {}})


async def login_application(request):
    app_token = request.query.get("loginToken")
    if (app_token not in APP_TOKENS.keys()) or (not APP_TOKENS[app_token]["enabled"]):
        return web.json_response({"message": "invalid application token"}, status=403)
    session_token = secrets.token_hex(32)
    print(f"Creating new session token {session_token} for app {app_token}")
    SESSION_TOKENS[session_token] = {
        "last_activity": datetime.now(),
        "app_token": app_token,
    }
    return web.json_response({"ok": True, "result": {"token": session_token}})


async def json_api(request):
    print(request.rel_url)
    result = ap.handle_request(request)
    print(result)
    return web.json_response(result)


async def websocket_handler(request):
    if ENABLE_AUTH_CHECKS:
        session_token = request.cookies.get("token")
        if (app_token := validate_and_get_app_token(session_token)) is None:
            return web.json_response({"message": "authentication failed"}, status=403)

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    if ENABLE_AUTH_CHECKS:
        ws.session = app_token

    print("WS connected")
    connected_ws.add(ws)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                print(f"WS message received: '{msg.data}'")
            elif msg.type == WSMsgType.ERROR:
                print("WS connection closed with exception %s" % ws.exception())
    finally:
        print("WS disconnected")
        connected_ws.discard(ws)

    return ws


async def send_event(request):
    # This is not part of the DSS API. You can use it to send websocket events to all connected clients.
    failed = False
    event = {}
    try:
        event_str = request.query.get("event")
        try:
            event = json.loads(event_str)
        except json.decoder.JSONDecodeError:
            try:
                event = ast.literal_eval(event_str)
            except SyntaxError:
                failed = True
        print(f"Event: {event_str}")
    except TypeError:
        failed = True
    if failed:
        return web.json_response(
            {
                "error": 'Invalid data. Use send_event?event={"name": "", "properties": "", "source": ""}'
            },
            status=400,
        )

    if "name" not in event:
        return web.json_response({"error": 'event does not contain "name"'}, status=400)
    if "properties" not in event:
        return web.json_response(
            {"error": 'event does not contain "properties"'}, status=400
        )
    if "source" not in event:
        return web.json_response(
            {"error": 'event does not contain "source"'}, status=400
        )

    if connected_ws:
        msg_text = json.dumps(event)
        coros = [ws.send_str(msg_text) for ws in connected_ws if not ws.closed]
        await asyncio.gather(*coros, return_exceptions=True)

    return web.json_response({"sent": True, "connected_clients": len(connected_ws)})


async def init_app():
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get("/json/system/getDSID", get_dsid)
    app.router.add_get(
        "/json/system/requestApplicationToken", request_application_token
    )
    app.router.add_get("/json/system/login", login)
    app.router.add_get("/json/system/enableToken", enable_token)
    app.router.add_get("/json/system/loginApplication", login_application)
    app.router.add_get(r"/json/{path:.*}", json_api)
    app.router.add_get("/websocket", websocket_handler)
    app.router.add_get("/send_event", send_event)
    return app


def print_login_details(cert_path, username, password):
    try:
        with open(cert_path, "rb") as cert_file:
            cert_data = cert_file.read()
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            fingerprint = cert.fingerprint(hashes.SHA256())
            print(f"Username: {username}\nPassword: {password}")
            print(f"Certificate fingerprint: {fingerprint.hex()}")
    except FileNotFoundError:
        print("Certificate file not found.\n")
        print("Generate a new key and certificate:")
        print(
            ' openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes -subj "/C=XX/ST=Test/L=Test/O=Test/OU=Test/CN=Test"\n'
        )
        exit()


def main():
    print_login_details(CERT_PATH, DS_USER, DS_PASSWORD)
    loop = asyncio.new_event_loop()
    app = loop.run_until_complete(init_app())
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(CERT_PATH, KEY_PATH)
    ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    web.run_app(app, host=HOST, port=PORT, ssl_context=ssl_ctx)


if __name__ == "__main__":
    main()
