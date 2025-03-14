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

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from panel.io.fastapi import add_application
from dtcgweb.ui.interface.apps.pn_runoff import get_runoff_dashboard

app = FastAPI()
templates = Jinja2Templates(directory="templates")
hostname = "127.0.0.1"

"""Middleware

TODO: sanitise user shapefiles
TODO: HTTPSRedirectMiddleware
"""
app.add_middleware(  # TODO: Bremen cluster support
    TrustedHostMiddleware, allowed_hosts=[hostname, "localhost", "dtcg.github.io"]
)

# app.mount("/static", StaticFiles(directory="static"), name="static")

# @app.get('/favicon.ico')
# async def favicon():
#     file_name = "favicon.png"
#     assert isinstance(app.root_path, str)
#     # file_path = Path(app.root_path)
#     # file_path = file_path / "static" / file_name
#     # print(file_path)
#     # assert file_path.is_file()
#     file_path = os.path.join(app.root_path, "static", file_name)

#     return FileResponse(path=file_path, headers={"Content-Disposition": "attachment; filename=" + file_name})


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
    return RedirectResponse(url="/app")


@add_application(
    "/app",
    app=app,
    title="DTCG Dashboard",
    # address=hostname,
    # port=8000,
    # show=False,
    # allow_websocket_origin=[f"{hostname}:8000", "localhost:8000"],
)
def get_dashboard():
    """Get the main dashboard"""
    return get_runoff_dashboard()
