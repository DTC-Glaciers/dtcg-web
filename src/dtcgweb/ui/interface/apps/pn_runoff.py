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

User interface displaying runoff for specific glaciers.
"""

import panel as pn

from ...components.region_selection import RegionSelection


def get_runoff_dashboard():
    """Get UI components for the dashboard.

    Returns
    -------
    pn.template.MaterialTemplate
        Dashboard interface.
    """
    rs = RegionSelection()

    # Indicators are also set by the template.
    indicator_loading = pn.indicators.LoadingSpinner(
        value=False, size=20, color="warning"
    )
    indicator_bar = pn.indicators.Progress(active=False, width=200)

    # # interface
    # button = pn.widgets.Button(
    #     name="Update", button_type="primary", sizing_mode="stretch_width"
    # )

    """Widgets
    
    Note that some buttons are already declared in RegionSelection.
    """

    # Dropdown
    # load region/subregion names dynamically from data
    dropdown_region = {
        "widget_type": pn.widgets.Select,
        "options": {label: label for label in rs.metadata["region_names"]},
    }
    dropdown_subregion = {
        # "widget_type": pn.widgets.Select.from_values(rs.data["metadata"]["name"].tolist()),
        "widget_type": pn.widgets.Select,
        "options": {
            label: variable
            for label, variable in zip(rs.metadata["name"], rs.metadata["id"])
        },
    }
    dropdown_glacier = {
        "widget_type": pn.widgets.Select,
        "options": [name for name in rs.data["glacier_data"]["Name"].dropna().tolist()],
    }

    # Buttons
    button_runoff = {
        "widget_type": pn.widgets.Button,
        "button_type": "default",
        "align": "center",
        "name": "Get Runoff",
        "value": False,
    }
    button_upload = {  # TODO: input sanitisation
        "widget_type": pn.widgets.FileInput,
        "accept": ".shx,.shp",
        "name": "Upload Shapefile",
    }
    button_datacube_l1 = {
        "widget_type": pn.widgets.Button,
        "button_type": "default",
        "align": "center",
        "name": "Get L1 Datacube",
        "value": False,
        "disabled": True,
    }
    button_datacube_l2 = {
        "widget_type": pn.widgets.Button,
        "button_type": "default",
        "align": "center",
        "name": "Get L2 Datacube",
        "value": False,
        "disabled": True,
    }

    sidebar = [
        pn.Param(
            rs.param,
            name="Select Glacier",
            widgets={
                # "get_runoff": button_runoff,
                "region_name": dropdown_region,
                "subregion_name": dropdown_subregion,
                "glacier_name": dropdown_glacier,
                "upload_shapefile": button_upload,
                "get_datacube_l1_button": button_datacube_l1,
                "get_datacube_l2_button": button_datacube_l2,
            },
        ),
    ]

    dashboard_content = [rs.plot]  # this is the dashboard content
    panel = pn.template.MaterialTemplate(
        site="DTEC Glaciers",
        title="Runoff Dashboard",
        busy_indicator=indicator_loading,
        sidebar=sidebar,
        sidebar_width=300,
        # collapsed_sidebar=True,
        main=dashboard_content,
        # header_background="#6bcafa",
    ).servable()
    return panel
