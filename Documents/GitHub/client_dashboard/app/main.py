from services.openai_service import OpenAIService
from app.services.airtable_service import AirtableService
from app.components.checklist import create_checklist
from app.components.data_processing import DataProcessor
from dash import Dash, dcc, html, Input, Output, State

# Initialize services
config = load_api_keys('config/config.yaml')
openai_service = OpenAIService(api_key=config['OPENAI_API_KEY'])
airtable_service = AirtableService(
    base_id=config['AIRTABLE_BASE_ID'],
    api_key=config['AIRTABLE_API_KEY'],
    table_name='sustainability_requirements'
)

# Create the Dash app
app = Dash(__name__)
server = app.server

# Define layout
app.layout = html.Div([
    html.H1("Client Dashboard"),
    create_checklist(['Option 1', 'Option 2', 'Option 3']),
    html.Div(id='output-div')
])

# Define callbacks
@app.callback(
    Output('output-div', 'children'),
    [Input('data-checklist', 'value')]
)
def update_output(selected_values):
    return f"Selected values: {', '.join(selected_values)}"

if __name__ == '__main__':
    app.run_server(debug=True)
from app.services.airtable_service import AirtableService
from app.components.checklist import create_checklist
from app.components.data_processing import DataProcessor
from dash import Dash, dcc, html, Input, Output, State

# Initialize services
config = load_api_keys('config/config.yaml')
openai_service = OpenAIService(api_key=config['OPENAI_API_KEY'])
airtable_service = AirtableService(
    base_id=config['AIRTABLE_BASE_ID'],
    api_key=config['AIRTABLE_API_KEY'],
    table_name='sustainability_requirements'
)

# Create the Dash app
app = Dash(__name__)
server = app.server

# Define layout
app.layout = html.Div([
    html.H1("Client Dashboard"),
    create_checklist(['Option 1', 'Option 2', 'Option 3']),
    html.Div(id='output-div')
])

# Define callbacks
@app.callback(
    Output('output-div', 'children'),
    [Input('data-checklist', 'value')]
)
def update_output(selected_values):
    return f"Selected values: {', '.join(selected_values)}"

if __name__ == '__main__':
    app.run_server(debug=True)
