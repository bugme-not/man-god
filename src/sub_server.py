from aiohttp import web
import base64
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


PORT = int(os.getenv("SUB_PORT", "8081"))
SECRET_TOKEN = "cxlvin777"


SERVER_ADDRESS = "app-analytics-services.com"
PORT_NUM = 443
VLESS_PATH = "%2FCxlvinVlWS"
SSH_USER = "cxlvin"
SSH_PASS = "cxlvin"
SSH_PAYLOAD_PARAM = "KUX3sw04Vw3D4VZXnUUdxzm0ktSn8qvoPZ3hvirbN91tTqyY31h2V7XVKv73sB2IaXm6ZKsOJh743ph9p1P7fvU969KDwVZdSJnk3gn+aCg9UXQ1lgtO3Zi3uUjhFyNhGihuZELf4IIqTXcroA+dsgQlcexmxLM2rcOxmGRWaQ9sXHoLMkiNyAjc4onG6DC+g+hPgyw7CQu7u+yIAq4emSak+5jKjAqnxwD7SgpO3CT4I56g/sVrpSJufSl5b4xqis4f8a4MHg6CEW6hX5ETRQ=="


async def handle_subscription(request: web.Request) -> web.Response:
    
    user_token = request.query.get("token")
    if user_token != SECRET_TOKEN:
        logging.warning(f"Unauthorized access attempt from {request.remote}")
        return web.Response(status=403, text="403 Access Denied: Invalid Token\n")

    
    run_app_host = request.host

    
    vless_uri = (
        f"vless://cxlvin777@{SERVER_ADDRESS}:{PORT_NUM}"
        f"?encryption=none&type=ws"
        f"&host={run_app_host}"
        f"&headerType=none&path={VLESS_PATH}&security=tls#CXLVIN-VLESS-WS"
    )

    
    ssh_uri = (
        f"ssh://{SSH_USER}:{SSH_PASS}@{SERVER_ADDRESS}:{PORT_NUM}"
        f"?{SSH_PAYLOAD_PARAM}#CXLVIN-SSH-WS"
    )
    
    full_payload = f"{vless_uri}\n\n{ssh_uri}\n"

    
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
