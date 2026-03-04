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

import xarray as xr
import zarr
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from panel.io.fastapi import add_application
import panel as pn
from contextlib import asynccontextmanager

from pyinstrument import Profiler
from pyinstrument.renderers.html import HTMLRenderer
from pyinstrument.renderers.speedscope import SpeedscopeRenderer

# pn.extension(loading_spinner='arcs', loading_color='black', template='material')

from pydantic_settings import BaseSettings

from dtcgweb.ui.interface.apps.pn_eolis import get_eolis_dashboard_with_selection

class Settings(BaseSettings):
    PROFILING_ENABLED: bool = True
settings = Settings()
@asynccontextmanager
async def lifespan(app: FastAPI):
    
    pn.config.loading_spinner = "arcs"
    pn.config.loading_color = 'black'
    
    # pn.param.ParamMethod.loading_indicator = False
    # pn.io.loading.start_loading_spinner(self.plot)
    yield 
    # yield
    # pn.param.ParamMethod.loading_indicator = False

# hostname = os.getenv("WS_ORIGIN", "127.0.0.1")
# port = 8080
# app = FastAPI(root_path="/dtcgweb")
def set_network_ports():
    """Set app's port and hostname.

    TODO: find a reliable way to determine if running via
    Docker-in-Docker.

    Returns
    -------
    tuple[FastAPI,str,int]
        FastAPI app, hostname, and port number.
    """
    hostname = os.getenv("WS_ORIGIN", "127.0.0.1")
    if hostname != "127.0.0.1":
        port = 8080
        app = FastAPI(root_path="/dtcgweb",lifespan=lifespan)
    else:
        port = 8080
        app = FastAPI(lifespan=lifespan, PROFILING_ENABLED=True)
        # use this until certain 127.0.0.1 is not used in DinD server.
        # port = 8080
        # app = FastAPI(root_path="/dtcgweb")
    return app, hostname, port


app, hostname, port = set_network_ports()

def register_middlewares(app: FastAPI):
    ...
    if True:

        @app.middleware("http")
        async def profile_request(request: Request, call_next):
            """Profile the current request

            Taken from https://pyinstrument.readthedocs.io/en/latest/guide.html#profile-a-web-request-in-fastapi
            with small improvements.

            """
            # we map a profile type to a file extension, as well as a pyinstrument profile renderer
            profile_type_to_ext = {"html": "html", "speedscope": "speedscope.json"}
            profile_type_to_renderer = {
                "html": HTMLRenderer,
                "speedscope": SpeedscopeRenderer,
            }

            # if the `profile=true` HTTP query argument is passed, we profile the request
            if request.query_params.get("profile", False):

                # The default profile format is speedscope
                profile_type = request.query_params.get("profile_format", "speedscope")

                # we profile the request along with all additional middlewares, by interrupting
                # the program every 1ms1 and records the entire stack at that point
                with Profiler(interval=0.001, async_mode="enabled") as profiler:
                    response = await call_next(request)

                # we dump the profiling into a file
                extension = profile_type_to_ext[profile_type]
                renderer = profile_type_to_renderer[profile_type]()
                with open(f"profile.{extension}", "w") as out:
                    out.write(profiler.output(renderer=renderer))
                return response

            # Proceed without profiling
            return await call_next(request)

register_middlewares(app)

BASE_DIR = Path(__file__).resolve().parent
# app.mount("/static", StaticFiles(directory=f"{BASE_DIR / 'static'}"), name="static")
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


def get_static_file(file_name: str):
    """Handler for returning static files.

    Parameters
    ----------
    file_name : str
        Name of file relative to ``static`` directory.
    """
    file_path = Path(app.root_path)
    # file_path = "/app"/ file_path / "static" / file_name
    file_path = f"{BASE_DIR}/static/{file_name}"
    # file_path = Path("/static" / file_name)

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
    """Get website logo."""
    return get_static_file("logo.png")


"""Error handling"""


@app.exception_handler(404)
async def get_404_handler(request, __):
    """Get and handle 404 errors."""
    return templates.TemplateResponse("404.html", {"request": request})


"""Serve dashboard"""


def stream_datacube(rgi_id):
    stream_url = f"https://cluster.klima.uni-bremen.de/~dtcg/datacubes_case_study_regions/v2026.2/L1_and_L2/{rgi_id}.zarr/"

    zipfile = f"./static/data/zarr_data/{rgi_id}.zarr.zip"
    store = zarr.storage.ZipStore(zipfile, mode="w")
    try:
        with xr.open_datatree(
            stream_url,
            group=None,
            chunks={},
            engine="zarr",
            consolidated=True,
            decode_cf=True,
        ) as stream:
            stream.compute().to_zarr(
                store=store,
                #     f"/static/data/zarr_data/{rgi_id}.zarr/",
                mode="w",
                consolidated=True,
                zarr_format=2,
                # encoding=stream.encoding,
            )
    except zarr.errors.GroupNotFoundError:
        raise HTTPException(status_code=403, detail="This data cube does not exist.")
    return zipfile


@app.get("/api/zarr/{rgi_id}")
async def download_datacube(rgi_id: str, format: str = "zarr"):
    # return StreamingResponse(stream_datacube(rgi_id=rgi_id))
    if format == "zip":
        return FileResponse(
            stream_datacube(rgi_id=rgi_id), filename=f"{rgi_id}.zarr.{format}"
        )
    else:
        return RedirectResponse(
            url=f"https://cluster.klima.uni-bremen.de/~dtcg/datacubes_case_study_regions/v2026.2/L1_and_L2/{rgi_id}.zarr/"
        )


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
    loading_indicator=False,
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
    return get_eolis_dashboard_with_selection()


# @add_application(
#     "/app/test",
#     app=app,
#     title="DTCG Dashboard",
#     # address=hostname,
#     # port=f"{port}",
#     # show=False,
#     # allow_websocket_origin=[
#     #     f"{hostname}:{port}",
#     #     f"localhost:{port}",
#     #     f"0.0.0.0:{port}",
#     # ],
# )
# def get_eolis_dashboard():
#     """Get the test dashboard."""
#     return get_eolis_dashboard_with_selection()
