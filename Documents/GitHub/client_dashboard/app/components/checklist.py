from dash import dcc

def create_checklist(options):
    return dcc.Checklist(
        options=[{'label': opt, 'value': opt} for opt in options],
        value=[],
        id='data-checklist'
    )
