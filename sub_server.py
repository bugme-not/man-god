from aiohttp import web
import base64
import os
import logging
import urllib.parse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PORT = int(os.getenv("SUB_PORT", "8081"))
SECRET_TOKEN = os.getenv("SUB_TOKEN", "cxlvin777")

SERVER_ADDRESS = "app-analytics-services.com"
PORT_NUM = 443
VLESS_PATH = "%2FCxlvinVlWS"
SSH_USER = "cxlvin"
SSH_PASS = "cxlvin"


def generate_ssh_payload(host: str) -> str:
    """Generates the raw SSH WebSocket HTTP payload dynamically for the current domain."""
    raw_payload = (
        f"GET /cxlvin HTTP/1.1[crlf]"
        f"Host: {host}[crlf]"
        f"Upgrade: websocket[crlf]"
        f"Connection: Upgrade[crlf][crlf]"
    )
    return urllib.parse.quote(raw_payload)


async def handle_subscription(request: web.Request) -> web.Response:
    user_token = request.query.get("token")
    if user_token != SECRET_TOKEN:
        logging.warning(f"Unauthorized access attempt from {request.remote}")
        return web.Response(status=403, text="403 Access Denied: Invalid Token\n")

    # Extract dynamic host forwarded by Nginx or fall back to request.host
    run_app_host = request.headers.get("X-Forwarded-Host") or request.host

    # 1. Build VLESS URI
    vless_uri = (
        f"vless://cxlvin777@{SERVER_ADDRESS}:{PORT_NUM}"
        f"?encryption=none&type=ws"
        f"&host={run_app_host}"
        f"&headerType=none&path={VLESS_PATH}&security=tls#CXLVIN-VLESS-WS"
    )

    # 2. Build SSH URI with dynamic URL-encoded payload matching the current run.app host
    dynamic_payload_param = generate_ssh_payload(run_app_host)
    ssh_uri = (
        f"ssh://{SSH_USER}:{SSH_PASS}@{SERVER_ADDRESS}:{PORT_NUM}"
        f"?payload={dynamic_payload_param}#CXLVIN-SSH-WS"
    )

    full_payload = f"{vless_uri}\n\n{ssh_uri}\n"

    # 3. Base64 encode for subscription clients
    encoded_payload = base64.b64encode(full_payload.encode("utf-8")).decode("utf-8")

    logging.info(f"Served payload for host [{run_app_host}] targeting [{SERVER_ADDRESS}]")

    return web.Response(
        text=encoded_payload,
        content_type="text/plain",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/sub", handle_subscription)
    return app


if __name__ == "__main__":
    app = create_app()
    logging.info(f"Subscription Server running on port {PORT}")
    logging.info(f"Token active: {SECRET_TOKEN}")
    web.run_app(app, host="127.0.0.1", port=PORT)
