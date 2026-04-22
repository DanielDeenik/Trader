"""Sustainability Dashboard — Dash entry point.

Exposes `server = app.server` for WSGI runners (gunicorn, Cloud Run).
Secrets are read from environment variables; there is no YAML config
loading at runtime.
"""

import os

import dash_bootstrap_components as dbc
import openai
import pandas as pd
from dash import Dash, Input, Output, State, dcc, html

# --- App init ------------------------------------------------------------

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.LUX],
    title="Sustainability Dashboard",
)
server = app.server  # exposed for gunicorn: `gunicorn app.app:server`

# OpenAI key read at module load — absence is tolerated so the container
# can boot and serve the layout even when the secret isn't wired up yet
# (callbacks will surface the error to the user instead).
openai.api_key = os.getenv("OPENAI_API_KEY", "")

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
                html.H3(
                    "AI-Powered Sustainability Assistant",
                    style={"color": "#2e8b57"},
                ),
                dcc.Textarea(
                    id="user-input",
                    placeholder="Ask me about your sustainability data...",
                    style={"width": "100%", "height": 100, "marginBottom": "10px"},
                ),
                html.Button(
                    "Send",
                    id="send-button",
                    n_clicks=0,
                    style={"backgroundColor": "#2e8b57", "color": "white"},
                ),
                html.Div(
                    id="bot-response",
                    style={"margin-top": "20px", "color": "#2e8b57"},
                ),
            ]
        )
    ]
)

# --- Callbacks -----------------------------------------------------------


@app.callback(
    Output("bot-response", "children"),
    [Input("send-button", "n_clicks")],
    [State("user-input", "value")],
)
def update_output(n_clicks, user_input):
    """Send user input to OpenAI and return the reply.

    Uses the legacy openai<1.0 client surface (`openai.ChatCompletion`).
    Migration to the v1 client is tracked as a deferred follow-up —
    see `docs/superpowers/specs/2026-04-21-client-dashboard-cloud-run-deploy.md`.
    """
    if not n_clicks or not user_input:
        return "Bot: How can I assist you today?"

    if not openai.api_key:
        return "Bot: OPENAI_API_KEY is not configured on the server."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_input}],
        )
        return f"Bot: {response['choices'][0]['message']['content']}"
    except Exception as exc:  # noqa: BLE001 — user-facing callback
        return f"Bot: sorry, the assistant failed ({type(exc).__name__})."


@app.callback(
    Output("tabs-content", "children"),
    [Input("graph-tabs", "value")],
)
def update_tab(tab):
    """Render placeholder content for each tab.

    The original implementation called `generate_visualizations{1..4}`
    from a `src/` package that was never implemented (all stubs were
    empty files, now deleted). This placeholder keeps the layout
    functional for a Cloud Run smoke test until the real visualizations
    are wired up in a follow-up spec.
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
