"""
Copyright 2025-2026 DTCG Contributors

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

Panel wrapper displaying runoff for specific glaciers.
"""

from datetime import date
from pathlib import Path

import dtcg.integration.oggm_bindings as oggm_bindings
import dtcg.interface.plotting as dtcg_plotting
import geopandas as gpd
import holoviews as hv
import panel as pn
import param
from dtcg.api.external.call import StreamDatacube

pn.extension(
    design="material",
    sizing_mode="stretch_width",
    defer_load=True,
    loading_indicator=True,
    notifications=True,
)
hv.extension("bokeh")


class CryotempoSelection(param.Parameterized):
    """Panel wrapper for displaying datacubes.

    All processing and plot generation should be handled by the ``dtcg``
    backend, not this frontend. The wrapper binds DTCG API calls to a
    user interface.
    UI parameters declared here can be overwritten in the child
    interface.

    **Do not call functions from ``dtcg`` directly.** Instead:
        - Use the ``binder`` attribute to interact with OGGM via DTCG.
        - Use the ``artist`` attribute to plot data via DTCG.

    Attributes
    ----------
    year : param.Selector, default 2017
        Available reference years.
    figure : hv.Layout
        Arranges visual components into a single layout.
    plot : pn.pane.HoloViews
        Unified panel for all visual components. Only this visual
        attribute is passed to the client.
    smb : dict
        Specific mass balance data.
    gdir : GlacierDirectory
        Glacier directory.
    datacube : xr.Dataset
        EOLIS-enhanced gridded data.
    """

    # Public parameters editable via interface
    action = param.String(default="select_glacier")
    region_name = param.Selector(
        objects=["Central Europe", "Iceland"], default="Central Europe"
    )
    region_name_html = param.String("Central Europe")
    _glacier_names = param.List()
    _glacier_rgi_ids = param.List()
    glacier_name = param.Selector()
    year = param.Selector(
        objects=range(int(date.today().year) - 1, 1999, -1),
        default=int(date.today().year) - 1,
    )
    rgi_id = param.Selector()
    oggm_model = param.Selector(
        objects={"Daily": "DailyTIModel", "Daily Surface Tracking": "SfcTypeTIModel"},
        default="DailyTIModel",
    )

    # Private parameters
    use_multiprocessing = param.Boolean(True)
    cached_data = param.Boolean(True)
    oggm_params = param.Dict(
        default={
            "use_multiprocessing": True,
            "rgi_version": "62",
            "store_model_geometry": True,
        },
    )
    metadata = param.Dict(default=None)
    debug = param.Integer(default=200, bounds=(0, None))

    def __init__(self, **params):
        super(CryotempoSelection, self).__init__(**params)
        self.figure = hv.Layout()
        self.plot_oggm = pn.FlexBox(
            sizing_mode="stretch_width",
            styles={
                "flex": "1 1 auto",
                "align-items": "stretch",
                "align-content": "flex-start",
                "flex-wrap": "nowrap",
            },
        )
        self.plot_cryosat = pn.FlexBox(
            sizing_mode="stretch_width",
            styles=self.get_flex_styling(),
        )
        self.download_button = pn.WidgetBox()
        self.plot_title = pn.pane.HTML()
        self.map = pn.FlexBox()
        self.binder = oggm_bindings.BindingsCryotempo()
        self.streamer = StreamDatacube(
            server="https://cluster.klima.uni-bremen.de/~dtcg/datacubes_case_study_regions/v2026.2/L1_and_L2/"
        )
        if not self.cached_data:
            self.binder.init_oggm(working_dir="test")
        self.cache_path = Path("./static/data/l2_precompute").resolve()
        self.artist = dtcg_plotting.HoloviewsDashboardL1()
        self.data = None
        self.details = pn.pane.HTML()
        self.tap = hv.streams.Selection1D()
        self.metadata = self.get_metadata()
        self.set_rgi_id()
        if not self.cached_data:
            self.set_dashboard_data()
        else:
            self.set_dashboard_data_cached()

        self.region_name_html = self.set_region_name()
        self.get_glacier_names()

        self._hide_params()
        # self.data_store = self.get_data_store()

        self.set_plot()
        self.set_map()
        self.set_details()
        # self.download_button = pn.widgets.FileDownload(
        #     callback=pn.bind(self.download_datacube, rgi_id=self.rgi_id), filename=self.rgi_id
        # )
        # self.download_button = self.set_download_button()

    def get_flex_styling(self, style=None) -> dict:
        """Get CSS styling for flex boxes.

        .. note:: Not-so-temporary workaround for unsolved bugs in
        Panel:
           - https://github.com/holoviz/panel/issues/5343
           - https://github.com/holoviz/panel/issues/5054
           - https://github.com/holoviz/panel/issues/1296
        """
        if not style:
            style = {
                "flex": "1 1 auto",
                "align-items": "stretch",
                "align-content": "flex-start",
                "flex-wrap": "nowrap",
            }

        return style

    def _hide_params(self):
        """Hides parameters from GUI."""
        for p_name in [
            "rgi_id",
            "oggm_params",
            "action",
            "_glacier_names",
            "_glacier_rgi_ids",
            "cached_data",
            "metadata",
            "debug",
            "use_multiprocessing",
            "region_name_html",
        ]:
            self.param[p_name].precedence = -1

    @param.depends("rgi_id", "region_name_html", "glacier_name", "year", watch=True)
    def set_plot_metadata(self):
        if not self.glacier_name:
            glacier_name = "Hintereisferner"
        else:
            glacier_name = self.glacier_name
        self.region_name_html = self.set_region_name()
        title = f"{glacier_name}, {self.region_name_html} ({self.year})"
        self.plot_title.object = f"""<h1>{title}</h1>"""

    def get_metadata(self) -> dict:
        """Get glacier metadata.

        Stores glacier metadata to avoid calling and opening the same
        file multiple times.
        """
        # pn.io.loading.start_loading_spinner(self.plot)
        metadata = {"name": [""], "id": [""], "glacier_names": {}}
        if not self.cached_data:
            metadata["region_names"] = sorted(
                [
                    i["Full_name"]
                    for i in self.binder.get_rgi_metadata(
                        "rgi_regions.csv", from_web=True
                    )
                ]
            )
            metadata["glacier_names"] = self.binder.get_rgi_files_from_subregion(
                region_name=self.region_name, subregion_name=""
            )
        else:
            metadata["glacier_names"] = self.binder.get_cached_metadata(
                cache=self.cache_path, index=""
            )
            metadata["glacier_names"] = dict(sorted(metadata["glacier_names"].items()))
            glacier_hash = {}
            for k, v in metadata["glacier_names"].items():
                glacier_hash.update({j["Name"]: i for i, j in v.items()})
            metadata["lookup"] = glacier_hash
        # pn.io.loading.stop_loading_spinner(self.plot)
        return metadata

    @param.depends("region_name", watch=True)
    def get_glacier_names(self):
        glacier_names = self.metadata["glacier_names"][self.region_name]
        glacier_hash = {}
        for k, v in glacier_names.items():
            glacier_hash.update({v["Name"]: k})
        self.metadata["hash"] = glacier_hash
        self._glacier_names = sorted(list(glacier_hash.keys()))
        self._glacier_rgi_ids = sorted(list(glacier_hash.values()))

    @param.depends("year", "debug", "glacier_name", "oggm_model", watch=True)
    def set_plot(self):
        """Set component graphics.

        This updates the main dashboard content.
        """

        if self.data is not None:

            rgi_id = self.get_rgi_id(self.glacier_name)
            if rgi_id not in self.data.keys():
                data = self.get_cached_data(rgi_id=rgi_id)
                self.data[rgi_id] = data
            data = self.data[rgi_id]
            self.figure = self.plot_dashboard_l1(
                data=data,
                glacier_name=self.glacier_name,
                model_name=self.oggm_model,
            )
            self.plot_oggm.objects = [i for i in self.figures]
            self.figure = self.plot_dashboard_l2(
                data=data,
                glacier_name=self.glacier_name,
            )
            self.plot_cryosat.objects = [i for i in self.figures]

    @param.depends("debug", "glacier_name", watch=True)
    def set_map(self):
        if self.data is not None:
            rgi_id = self.get_rgi_id(glacier_name=self.glacier_name)
            data = self.data[rgi_id]

            glacier_map = self.plot_selection_map(data=data, rgi_id=rgi_id).opts(
                max_width=250
            )
            self.tap.source = glacier_map
            self.map.objects = [glacier_map]

    @param.depends("debug", "glacier_name", watch=True)
    def set_details(self):

        if self.data is not None:
            rgi_id = self.get_rgi_id(self.glacier_name)
            details = self.binder.get_outline_details(
                polygon=self.data[rgi_id]["outlines"].iloc[0]
            )
            table = ""
            for k, v in details.items():
                if isinstance(v["value"], float):
                    value = f"{v['value']:.2f}"
                else:
                    value = v["value"]
                table_row = (
                    f"<tr><th>{k}</th><td>{' '.join((f'{value}', v['unit']))}</td></tr>"
                )
                table = f"{table}{table_row}"

            self.details.object = (
                f"<hr></hr><h2>Glacier Details</h2><table>{table}</table><hr></hr>"
            )

    @param.depends("glacier_name")
    def set_rgi_id(self):
        """Set glacier RGI-ID from a glacier name."""
        self.rgi_id = self.get_rgi_id(glacier_name=self.glacier_name)
        self.region_name_html = self.set_region_name()

    def get_rgi_id(self, glacier_name):
        """Get glacier RGI-ID from a glacier name."""
        default_glacier = "RGI60-11.00897"  # Hef because it appears first
        rgi_id = self.metadata["lookup"].get(glacier_name, default_glacier)

        return rgi_id

    @param.depends("region_name_html", "rgi_id", "glacier_name", watch=True)
    def set_region_name(self):
        """Set region name from RGI ID."""

        rgi_id = self.get_rgi_id(self.glacier_name)
        region_id = rgi_id.split("-")[1]

        if "11." in region_id:
            self.param.update(region_name_html="Central Europe")
            # self.region_name_html = "Central Europe"
        elif "06." in region_id:
            self.param.update(region_name_html="Iceland")
            # self.region_name_html = "Iceland"
        else:
            self.param.update(region_name_html="")
            # self.region_name_html = ""

        return self.region_name_html

    def get_zipped_datacube(
        self, rgi_id, zip_path=Path("./static/data/zarr_data/")
    ) -> Path:
        # pn.state.notifications.info("Zipping, please wait...", duration=2000)
        try:
            path = self.streamer.zip_datacube(zip_path=zip_path, rgi_id=rgi_id)
        except FileNotFoundError as e:
            pn.state.notifications.position = "bottom-left"
            pn.state.notifications.error(
                "No datacube available for this glacier.", duration=3000
            )
            path = ""
        finally:
            return path  # avoid unbound local errors and other such things

        return path

    @pn.depends("rgi_id", "glacier_name", watch=True)
    def set_download_button(self):
        rgi_id = self.get_rgi_id(self.glacier_name)
        self.param.update(rgi_id=rgi_id)
        self.download_button.objects = [
            pn.widgets.FileDownload(
                callback=pn.bind(self.get_zipped_datacube, rgi_id=rgi_id),
                filename=f"{rgi_id}.zarr.zip",
                label="Download Datacube",
            )
        ]
        return self.download_button

    def set_dashboard_data(self) -> dict:
        """Get data from OGGM."""
        gdir, datacube = self.get_data([self.rgi_id])
        print("Calibrating model...")
        _, _, smb = self.binder.calibrator.run_calibration(
            gdir=gdir, datacube=datacube, model=self.oggm_model
        )
        runoff_data = self.binder.get_aggregate_runoff(gdir=gdir)
        self.data = {
            "gdir": gdir,
            "eolis": datacube,
            "smb": smb,
            "runoff_data": runoff_data,
        }

    @param.depends("rgi_id", "glacier_name", watch=True)
    def set_dashboard_data_cached(self) -> dict:
        """Get data from precomputed cache.

        This skips all processing steps, and the data is loaded into the
        same formats as would otherwise be expected when running
        post-processing.

        Returns
        -------
        dict
            GlacierDirectory parameters as dict, surface mass balance as
            a np.ndarray, datacubes and runoff data as xr.Datasets,
            glacier outlines as a gpd.Dataframe.
        """

        if self.data is None:
            self.data = {}
        data = self.get_cached_data(rgi_id=self.rgi_id)
        self.data[self.rgi_id] = data

    def get_cached_data(self, rgi_id: str) -> dict:
        """Load a single precomputed glacier data file.

        Parameters
        ----------
        rgi_id : str
            Glacier RGI ID.

        Returns
        -------
        dict
            Cached glacier dataset containing minimal GlacierDirectory
            data, datacube, time series for specific mass balance and
            runoff, and glacier outline. Unavailable datasets default
            to a ``NoneType`` object.
        """
        cached_data = self.binder.get_cached_data(rgi_id=rgi_id, cache=self.cache_path)
        data = {
            "gdir": cached_data.get("gdir", None),
            "eolis": cached_data.get("eolis", None),
            "smb": cached_data.get("smb", None),
            "runoff_data": cached_data.get("runoff", None),
            "outlines": cached_data.get("outlines", None),
        }
        return data

    def get_data(self, rgi_ids: list):
        """Get dashboard data.

        Returns
        -------
        tuple
            Glacier directory, EOLIS-enhanced gridded data, and
            specific mass balance.
        """
        self.binder.init_oggm(working_dir="test")
        gdir = self.binder.get_glacier_directories(
            rgi_ids=rgi_ids, prepro_level=4, prepro_border=80
        )[0]
        print("Fetching OGGM data from shop...")
        self.binder.get_glacier_data(gdirs=[gdir])
        print("Checking flowlines...")
        self.binder.set_flowlines(gdir)
        print("Streaming data from Specklia...")
        gdir, datacube = self.binder.get_eolis_data(gdir)
        return gdir, datacube

    # @pn.cache
    def get_cached_region_outlines(
        self,
        region_id: int,
        file_name="glacier_outlines.shp",
    ) -> gpd.GeoDataFrame:
        """Get subregion domain outlines.

        TODO: Only merge the glacier outlines into a single file if
        caching middleware exists, as FastAPI doesn't cache by default.

        Parameters
        ----------
        region_id : int
            O1 region ID number.
        file_name : str
            Shapefile name.
        """
        try:
            shapefile_path = Path(
                self.cache_path / f"RGI60-{str(region_id).zfill(2)}/{file_name}"
            )
            shapefile = gpd.read_feather(shapefile_path)
        except FileNotFoundError:
            return None

        return shapefile

    def plot_selection_map(self, data: dict, rgi_id: str = "") -> hv.Layout:
        """Plot map showing the selected glacier.

        Parameters
        ----------
        data : dict
            Contains glacier data, shapefile, and optionally runoff
            data and observations.
        glacier_name : str, optional
            Name of glacier in subregion. Default empty string.

        Returns
        -------
        hv.Layout
            Dashboard showing a map of the subregion and runoff data.
        """
        self.plot_map = dtcg_plotting.BokehMapOutlines()
        try:
            region_id = int(rgi_id[6:8])
            shapefile = self.get_cached_region_outlines(region_id=region_id)
            fig_glacier_highlight = self.plot_map.plot_region_with_glacier(
                shapefile=shapefile, rgi_id=rgi_id
            ).opts(xlabel="", ylabel="", xaxis=None, yaxis=None, scalebar=True)
            return fig_glacier_highlight
        except:
            return hv.Overlay([])

    def plot_dashboard(
        self,
        data,
        glacier_name: str = "",
    ) -> hv.Layout:
        """Plot a dashboard showing runoff data.

        Parameters
        ----------
        data : dict
            Contains glacier data, shapefile, and optionally runoff
            data and observations.
        glacier_name : str, optional
            Name of glacier in subregion. Default empty string.

        Returns
        -------
        hv.Layout
            Dashboard showing EO and modelled specific mass balance and
            runoff.
        """
        self.plot_cryo = dtcg_plotting.BokehSynthetic()
        self.plot_graph = dtcg_plotting.BokehGraph()
        self.plot_map = dtcg_plotting.BokehMapOutlines()

        runoff_data = data["runoff_data"]
        gdir = data["gdir"]
        datacube = data["eolis"]
        smb = data["smb"]

        fig_monthly_runoff = self.plot_graph.plot_runoff_timeseries(
            runoff=runoff_data["monthly_runoff"], ref_year=self.year, nyears=27
        )
        fig_runoff_cumulative = self.plot_graph.plot_runoff_timeseries(
            runoff=runoff_data["monthly_runoff"],
            ref_year=self.year,
            cumulative=True,
            nyears=27,
        )
        fig_daily_mb = self.plot_cryo.plot_mb_comparison(
            smb=smb,
            ref_year=self.year,
            datacube=None,
            gdir=gdir,
            cumulative=False,
        )
        fig_cumulative_mb = self.plot_cryo.plot_mb_comparison(
            smb=smb,
            ref_year=self.year,
            datacube=None,
            gdir=gdir,
            cumulative=True,
        )
        figures = [
            fig_daily_mb,
            fig_cumulative_mb,
            fig_monthly_runoff,
            fig_runoff_cumulative,
        ]

        if datacube is not None:
            fig_eo_elevation = self.plot_cryo.plot_eolis_timeseries(
                datacube=datacube,
                mass_balance=True,
                glacier_area=gdir.get("rgi_area_km2", None),
            ).opts(title="Monthly Cumulative Specific Mass Balance (CryoSat)")

            fig_eo_smb = self.plot_cryo.plot_eolis_smb(
                datacube=datacube,
                ref_year=self.year,
                years=None,
                cumulative=False,
                glacier_area=gdir.get("rgi_area_km2", None),
            ).opts(title="Cumulative Specific Mass Balance (CryoSat)")
            figures = [
                hv.Layout(
                    fig_daily_mb.opts(title=f"Specific Mass Balance (OGGM)")
                    + fig_eo_elevation
                ).opts(tabs=True),
                hv.Layout(
                    fig_cumulative_mb.opts(
                        title=f"Cumulative Specific Mass Balance (OGGM)"
                    )
                    + fig_eo_smb
                ).opts(tabs=True),
                fig_monthly_runoff,
                fig_runoff_cumulative,
            ]
        self.figures = figures

        if glacier_name:
            self.artist.set_dashboard_title(name=self.glacier_name)

        self.artist.dashboard = pn.Column(
            hv.Layout(figures[:2]).opts(
                shared_axes=False,
                title=self.artist.title,
                fontsize={"title": 18},
                sizing_mode="stretch_width",
                merge_tools=False,
                tabs=True,
            ),
            pn.Row(
                hv.Layout(figures[2:]).opts(
                    shared_axes=False, sizing_mode="stretch_width", merge_tools=False
                )
            ),
        )

        return self.artist.dashboard

    def plot_dashboard_l1(
        self, data, glacier_name: str = "", model_name: str = "DailyTIModel"
    ) -> hv.Layout:
        """Plot a dashboard showing runoff data.

        Parameters
        ----------
        data : dict
            Contains glacier data, shapefile, and optionally runoff
            data and observations.
        glacier_name : str, optional
            Name of glacier in subregion. Default empty string.

        Returns
        -------
        hv.Layout
            Dashboard showing EO and modelled specific mass balance and
            runoff.
        """
        self.plot_cryo = dtcg_plotting.BokehSynthetic()
        self.plot_graph = dtcg_plotting.BokehGraph()
        self.plot_map = dtcg_plotting.BokehMapOutlines()

        runoff_data = data["runoff_data"]["Daily_Hugonnet_2000_2020"]
        gdir = data["gdir"]
        datacube = data.get("eolis", None)
        smb = data["smb"]

        # if len(smb.keys()) > 1:
        #     for key, value in smb.items():
        #         if "Cryosat" in key:
        #             smb = {key: value}
        # else:
        # smb = smb["Daily_Hugonnet_2000_2020"]

        fig_monthly_runoff = self.plot_graph.plot_runoff_timeseries(
            runoff=runoff_data["monthly_runoff"], ref_year=self.year, nyears=27
        )
        fig_runoff_cumulative = self.plot_graph.plot_runoff_timeseries(
            runoff=runoff_data["monthly_runoff"],
            ref_year=self.year,
            cumulative=True,
            nyears=27,
        )

        fig_daily_mb = self.plot_cryo.plot_mb_comparison(
            smb=smb,
            ref_year=self.year,
            datacube=datacube,
            gdir=gdir,
            cumulative=False,
            model_name=model_name,
        )
        fig_cumulative_mb = self.plot_cryo.plot_mb_comparison(
            smb=smb,
            ref_year=self.year,
            datacube=datacube,
            gdir=gdir,
            cumulative=True,
            model_name=model_name,
        )

        figures = [
            fig_daily_mb.opts(title=f"Specific Mass Balance (OGGM)"),
            fig_cumulative_mb.opts(title=f"Cumulative Specific Mass Balance (OGGM)"),
            fig_monthly_runoff,
            fig_runoff_cumulative,
        ]

        if datacube is not None:
            figures = [
                fig_daily_mb.opts(title=f"Specific Mass Balance (OGGM + CryoSat)"),
                fig_cumulative_mb.opts(
                    title=f"Cumulative Specific Mass Balance (OGGM + CryoSat)"
                ),
                fig_monthly_runoff,
                fig_runoff_cumulative,
            ]
        self.figures = figures

        if glacier_name:
            self.artist.set_dashboard_title(name=self.glacier_name)

        self.artist.dashboard = pn.Column(
            pn.Row(
                hv.Layout(figures[:2]).opts(
                    shared_axes=False,
                    title=self.artist.title,
                    fontsize={"title": 18},
                    sizing_mode="stretch_width",
                    merge_tools=False,
                ),
                styles=self.get_flex_styling(),
            ),
            pn.Row(
                hv.Layout(figures[2:]).opts(
                    shared_axes=False, sizing_mode="stretch_width", merge_tools=False
                ),
                styles=self.get_flex_styling(),
            ),
            styles=self.get_flex_styling(),
        )

        return self.artist.dashboard

    def plot_dashboard_l2(
        self,
        data,
        glacier_name: str = "",
    ) -> hv.Layout:
        """Plot a dashboard showing runoff data.

        Parameters
        ----------
        data : dict
            Contains glacier data, shapefile, and optionally runoff
            data and observations.
        glacier_name : str, optional
            Name of glacier in subregion. Default empty string.

        Returns
        -------
        hv.Layout
            Dashboard showing EO and modelled specific mass balance and
            runoff.
        """
        self.plot_cryo = dtcg_plotting.BokehSynthetic()
        self.plot_graph = dtcg_plotting.BokehGraph()
        self.plot_map = dtcg_plotting.BokehMapOutlines()

        gdir = data["gdir"]
        datacube = data["eolis"]
        figures = []
        if datacube is not None:
            fig_eo_elevation = self.plot_cryo.plot_eolis_timeseries(
                datacube=datacube,
                mass_balance=True,
                glacier_area=gdir.get("rgi_area_km2", None),
            ).opts(title="Monthly Cumulative Specific Mass Balance (CryoSat)")

            fig_eo_smb = self.plot_cryo.plot_eolis_smb(
                datacube=datacube,
                ref_year=self.year,
                years=None,
                cumulative=False,
                glacier_area=gdir.get("rgi_area_km2", None),
            ).opts(title="Cumulative Specific Mass Balance (CryoSat)")
            figures = [
                fig_eo_elevation,
                fig_eo_smb,
            ]
        self.figures = figures

        if not glacier_name:
            glacier_name = gdir.get("name", "")

        self.artist.set_dashboard_title(name=glacier_name)

        self.artist.dashboard = pn.Column(
            hv.Layout(figures).opts(
                shared_axes=False,
                title=self.artist.title,
                fontsize={"title": 18},
                sizing_mode="stretch_width",
                merge_tools=False,
            ),
            styles=self.get_flex_styling(),
        )
        if datacube is None:
            self.artist.dashboard = pn.Column(
                "No CryoSat data available.", name="CryoSat Data"
            )
            self.figures = [
                pn.Column("No CryoSat data available.", name="CryoSat Data")
            ]

        return self.artist.dashboard
