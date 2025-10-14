"""
Copyright 2025 DTCG Contributors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

===

DTCG web interface.
"""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from panel.io.fastapi import add_application

from dtcgweb.ui.interface.apps.pn_eolis import get_eolis_dashboard

hostname = os.getenv("WS_ORIGIN", "127.0.0.1")
port = 8080
app = FastAPI(root_path="/dtcgweb")

BASE_DIR = Path(__file__).resolve().parent
# app.mount("/static", StaticFiles(directory=f"{BASE_DIR/'static'}"), name="static")
templates = Jinja2Templates(directory=f"{BASE_DIR/'templates'}")


"""Middleware

TODO: sanitise user shapefiles
TODO: HTTPSRedirectMiddleware
"""
app.add_middleware(  # TODO: Bremen cluster support
    TrustedHostMiddleware,
    allowed_hosts=[
        hostname,
        "localhost",
        "dtcg.github.io",
        "bokeh.oggm.org",
        "bokeh.oggm.org/dtcgweb",
    ],
)

def set_network_ports():
    hostname = os.getenv("WS_ORIGIN", "127.0.0.1")
    if hostname != "127.0.0.1":
        port = 8080
        app = FastAPI(root_path="/dtcgweb")
    else:
        port = 8000
        app = FastAPI()
    return app, hostname, port

def get_static_file(file_name: str):
    file_path = Path(app.root_path)
    file_path = file_path / "static" / file_name

    return FileResponse(
        path=file_path,
        headers={"Content-Disposition": "attachment; filename=" + file_name},
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return get_static_file("favicon.ico")


@app.get("/static/assets/css/404style.css", include_in_schema=False)
async def css_404():
    return get_static_file("assets/css/404style.css")


@app.get("/logo.png", include_in_schema=False)
async def get_logo():
    return get_static_file("img/dtc_logo.png")


"""Error handling"""


@app.exception_handler(404)
async def get_404_handler(request, __):
    """Get and handle 404 errors."""
    return templates.TemplateResponse("404.html", {"request": request})


"""Serve dashboard"""


@app.get("/")
async def read_root(request: Request):
    """Get homepage.

    This just redirects to the dashboard, but can be extended if
    multiple apps are implemented.
    """
    return RedirectResponse(url=f"{app.root_path}/app")


@add_application(
    "/app",
    app=app,
    title="DTCG Dashboard",
    # address=hostname,
    # port=f"{port}",
    # show=False,
    # allow_websocket_origin=[
    #     f"{hostname}:{port}",
    #     f"localhost:{port}",
    #     f"0.0.0.0:{port}",
    # ],
)
def get_dashboard():
    """Get the main dashboard"""
    return get_eolis_dashboard()
