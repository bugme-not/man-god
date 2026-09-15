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
    """Generates the raw HTTP WebSocket payload string."""
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

    # Extract dynamic host forwarded by Nginx or fall back to request header
    run_app_host = request.headers.get("X-Forwarded-Host") or request.host

    # 1. VLESS Configuration URI
    vless_uri = (
        f"vless://cxlvin777@{SERVER_ADDRESS}:{PORT_NUM}"
        f"?encryption=none&type=ws"
        f"&host={run_app_host}"
        f"&headerType=none&path={VLESS_PATH}&security=tls#CXLVIN-VLESS-WS"
    )

    # 2. Universal SSH-WS URI (Parsed by NekoBox, SagerNet, and modern SSH-WS clients)
    # Uses URL-encoded payload as query parameter
    raw_payload = generate_ssh_payload(run_app_host)
    ssh_uri = (
        f"ssh://{SSH_USER}:{SSH_PASS}@{SERVER_ADDRESS}:{PORT_NUM}"
        f"?net=ws&host={run_app_host}&path=%2Fcxlvin&type=ws&tls=1#CXLVIN-SSH-WS"
    )

    # 3. HTTP Custom / Injector direct format
    http_custom_format = (
        f"SSH Host: {SERVER_ADDRESS}:{PORT_NUM}@{SSH_USER}:{SSH_PASS}\n"
        f"Payload: {raw_payload}"
    )

    # Combine ALL formats separated by newlines
    combined_raw_payload = f"{vless_uri}\n{ssh_uri}\n"

    # Always Base64 encode the combined lines so subscription managers parse BOTH configs
    encoded_payload = base64.b64encode(combined_raw_payload.encode("utf-8")).decode("utf-8")

    logging.info(f"Served VLESS + SSH subscription for [{run_app_host}]")

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
