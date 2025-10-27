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

Panel wrapper displaying runoff for specific glaciers.
"""

from pathlib import Path

import dtcg.integration.oggm_bindings as oggm_bindings
import dtcg.interface.plotting as dtcg_plotting
import holoviews as hv
import geopandas as gpd
import panel as pn
import param

pn.extension(design="material", sizing_mode="stretch_width")
pn.extension(loading_spinner="dots", loading_color="#00aa41", template="material")
pn.param.ParamMethod.loading_indicator = True
hv.extension("bokeh")


class CryotempoComparison(param.Parameterized):
    """Panel wrapper around DTCG API.

    All computations should be processed by DTCG backend API, not this
    frontend. The wrapper binds DTCG API calls to a user interface.
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

    action = param.String(default="select_glacier")
    region_name = param.Selector(
        objects=["Central Europe", "Iceland"], default="Iceland"
    )
    _glacier_names = param.List(default=[""])
    glacier_name = param.Selector()
    year = param.Selector(objects=range(2000, 2020), default=2017)
    rgi_id = param.Selector()
    oggm_model = param.Selector(
        objects={"Daily": "DailyTIModel", "Daily Surface Tracking": "SfcTypeTIModel"},
        default="DailyTIModel",
    )
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

    def __init__(
        self, cache_path: Path = Path("./static/data/l2_precompute").resolve(), **params
    ):
        super(CryotempoComparison, self).__init__(**params)
        self.figure = hv.Layout()
        self.binder = oggm_bindings.BindingsCryotempo()
        if not self.cached_data:
            self.binder.init_oggm(dirname="test")
        self.cache_path = cache_path
        self.artist = dtcg_plotting.HoloviewsDashboardL2()
        self.data = None
        self.plot = pn.pane.HoloViews(self.figure, sizing_mode="scale_both")
        self.metadata = self.get_metadata()
        # if self.glacier_name:
        self.rgi_id = self.set_rgi_id()
        self._hide_params()
        if not self.cached_data:
            self.get_dashboard_data()
        else:
            self.get_dashboard_data_cached()
        self.set_plot()

    def _hide_params(self):
        """Hides parameters from GUI."""
        for p_name in [
            "rgi_id",
            "oggm_params",
            "action",
            "_glacier_names",
            "region_name",
            "cached_data",
            "metadata",
            "debug",
        ]:
            self.param[p_name].precedence = -1

    @param.depends("region_name")
    def get_metadata(self) -> dict:
        """Get glacier metadata.

        Stores glacier metadata to avoid calling and opening the same
        file multiple times.
        """
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

        return metadata

    @param.depends(
        "year",
        "debug",
        "region_name",
        "glacier_name",
        "rgi_id",
        "oggm_model",
        watch=True,
    )
    def set_plot(self):
        """Set component graphics."""
        if self.data is not None:
            self.rgi_id = self.set_rgi_id()

            self.figure = self.plot_dashboard(
                data=self.data,
                glacier_name=self.glacier_name,
            )
            self.plot.object = self.figure

    @param.depends("glacier_name", "rgi_id")
    def set_rgi_id(self):

        self.rgi_id = self.metadata["lookup"].get(self.glacier_name, "RGI60-06.00377")
        return self.rgi_id

    @param.depends(
        "region_name",
        "glacier_name",
        "oggm_params",
        "rgi_id",
        "oggm_model",
        watch=False,
    )
    def get_dashboard_data(self) -> dict:
        """Get data from OGGM."""
        pn.io.loading.start_loading_spinner(self.plot)
        gdir, datacube = self.get_data([self.rgi_id])
        print("Calibrating model...")
        _, _, smb = self.binder.calibrator.run_calibration(
            gdir=gdir, datacube=datacube, model=self.oggm_model
        )
        runoff_data = self.binder.get_aggregate_runoff(gdir=gdir)
        self.data = {
            "gdir": gdir,
            "datacube": datacube,
            "smb": smb,
            "runoff_data": runoff_data,
        }
        pn.io.loading.stop_loading_spinner(self.plot)

    @param.depends(
        "region_name",
        "glacier_name",
        "oggm_params",
        "rgi_id",
        "oggm_model",
        watch=True,
    )
    def get_dashboard_data_cached(self) -> dict:
        """Get data from OGGM."""

        self.rgi_id = self.set_rgi_id()
        pn.io.loading.start_loading_spinner(self.plot)

        cached_data = self.binder.get_cached_data(
            rgi_id=self.rgi_id, cache=self.cache_path
        )
        run_name = f"{self.oggm_model}_Hugonnet_2000-01-01_2020-01-01"

        self.data = {
            "gdir": cached_data.get("gdir", None),
            "datacube": cached_data.get("eolis", None),
            "smb": cached_data.get("smb", None),
            "runoff_data": cached_data.get("runoff_data", None),
        }
        pn.io.loading.stop_loading_spinner(self.plot)

    def get_data(self, rgi_ids: list):
        """Get dashboard data.

        Returns
        -------
        tuple
            Glacier directory, EOLIS-enhanced gridded data, and specific mass balance.
        """
        self.binder.init_oggm(dirname="test")
        gdir = self.binder.get_glacier_directories(
            rgi_ids=rgi_ids, prepro_level=4, prepro_border=80
        )[0]
        print("Fetching OGGM data from shop...")
        self.binder.get_glacier_data(gdirs=[gdir])
        print("Checking flowlines...")
        self.binder.set_flowlines(gdir)
        print("Streaming data from Specklia...")
        # gdir, datacube = self.binder.get_eolis_data(gdir)
        datacube = None
        return gdir, datacube

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
            Dashboard showing a map of the subregion and runoff data.
        """

        self.plot_cryo = dtcg_plotting.BokehSynthetic()
        self.plot_graph = dtcg_plotting.BokehGraph()

        runoff_data = data["runoff_data"]
        gdir = data["gdir"]
        datacube = data["datacube"]
        smb = data["smb"]

        fig_monthly_runoff = self.plot_graph.plot_runoff_timeseries(
            runoff=runoff_data["monthly_runoff"],
            ref_year=self.year,
            year_minimum_runoff=runoff_data["runoff_year_min"],
            year_maximum_runoff=runoff_data["runoff_year_max"],
        )
        fig_runoff_cumulative = self.plot_graph.plot_runoff_timeseries(
            runoff=runoff_data["monthly_runoff"],
            ref_year=self.year,
            cumulative=True,
        )
        fig_daily_mb = self.plot_cryo.plot_mb_comparison(
            smb=smb,
            ref_year=self.year,
            datacube=datacube,
            gdir=gdir,
            cumulative=False,
        )
        fig_cumulative_mb = self.plot_cryo.plot_mb_comparison(
            smb=smb,
            ref_year=self.year,
            datacube=datacube,
            gdir=gdir,
            cumulative=True,
        )
        figures = [
            fig_daily_mb,
            fig_cumulative_mb,
            fig_monthly_runoff,
            fig_runoff_cumulative,
        ]
        self.figures = figures
        if glacier_name:
            self.artist.set_dashboard_title(name=self.glacier_name)
        dashboard = self.artist.set_dashboard(figures=figures)
        return self.artist.dashboard


class CryotempoSelection(param.Parameterized):
    """Panel wrapper around DTCG API for L1 datacubes.

    All computations should be processed by DTCG backend API, not this
    frontend. The wrapper binds DTCG API calls to a user interface.
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

    action = param.String(default="select_glacier")
    region_name = param.Selector(
        objects=["Central Europe", "Iceland"], default="Iceland"
    )
    _glacier_names = param.List(default=[""])
    glacier_name = param.Selector()
    year = param.Selector(objects=range(2000, 2020), default=2017)
    rgi_id = param.Selector()
    oggm_model = param.Selector(
        objects={"Daily": "DailyTIModel", "Daily Surface Tracking": "SfcTypeTIModel"},
        default="DailyTIModel",
    )
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
        self.binder = oggm_bindings.BindingsCryotempo()
        if not self.cached_data:
            self.binder.init_oggm(dirname="test")
        self.cache_path = Path("./static/data/l2_precompute").resolve()
        self.artist = dtcg_plotting.HoloviewsDashboardL1()
        self.data = None
        self.plot = pn.FlexBox()
        self.map = pn.FlexBox()
        self.metadata = self.get_metadata()
        # if self.glacier_name:
        self.rgi_id = self.set_rgi_id()
        self._hide_params()
        if not self.cached_data:
            self.get_dashboard_data()
        else:
            self.get_dashboard_data_cached()
        self.set_plot()

    def _hide_params(self):
        """Hides parameters from GUI."""
        for p_name in [
            "rgi_id",
            "oggm_params",
            "action",
            "_glacier_names",
            "region_name",
            "cached_data",
            "metadata",
            "debug",
        ]:
            self.param[p_name].precedence = -1

    @pn.cache
    @param.depends("region_name")
    def get_metadata(self) -> dict:
        """Get glacier metadata.

        Stores glacier metadata to avoid calling and opening the same
        file multiple times.
        """
        pn.io.loading.start_loading_spinner(self.plot)
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
        pn.io.loading.stop_loading_spinner(self.plot)
        return metadata

    @param.depends(
        "year",
        "debug",
        "region_name",
        "glacier_name",
        "rgi_id",
        "oggm_model",
        watch=True,
    )
    def set_plot(self):
        """Set component graphics.

        This updates the main dashboard content.
        """
        if self.data is not None:
            self.rgi_id = self.set_rgi_id()
            self.figure = self.plot_dashboard(
                data=self.data,
                glacier_name=self.glacier_name,
            )
            self.map.objects = [
                self.plot_selection_map(
                    data=self.data, glacier_name=self.glacier_name
                ).opts(max_width=250)
            ]
            self.plot.objects = [i for i in self.figures]

    @param.depends("glacier_name", "rgi_id")
    def set_rgi_id(self):
        """Set glacier RGI-ID from a glacier name."""

        default_glacier = "RGI60-11.00897"  # Hef because it appears first
        self.rgi_id = self.metadata["lookup"].get(self.glacier_name, default_glacier)
        return self.rgi_id

    @param.depends(
        "region_name",
        "glacier_name",
        "oggm_params",
        "rgi_id",
        "oggm_model",
        watch=False,
    )
    def get_dashboard_data(self) -> dict:
        """Get data from OGGM."""
        pn.io.loading.start_loading_spinner(self.plot)
        gdir, datacube = self.get_data([self.rgi_id])
        print("Calibrating model...")
        _, _, smb = self.binder.calibrator.run_calibration(
            gdir=gdir, datacube=datacube, model=self.oggm_model
        )
        runoff_data = self.binder.get_aggregate_runoff(gdir=gdir)
        self.data = {
            "gdir": gdir,
            "datacube": datacube,
            "smb": smb,
            "runoff_data": runoff_data,
        }
        pn.io.loading.stop_loading_spinner(self.plot)

    @param.depends(
        "region_name",
        "glacier_name",
        "oggm_params",
        "rgi_id",
        "oggm_model",
        watch=True,
    )
    def get_dashboard_data_cached(self) -> dict:
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

        pn.io.loading.start_loading_spinner(self.plot)
        self.rgi_id = self.set_rgi_id()
        cached_data = self.binder.get_cached_data(
            rgi_id=self.rgi_id, cache=self.cache_path
        )
        run_name = f"{self.oggm_model}_Hugonnet_2000-01-01_2020-01-01"

        self.data = {
            "gdir": cached_data.get("gdir", None),
            "datacube": cached_data.get("eolis", None),
            "smb": cached_data.get("smb", None),
            "runoff_data": cached_data.get("runoff", None),
            "outlines": cached_data.get("outlines", None),
        }
        pn.io.loading.stop_loading_spinner(self.plot)

    def get_data(self, rgi_ids: list):
        """Get dashboard data.

        Returns
        -------
        tuple
            Glacier directory, EOLIS-enhanced gridded data, and
            specific mass balance.
        """
        self.binder.init_oggm(dirname="test")
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

    @pn.cache
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

    @pn.cache
    def plot_selection_map(self, data: dict, glacier_name: str = "") -> hv.Layout:
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
        outlines = data["outlines"].to_crs(4326)

        title = outlines.get("Name", [""])[0]
        region_id = int(self.rgi_id[6:8])
        shapefile = self.get_cached_region_outlines(region_id=region_id)
        fig_glacier_highlight = self.plot_map.plot_region_with_glacier(
            shapefile=shapefile, rgi_id=self.rgi_id
        ).opts(xlabel="", ylabel="", xaxis=None, yaxis=None, scalebar=True)
        return fig_glacier_highlight

    @pn.cache
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
        datacube = data["datacube"]
        smb = data["smb"]

        fig_monthly_runoff = self.plot_graph.plot_runoff_timeseries(
            runoff=runoff_data["monthly_runoff"],
            ref_year=self.year,
            year_minimum_runoff=runoff_data["runoff_year_min"],
            year_maximum_runoff=runoff_data["runoff_year_max"],
        )
        fig_runoff_cumulative = self.plot_graph.plot_runoff_timeseries(
            runoff=runoff_data["monthly_runoff"],
            ref_year=self.year,
            cumulative=True,
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
                mass_balance=False,
            ).opts(title="Elevation Change (CryoSat)")

            fig_eo_smb = self.plot_cryo.plot_eolis_timeseries(
                datacube=datacube,
                mass_balance=True,
                glacier_area=gdir.get("rgi_area_km2", None),
            ).opts(title="Specific Mass Balance (CryoSat)")
            figures = [
                hv.Layout(
                    fig_daily_mb.opts(title=f"Specific Mass Balance (OGGM)")
                    + fig_eo_smb
                ).opts(tabs=True),
                hv.Layout(
                    fig_cumulative_mb.opts(
                        title=f"Cumulative Specific Mass Balance (OGGM)"
                    )
                    + fig_eo_elevation
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
                sizing_mode="scale_both",
                merge_tools=False,
                tabs=True,
            ),
            pn.Row(
                hv.Layout(figures[2:]).opts(
                    shared_axes=False, sizing_mode="scale_both", merge_tools=False
                )
            ),
        )

        return self.artist.dashboard
