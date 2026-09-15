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

# Your exact hardcoded SSH URI string
STATIC_SSH_URI = (
    "ssh://cxlvin:cxlvin@app-analytics-services.com:443?"
    "KUX3sw04Vw3D4VZXnUUdxzm0ktSn8qvoPZ3hvirbN91tTqyY31h2V7XVKv73sB2"
    "ILVyHxGUbVINzukXMSyb0UFx+VrMS1LHkNZ5Jmpe3IysdJjLdKr8+htIrTvcvoN"
    "+5DJy37v0gvmhcnKnHkqDjNYy/oPY+wukc2+gHUbWC8AXfKNWl7uJZIoKwR59Fk"
    "4E//i0PXb/pvwtFTUgJJl4cH6e7GNUM3g1Id3I03TucmSEUeQq/LOBbcQ4d0LbZM"
    "p4woUGMJMWdEEL9I0tjEKN+Eg=="
)


async def handle_subscription(request: web.Request) -> web.Response:
    user_token = request.query.get("token")
    if user_token != SECRET_TOKEN:
        logging.warning(f"Unauthorized access attempt from {request.remote}")
        return web.Response(status=403, text="403 Access Denied: Invalid Token\n")

    # Extract dynamic host forwarded by Nginx
    run_app_host = request.headers.get("X-Forwarded-Host") or request.host

    # 1. Build VLESS URI dynamically with the current .run.app host
    vless_uri = (
        f"vless://cxlvin777@{SERVER_ADDRESS}:{PORT_NUM}"
        f"?encryption=none&type=ws"
        f"&host={run_app_host}"
        f"&headerType=none&path={VLESS_PATH}&security=tls#CXLVIN-VLESS-WS"
    )

    # 2. Combine VLESS and your exact SSH URI
    full_text_output = f"{vless_uri}\n\n{STATIC_SSH_URI}\n"

    # 3. Base64 encode for subscription clients
    encoded_payload = base64.b64encode(f"{vless_uri}\n{STATIC_SSH_URI}\n".encode("utf-8")).decode("utf-8")

    # Check if request comes from a subscription app
    user_agent = request.headers.get("User-Agent", "").lower()
    is_v2ray_client = any(client in user_agent for client in ["v2ray", "nekobox", "shadowrocket", "v2rayng", "clash"])

    if is_v2ray_client:
        return web.Response(
            text=encoded_payload,
            content_type="text/plain",
            headers={"Cache-Control": "no-cache"},
        )

    # Return plain text showing both links clearly for manual copying
    return web.Response(
        text=full_text_output,
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
