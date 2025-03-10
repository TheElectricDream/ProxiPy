import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import numpy as np
import base64
import io
import json
import os
from dash.exceptions import PreventUpdate

# Initialize the Dash app
app = dash.Dash(__name__, title="NPY Data Viewer")

# App layout
app.layout = html.Div([
    html.H1("NPY Data Viewer", style={'textAlign': 'center'}),
    
    # File upload component
    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select a .npy File')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            multiple=False
        ),
        html.Div(id='upload-status')
    ]),
    
    # Dropdown for selecting data keys
    html.Div([
        html.Label("Select Data to Plot:"),
        dcc.Dropdown(
            id='data-key-dropdown',
            options=[],
            value=None,
            disabled=True
        ),
    ], style={'width': '50%', 'margin': '20px auto'}),
    
    # Plot area
    dcc.Graph(id='time-series-plot'),
    
    # Store the data
    dcc.Store(id='stored-data'),
    
    # Footer
    html.Div([
        html.Hr(),
        html.P("Data Viewer for simulation data stored in .npy files", 
               style={'textAlign': 'center'})
    ])
], style={'maxWidth': '1200px', 'margin': '0 auto', 'padding': '20px'})

# Callback for uploading data
@app.callback(
    [Output('stored-data', 'data'),
     Output('data-key-dropdown', 'options'),
     Output('data-key-dropdown', 'disabled'),
     Output('upload-status', 'children')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def update_data(content, filename):
    if content is None:
        return None, [], True, ""
    
    try:
        # Decode the uploaded file
        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        
        # Check file extension
        if not filename.endswith('.npy'):
            return None, [], True, html.Div(f"Error: File must be a .npy file.", style={'color': 'red'})
        
        # Load the numpy array from the decoded content
        with io.BytesIO(decoded) as f:
            data_dict = np.load(f, allow_pickle=True).item()
        
        # Check if it's a dictionary
        if not isinstance(data_dict, dict):
            return None, [], True, html.Div("Error: Loaded file does not contain a dictionary.", style={'color': 'red'})
        
        # Convert data for JSON serialization (np arrays to lists)
        serializable_data = {}
        for key, value in data_dict.items():
            if isinstance(value, (np.ndarray, list)):
                serializable_data[key] = np.array(value).tolist()
            else:
                serializable_data[key] = value
        
        # Create dropdown options from dictionary keys
        dropdown_options = [{'label': key, 'value': key} for key in data_dict.keys()]
        
        return serializable_data, dropdown_options, False, html.Div(f"File '{filename}' loaded successfully!", style={'color': 'green'})
    
    except Exception as e:
        return None, [], True, html.Div(f"Error loading file: {str(e)}", style={'color': 'red'})

# Callback for updating the plot
@app.callback(
    Output('time-series-plot', 'figure'),
    [Input('data-key-dropdown', 'value')],
    [State('stored-data', 'data')]
)
def update_plot(selected_key, data):
    if data is None or selected_key is None:
        # Return empty figure if no data or key selected
        return go.Figure()
    
    # Get time data if available, otherwise use indices
    if 'time_s' in data:
        x_data = data['time_s']
        x_title = 'Time (s)'
    else:
        x_data = list(range(len(data[selected_key])))
        x_title = 'Index'
    
    # Create the figure
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=x_data,
        y=data[selected_key],
        mode='lines',
        name=selected_key
    ))
    
    # Update layout
    fig.update_layout(
        title=f'{selected_key} vs {x_title}',
        xaxis_title=x_title,
        yaxis_title=selected_key,
        template='plotly_white',
        height=600,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)