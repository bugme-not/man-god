from aiohttp import web
import base64
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PORT = int(os.getenv("SUB_PORT", "8081"))
SECRET_TOKEN = os.getenv("SUB_TOKEN", "cxlvin777")

SERVER_ADDRESS = "app-analytics-services.com"
PORT_NUM = 443
VLESS_PATH = "%2FCxlvinVlWS"
SSH_USER = "cxlvin"
SSH_PASS = "cxlvin"


def generate_ssh_payload(host: str) -> str:
    """Generates the clean raw SSH HTTP WebSocket payload string."""
    return (
        f"GET /cxlvin HTTP/1.1[crlf]"
        f"Host: {host}[crlf]"
        f"Upgrade: websocket[crlf]"
        f"Connection: Upgrade[crlf][crlf]"
    )


async def handle_subscription(request: web.Request) -> web.Response:
    user_token = request.query.get("token")
    if user_token != SECRET_TOKEN:
        logging.warning(f"Unauthorized access attempt from {request.remote}")
        return web.Response(status=403, text="403 Access Denied: Invalid Token\n")

    # Extract dynamic host forwarded by Nginx
    run_app_host = request.headers.get("X-Forwarded-Host") or request.host

    # 1. Standard VLESS Link
    vless_uri = (
        f"vless://cxlvin777@{SERVER_ADDRESS}:{PORT_NUM}"
        f"?encryption=none&type=ws"
        f"&host={run_app_host}"
        f"&headerType=none&path={VLESS_PATH}&security=tls#CXLVIN-VLESS-WS"
    )

    # 2. Raw SSH Connection Details & Custom Injector Payload
    raw_payload = generate_ssh_payload(run_app_host)
    
    plain_text_output = (
        f"========================================\n"
        f"         CXLVIN PROXY CONFIGS           \n"
        f"========================================\n\n"
        f"[ VLESS CONFIG LINK ]\n"
        f"{vless_uri}\n\n"
        f"----------------------------------------\n"
        f"[ SSH OVER WEBSOCKET DETAILS ]\n"
        f"Host/IP    : {SERVER_ADDRESS}\n"
        f"Port       : {PORT_NUM}\n"
        f"Username   : {SSH_USER}\n"
        f"Password   : {SSH_PASS}\n"
        f"WS Path    : /cxlvin\n"
        f"SNI / Host : {run_app_host}\n\n"
        f"[ SSH PAYLOAD FOR HTTP CUSTOM / INJECTOR ]\n"
        f"{raw_payload}\n"
        f"========================================\n"
    )

    # Check if request comes from browser/curl or dedicated v2ray subscription client
    user_agent = request.headers.get("User-Agent", "").lower()
    is_v2ray_client = any(client in user_agent for client in ["v2ray", "nekobox", "shadowrocket", "clash", "v2rayng"])

    if is_v2ray_client:
        # Serve base64 VLESS config for v2ray app auto-imports
        encoded_payload = base64.b64encode(f"{vless_uri}\n".encode("utf-8")).decode("utf-8")
        return web.Response(
            text=encoded_payload,
            content_type="text/plain",
            headers={"Cache-Control": "no-cache"}
        )

    # Return readable plain-text showing both VLESS and SSH payload for manual copy-pasting
    return web.Response(
        text=plain_text_output,
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
