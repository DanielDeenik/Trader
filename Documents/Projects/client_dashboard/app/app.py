import os
import sys
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import openai
import plotly.express as px
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
# from src.const import get_constants
# from src.dash1 import generate_visualizations as generate_visualizations1
# from src.dash2 import generate_visualizations as generate_visualizations2
# from src.dash3 import generate_visualizations as generate_visualizations3
# from src.dash4 import generate_visualizations as generate_visualizations4

# Function to validate project structure and environment setup
# def validate_project():
#     required_files = [
#         'src/const.py',
#         'src/dash1.py',
#         'src/dash2.py',
#         'src/dash3.py',
#         'src/dash4.py'
# #     ]
    
#     required_dirs = ['assets','components']
    
#     missing_files = [file for file in required_files if not os.path.isfile(file)]
#     missing_dirs = [dir for dir in required_dirs if not os.path.isdir(dir)]

#     # Print missing files and directories
#     if missing_files or missing_dirs:
#         print("\nMissing files:")
#         for file in missing_files:
#             print(f" - {file}")
        
#         print("\nMissing directories:")
#         for dir in missing_dirs:
#             print(f" - {dir}")
        
#         sys.exit("Project validation failed. Please ensure all files and directories are present.")

    # Check for essential environment variables
    # if 'OPENAI_API_KEY' not in os.environ:
    #     sys.exit("Environment variable OPENAI_API_KEY is not set. Please configure it before running the app.")
    
    # print("\nProject validation successful.")

# Run validation before starting the app
# validate_project()

# Define function to load data based on tab selection
def load_data(tab):
    # Placeholder function since CSV/XLSX files were removed
    return pd.DataFrame(), {}

# num_of_works, num_of_countries, num_of_lang, avg_votes = get_constants(pd.DataFrame(), pd.DataFrame(), {}, {})

# Initialize the Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.LUX], title='Sustainability Dashboard')
server = app.server

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Sample data for visualization
data = {
    'Metric': ['Energy Consumption', 'Water Usage', 'Waste Generation'],
    'Value': [200, 150, 50]
}
df = pd.DataFrame(data)

# Layout of the Dash app
app.layout = html.Div([
    dbc.Container([
        html.H1("Sustainability Dashboard", style={'textAlign': 'center', 'color': '#2e8b57'}),
        dcc.Tabs(id='graph-tabs', value='Regulatory', children=[
            dcc.Tab(label='Regulatory', value='Regulatory', style={'padding': '6px', 'fontWeight': 'bold'}),
            dcc.Tab(label='Insights', value='Insights', style={'padding': '6px', 'fontWeight': 'bold'}),
            dcc.Tab(label='Project Plan', value='Project Plan', style={'padding': '6px', 'fontWeight': 'bold'}),
            dcc.Tab(label='Your Sustainability Story', value='Your Sustainability Story', style={'padding': '6px', 'fontWeight': 'bold'})
        ]),
        html.Div(id='tabs-content'),
        html.H3("AI-Powered Sustainability Assistant", style={'color': '#2e8b57'}),
        dcc.Textarea(
            id='user-input',
            placeholder='Ask me about your sustainability data...',
            style={'width': '100%', 'height': 100, 'marginBottom': '10px'}
        ),
        html.Button('Send', id='send-button', n_clicks=0, style={'backgroundColor': '#2e8b57', 'color': 'white'}),
        html.Div(id='bot-response', style={'margin-top': '20px', 'color': '#2e8b57'})
    ])
])

# Callback to handle user input and get response from OpenAI
@app.callback(
    Output('bot-response', 'children'),
    [Input('send-button', 'n_clicks')],
    [State('user-input', 'value')]
)
def update_output(n_clicks, user_input):
    if n_clicks > 0 and user_input:
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": user_input}
            ]
        )
        bot_response = response['choices'][0]['message']['content']
        return f"Bot: {bot_response}"
    return "Bot: How can I assist you today?"

# Callback to update visualizations based on tab selection
@app.callback(
    Output('tabs-content', 'children'),
    [Input('graph-tabs', 'value')]
)
def update_tab(tab):
    data, splits = load_data('movie')  # Replace with dynamic selection if needed

    if tab == 'overview':
        fig1, fig2, fig3, fig4 = generate_visualizations1(data, splits)
        return html.Div([
            html.Div([dcc.Graph(figure=fig1)], style={'width': '50%', 'display': 'inline-block'}),
            html.Div([dcc.Graph(figure=fig2)], style={'width': '50%', 'display': 'inline-block'}),
            html.Div([dcc.Graph(figure=fig3)], style={'width': '50%', 'display': 'inline-block'}),
            html.Div([dcc.Graph(figure=fig4)], style={'width': '50%', 'display': 'inline-block'})
        ])
    elif tab == 'content_creators':
        fig1, fig2, fig3, fig4 = generate_visualizations2(data, splits)
        return html.Div([
            html.Div([dcc.Graph(figure=fig1)], style={'width': '50%', 'display': 'inline-block'}),
            html.Div([dcc.Graph(figure=fig2)], style={'width': '50%', 'display': 'inline-block'}),
            html.Div([dcc.Graph(figure=fig3)], style={'width': '50%', 'display': 'inline-block'}),
            html.Div([dcc.Graph(figure=fig4)], style={'width': '50%', 'display': 'inline-block'})
        ])
    elif tab == 'parental':
        fig1, fig2 = generate_visualizations3(data, splits)
        return html.Div([
            html.Div([dcc.Graph(figure=fig1)], style={'width': '50%', 'display': 'inline-block'}),
            html.Div([dcc.Graph(figure=fig2)], style={'width': '50%', 'display': 'inline-block'})
        ])
    elif tab == 'year':
        fig1, fig2 = generate_visualizations4(data, splits)
        return html.Div([
            html.Div([dcc.Graph(figure=fig1)], style={'width': '50%', 'display': 'inline-block'}),
            html.Div([dcc.Graph(figure=fig2)], style={'width': '50%', 'display': 'inline-block'})
        ])

if __name__ == '__main__':
    app.run_server(debug=True)
