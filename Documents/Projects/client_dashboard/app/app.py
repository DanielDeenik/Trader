"""Sustainability Dashboard — Dash entry point.

Exposes `server = app.server` for WSGI runners (gunicorn, Cloud Run).
No external API integrations: the dashboard renders sample data and
tab placeholders. OpenAI + Airtable wiring was removed 2026-04-23 —
those services were never actually used by the layout callbacks.
"""

import os

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, Input, Output, dcc, html

# --- App init ------------------------------------------------------------

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.LUX],
    title="Sustainability Dashboard",
)
server = app.server  # exposed for gunicorn: `gunicorn app.app:server`

# --- Sample layout data --------------------------------------------------

_sample_metrics = pd.DataFrame(
    {
        "Metric": ["Energy Consumption", "Water Usage", "Waste Generation"],
        "Value": [200, 150, 50],
    }
)

# --- Layout --------------------------------------------------------------

app.layout = html.Div(
    [
        dbc.Container(
            [
                html.H1(
                    "Sustainability Dashboard",
                    style={"textAlign": "center", "color": "#2e8b57"},
                ),
                dcc.Tabs(
                    id="graph-tabs",
                    value="Regulatory",
                    children=[
                        dcc.Tab(label="Regulatory", value="Regulatory",
                                style={"padding": "6px", "fontWeight": "bold"}),
                        dcc.Tab(label="Insights", value="Insights",
                                style={"padding": "6px", "fontWeight": "bold"}),
                        dcc.Tab(label="Project Plan", value="Project Plan",
                                style={"padding": "6px", "fontWeight": "bold"}),
                        dcc.Tab(label="Your Sustainability Story",
                                value="Your Sustainability Story",
                                style={"padding": "6px", "fontWeight": "bold"}),
                    ],
                ),
                html.Div(id="tabs-content"),
            ]
        )
    ]
)

# --- Callbacks -----------------------------------------------------------


@app.callback(
    Output("tabs-content", "children"),
    [Input("graph-tabs", "value")],
)
def update_tab(tab):
    """Render placeholder content for each tab.

    Real visualizations are tracked as a follow-up in
    `docs/superpowers/specs/2026-04-21-client-dashboard-cloud-run-deploy.md`.
    """
    return html.Div(
        [
            html.H4(tab, style={"color": "#2e8b57"}),
            html.P(
                "Visualizations for this tab are not yet implemented. "
                "See the Cloud Run deploy spec for the follow-up plan.",
                style={"fontStyle": "italic", "color": "#555"},
            ),
        ],
        style={"padding": "20px"},
    )


# --- Local dev entrypoint -----------------------------------------------

if __name__ == "__main__":
    # Production runs under gunicorn (see Dockerfile). This path is for
    # local development only.
    port = int(os.getenv("PORT", "8050"))
    app.run_server(host="0.0.0.0", port=port, debug=False)
