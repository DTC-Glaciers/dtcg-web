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

User interface displaying L2 dashboard for specific glaciers.
"""

import panel as pn

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

    groups = {}
    for k, v in rs.metadata["glacier_names"].items():
        groups[k] = sorted([j["Name"] for i, j in v.items()])
        # groups[k] = {j["Name"]:i for i,j in v.items()}

    dropdown_glacier = {
        "widget_type": pn.widgets.Select,
        "groups": groups,
    }

    sidebar = [
        pn.Param(
            rs.param,
            name="",
            widgets={
                "glacier_name": dropdown_glacier,
            },
        ),
    ]

    dashboard_content = [rs.plot]  # this is the dashboard content
    panel = pn.template.MaterialTemplate(
        title="L2 Dashboard Prototype",
        # busy_indicator=indicator_loading,
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

    # Dropdown
    # load region/subregion names dynamically from data

    groups = {}
    for k, v in rs.metadata["glacier_names"].items():
        groups[k] = sorted([j["Name"] for i, j in v.items()])
        # groups[k] = {j["Name"]:i for i,j in v.items()}

    dropdown_glacier = {
        "widget_type": pn.widgets.Select,
        "groups": groups,
    }

    sidebar = [
        pn.Param(
            rs.param,
            name="",
            widgets={
                "glacier_name": dropdown_glacier,
            },
        ),
        rs.map,
    ]

    dashboard_content = pn.Column(
        rs.plot_title,
        pn.Tabs(
            ("L1 (OGGM)", rs.plot_l1),
            ("L2 (Cryosat)", rs.plot_l2),
            styles={
                "flex": "0 0 auto",
                "align-items": "stretch",
                "align-content": "stretch",
                "flex-wrap": "nowrap",
            },
            # sizing_mode="scale_both"
        ),
        styles={
            "flex": "1 1 auto",
            "align-items": "stretch",
            "align-content": "stretch",
            "flex-wrap": "nowrap",
        },
        # sizing_mode="scale_both"
    )
    panel = pn.template.MaterialTemplate(
        title="L2 Dashboard Prototype",
        # busy_indicator=indicator_loading,
        sidebar=sidebar,
        logo="./static/img/dtc_logo_inv_min.png",
        main=dashboard_content,
        sidebar_width=250,
    )

    return panel
