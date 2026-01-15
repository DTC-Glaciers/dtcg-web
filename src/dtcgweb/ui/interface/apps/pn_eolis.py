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

User interface displaying dashboard data for specific glaciers.
"""

import panel as pn

pn.extension(sizing_mode="stretch_width", defer_load=True, loading_indicator=True)

from ...components.cryotempo_selection import CryotempoSelection


def get_eolis_dashboard():
    """Get UI components for the dashboard.

    Returns
    -------
    pn.template.MaterialTemplate
        Dashboard interface.
    """
    rs = CryotempoSelection()

    """Widgets
    
    Note that some buttons are already declared in RegionSelection.
    """

    # Dropdown
    # load region/subregion names dynamically from data

    dropdown_glacier = {
        "widget_type": pn.widgets.Select,
        "groups": rs.metadata["hash"],
    }
    dropdown_region = {
        "widget_type": pn.widgets.Select,
        "objects": ["Central Europe", "Iceland"],
    }

    sidebar = [
        pn.Param(
            rs.param,
            name="",
            widgets={
                "glacier_name": dropdown_glacier,
                "region_name": dropdown_region,
            },
        ),
    ]

    dashboard_content = [rs.plot]  # this is the dashboard content
    panel = pn.template.MaterialTemplate(
        title="L2 Dashboard Prototype",
        sidebar=sidebar,
        logo="./static/img/dtc_logo_inv_min.png",
        main=dashboard_content,
        sidebar_width=250,
    )
    return panel


def get_eolis_dashboard_with_selection():
    """Get UI components for the dashboard.

    Returns
    -------
    pn.template.MaterialTemplate
        Dashboard interface.
    """
    rs = CryotempoSelection()

    """Widgets
    
    Note that some buttons are already declared in RegionSelection.
    """

    dropdown_glacier = {
        "widget_type": pn.widgets.Select,
        "options": rs.param._glacier_names,
    }

    sidebar = [
        pn.Param(
            rs.param,
            name="First select a region:",
            widgets={
                "glacier_name": dropdown_glacier,
            },
        ),
        rs.map,
        rs.details,
        rs.download_button,
    ]

    dashboard_content = pn.Column(
        rs.plot_title,
        pn.Tabs(
            ("Model (OGGM)", rs.plot_oggm),
            ("EO (Cryosat)", rs.plot_cryosat),
            styles={
                "flex": "0 0 auto",
                "align-items": "stretch",
                "align-content": "stretch",
                "flex-wrap": "nowrap",
            },
            sizing_mode="stretch_width",
        ),
        styles={
            "flex": "1 1 auto",
            "align-items": "stretch",
            "align-content": "stretch",
            "flex-wrap": "nowrap",
        },
        sizing_mode="stretch_width",
    )

    panel = pn.template.MaterialTemplate(
        title="Alpine and Icelandic Glacier Dashboard",
        busy_indicator=pn.indicators.LoadingSpinner(size=40),
        sidebar=sidebar,
        logo="./static/img/dtc_logo_inv_min.png",
        main=dashboard_content,
        sidebar_width=250,
    )

    return panel
