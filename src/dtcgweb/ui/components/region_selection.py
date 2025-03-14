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

import dtcg.integration.oggm_bindings as oggm_bindings
import dtcg.interface.plotting as dtcg_plotting
import holoviews as hv
import panel as pn
import param

pn.extension(design="material", sizing_mode="stretch_width")
pn.extension(loading_spinner="dots", loading_color="#00aa41", template="material")
pn.param.ParamMethod.loading_indicator = True
hv.extension("bokeh")

data_server_address = "https://cluster.klima.uni-bremen.de/~dtcg/test_files/case_study_regions/austria/nested_catchments_oetztal"


class RegionSelection(param.Parameterized):
    """Panel wrapper around DTCG API.

    All computations should be processed by DTCG backend API, not this
    frontend. The wrapper binds DTCG API calls to a user interface.
    UI parameters declared here can be overwritten in the child
    interface.

    **Do not call functions from ``dtcg`` directly.** Instead:
        - Use the ``binder`` attribute to interact with OGGM via DTCG.
        - Use the ``artist`` attribute to plot data via DTCG.

    Parameters
    ----------

    action : param.String, default="select_glacier"
    region_name : param.Selector, default "Central Europe"
        RGI region name.
    subregion_name : param.Selector, default "tumpen_oetztalerache"
        RGI subregion name.
    glacier_name : param.Selector, default "Vernagtferner"
        Name or RGI-ID of glacier. RGI-IDs are filtered out of the
        dropdown menu.
    upload_shapefile : param.Bytes, default None
        A shapefile for a catchment area uploaded by the user.
    shapefile_path : param.String, optional
        Path to a shapefile for a catchment area.
        Default "nested_catchments_oetztal/nested_catchments_oetztal.shx".
    use_multiprocessing : param.Boolean, default True
        Let OGGM use multiprocessing.
    oggm_params : param.Dict, optional
        OGGM configuration parameters. Default key/value pairs:
            * "use_multiprocessing": True,
            * "rgi_version": "62",
            * "store_model_geometry": True,
    get_runoff : param.Event
        Trigger to compute glacier runoff.
    metadata : param.Dict, default None
        Stores glacier metadata to avoid opening and closing a file
        multiple times.
    binder : oggm_bindings.BindingsHydro
        Orchestrates OGGM bindings via the DTCG backend API. All calls
        to OGGM should go through here.
    artist : dtcg_plotting.HoloviewsDashboard
        Constructs and orchestrates visual components via the DTCG API.
    figure : hv.Layout
        Arranges visual components into a single layout.
    plot : pn.pane.HoloViews
        Unified panel for all visual components. Only this visual
        attribute is passed to the client.
    callback_runoff : Callable
        Callback which binds the ``get_runoff`` trigger to get and
        process runoff data.
    data : dict, default None
        Stores glacier, shapefile, and runoff data.
    """

    action = param.String(default="select_glacier")
    # region_name = param.Selector(default="Central Europe")
    # names = sorted(
    #     [
    #         i["Full_name"]
    #         for i in oggm_bindings.get_rgi_metadata("rgi_regions.csv", from_web=True)
    #     ]
    # )
    region_name = param.Selector(default="Central Europe")
    subregion_name = param.Selector(default="tumpen_oetztalerache")
    _glacier_names = param.List(default=[""])
    glacier_name = param.Selector(default="Vernagtferner")
    upload_shapefile = param.Bytes(default=None)
    shapefile_path = param.String(
        default="nested_catchments_oetztal/nested_catchments_oetztal.shx"
    )
    use_multiprocessing = param.Boolean(True)
    oggm_params = param.Dict(
        default={
            "use_multiprocessing": True,
            "rgi_version": "62",
            "store_model_geometry": True,
        },
    )
    get_runoff = param.Event()
    metadata = param.Dict(default=None)
    debug = param.Integer(default=200, bounds=(0, None))

    def __init__(self, **params):
        super(RegionSelection, self).__init__(**params)

        self.binder = oggm_bindings.BindingsHydro()
        self.artist = dtcg_plotting.HoloviewsDashboard()
        self.figure = hv.Layout()
        self.plot = pn.pane.HoloViews(self.figure, sizing_mode="scale_both")
        self.metadata = self.get_metadata()
        self.callback_runoff = pn.bind(self.get_runoff_data, self.get_runoff)
        self._hide_params()
        self.update_plot()

    def _hide_params(self):
        """Hides parameters from GUI."""
        for p_name in [
            "oggm_params",
            "action",
            "shapefile_path",
            "_glacier_names",
            # "glacier_name",
            "metadata",
        ]:
            self.param[p_name].precedence = -1

    @param.depends("shapefile_path", "upload_shapefile")
    def get_metadata(self) -> dict:
        """Get glacier metadata.

        Stores glacier metadata to avoid calling and opening the same
        file multiple times.
        """
        if not self.shapefile_path:
            metadata = {"name": [""], "id": [""]}
        elif not self.upload_shapefile:
            shapefile_path = f"{self.binder.SHAPEFILE_PATH}/{self.shapefile_path}"
        else:
            self.shapefile_path = self.upload_shapefile
            shapefile_path = self.shapefile_path
        if self.shapefile_path:
            shapefile = self.binder.get_shapefile(path=shapefile_path)
            metadata = self.binder.get_shapefile_metadata(shapefile=shapefile)
            metadata["region_names"] = sorted(
                [
                    i["Full_name"]
                    for i in self.binder.get_rgi_metadata(
                        "rgi_regions.csv", from_web=True
                    )
                ]
            )
        return metadata

    @param.depends(
        "debug",
        # "region_name",
        "subregion_name",
        "glacier_name",
        "shapefile_path",
        "upload_shapefile",
        # "oggm_params",
        watch=True,
    )
    def update_plot(self):
        """Get new figures and update the plot attribute.

        Triggered if the user selects a new shapefile, glacier, or
        region.
        """
        data = self.get_dashboard_data()
        if data is not None:
            self.data = data
            self.figure = self.artist.plot_runoff_dashboard(
                data=self.data,
                subregion_name=self.subregion_name,
                glacier_name=self.glacier_name,
            )
            self.plot.object = self.figure
        # self.cds.data = dict(x=x, y=y)
        # self.plot.x_range.start, self.plot.x_range.end = self.x_range
        # self.plot.y_range.start, self.plot.y_range.end = self.y_range

    @param.depends(
        "get_runoff",
        watch=True,
    )
    def get_runoff_data(self):
        """Get, process, and plot runoff data."""
        # TODO: disable interface while loading.
        pn.io.loading.start_loading_spinner(self.plot)
        self.data["runoff_data"] = self.binder.get_aggregate_runoff(
            data=self.data["glacier_data"]
        )
        self.figure = self.artist.plot_runoff_dashboard(
            data=self.data,
            subregion_name=self.subregion_name,
            glacier_name="",
        )
        self.plot.object = self.figure
        pn.io.loading.stop_loading_spinner(self.plot)

    @param.depends(
        # "region_name",
        "subregion_name",
        "shapefile_path",
        "upload_shapefile",
        "oggm_params",
        watch=True,
    )
    def get_dashboard_data(self) -> dict:
        """Get data from OGGM."""
        data = self.binder.get_user_subregion(
            region_name=self.region_name,
            subregion_name=self.subregion_name,
            shapefile_path=self.shapefile_path,
            **self.oggm_params,
        )

        return data
