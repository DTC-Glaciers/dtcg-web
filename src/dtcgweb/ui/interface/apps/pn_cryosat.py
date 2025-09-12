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

from ...components.cryotempo_selection import CryotempoComparison


def get_cryosat_dashboard():
    """Get UI components for the dashboard.

    Returns
    -------
    pn.template.MaterialTemplate
        Dashboard interface.
    """
    rs = CryotempoComparison()

    # Indicators are also set by the template.
    # indicator_loading = pn.indicators.LoadingSpinner(
    #     value=False, size=20, color="warning"
    # )
    # indicator_bar = pn.indicators.Progress(active=False, width=200)

    # # interface
    # button = pn.widgets.Button(
    #     name="Update", button_type="primary", sizing_mode="stretch_width"
    # )

    """Widgets
    
    Note that some buttons are already declared in RegionSelection.
    """

    # Dropdown
    # load region/subregion names dynamically from data

    groups = {}
    for k,v in rs.metadata["glacier_names"].items():
        groups[k] = [j["Name"] for i,j in v.items()]
        # groups[k] = {j["Name"]:i for i,j in v.items()}
    
    dropdown_glacier = {
        "widget_type": pn.widgets.Select,
        "groups":  groups,
    }

    sidebar = [
        pn.Param(
            rs.param,
            widgets={
                # "region_name": dropdown_region,
                "glacier_name": dropdown_glacier,
            },
        ),
    ]

    dashboard_content = [rs.plot]  # this is the dashboard content
    panel = pn.template.MaterialTemplate(
        site="DTEC Glaciers",
        title="L2 Dashboard Prototype",
        # busy_indicator=indicator_loading,
        sidebar=sidebar,
        main=dashboard_content,
    )  # .servable()
    return panel
