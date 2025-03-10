import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go
import numpy as np
import base64
import io
import json
import os
from dash.exceptions import PreventUpdate
import time
import math

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
    
    # Tabs for Plot and Animation
    dcc.Tabs([
        dcc.Tab(label='Time Series Plot', children=[
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
        ]),
        dcc.Tab(label='Spacecraft Animation', children=[
            # Animation controls
            html.Div([
                html.Button('Run Animation', id='run-animation', n_clicks=0,
                           style={'margin': '10px', 'padding': '10px 20px'}),
                html.Button('Stop Animation', id='stop-animation', n_clicks=0,
                           style={'margin': '10px', 'padding': '10px 20px'}),
                html.Div(id='animation-status'),
            ], style={'textAlign': 'center', 'margin': '20px'}),
            
            # Animation display
            dcc.Graph(id='animation-plot', style={'height': '600px'}),
            
            # Animation interval
            dcc.Interval(
                id='animation-interval',
                interval=100,  # ms
                n_intervals=0,
                disabled=True
            ),
            
            # Frame slider
            html.Div([
                html.Label("Frame:"),
                dcc.Slider(
                    id='frame-slider',
                    min=0,
                    max=100,
                    step=1,
                    value=0,
                    marks=None,
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
            ], style={'width': '80%', 'margin': '20px auto'}),
        ]),
    ]),
    
    # Store the data
    dcc.Store(id='stored-data'),
    dcc.Store(id='animation-state', data={'is_running': False, 'current_frame': 0}),
    
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
     Output('upload-status', 'children'),
     Output('frame-slider', 'max'),
     Output('frame-slider', 'marks')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def update_data(content, filename):
    if content is None:
        return None, [], True, "", 100, None
    
    try:
        # Decode the uploaded file
        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        
        # Check file extension
        if not filename.endswith('.npy'):
            return None, [], True, html.Div(f"Error: File must be a .npy file.", style={'color': 'red'}), 100, None
        
        # Load the numpy array from the decoded content
        with io.BytesIO(decoded) as f:
            data_dict = np.load(f, allow_pickle=True).item()
        
        # Check if it's a dictionary
        if not isinstance(data_dict, dict):
            return None, [], True, html.Div("Error: Loaded file does not contain a dictionary.", style={'color': 'red'}), 100, None
        
        # Convert data for JSON serialization (np arrays to lists)
        serializable_data = {}
        for key, value in data_dict.items():
            if isinstance(value, (np.ndarray, list)):
                serializable_data[key] = np.array(value).tolist()
            else:
                serializable_data[key] = value
        
        # Create dropdown options from dictionary keys
        dropdown_options = [{'label': key, 'value': key} for key in data_dict.keys()]
        
        # Get the length of position data for the slider
        data_length = 100  # Default value
        if 'Chaser Px (m)' in serializable_data:
            data_length = len(serializable_data['Chaser Px (m)']) - 1
        
        # Create marks for the slider at regular intervals
        slider_marks = {}
        if data_length > 0:
            step_size = max(1, data_length // 10)
            for i in range(0, data_length + 1, step_size):
                slider_marks[i] = {'label': str(i)}
        
        return serializable_data, dropdown_options, False, html.Div(f"File '{filename}' loaded successfully!", style={'color': 'green'}), data_length, slider_marks
    
    except Exception as e:
        return None, [], True, html.Div(f"Error loading file: {str(e)}", style={'color': 'red'}), 100, None

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

# Callback for animation controls
@app.callback(
    [Output('animation-interval', 'disabled'),
     Output('animation-state', 'data')],
    [Input('run-animation', 'n_clicks'),
     Input('stop-animation', 'n_clicks'),
     Input('frame-slider', 'value')],
    [State('animation-state', 'data')]
)
def control_animation(run_clicks, stop_clicks, slider_value, animation_state):
    ctx = callback_context
    if not ctx.triggered:
        return True, animation_state
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'run-animation' and run_clicks > 0:
        animation_state['is_running'] = True
        return False, animation_state
    elif trigger_id == 'stop-animation' and stop_clicks > 0:
        animation_state['is_running'] = False
        return True, animation_state
    elif trigger_id == 'frame-slider':
        animation_state['current_frame'] = slider_value
        return animation_state['is_running'] is False, animation_state
    
    return True, animation_state

# Callback for updating the animation frame
@app.callback(
    [Output('animation-plot', 'figure'),
     Output('frame-slider', 'value'),
     Output('animation-status', 'children')],
    [Input('animation-interval', 'n_intervals'),
     Input('frame-slider', 'value'),
     Input('stored-data', 'data')],
    [State('animation-state', 'data'),
     State('animation-interval', 'disabled')]
)
def update_animation(n_intervals, slider_value, data, animation_state, interval_disabled):
    if data is None:
        return create_empty_animation(), 0, ""
    
    # Check if we have the necessary position data
    required_keys = ['Chaser Px (m)', 'Chaser Py (m)', 'Chaser Rz (rad)']
    if not all(key in data for key in required_keys):
        return create_empty_animation(), 0, html.Div("Missing position data for animation.", style={'color': 'red'})
    
    # Determine the current frame
    current_frame = slider_value
    if not interval_disabled and animation_state['is_running']:
        data_length = len(data['Chaser Px (m)']) - 1
        current_frame = (current_frame + 1) % (data_length + 1)
    
    # Get position data for current frame
    px = data['Chaser Px (m)'][current_frame]
    py = data['Chaser Py (m)'][current_frame]
    rz = data['Chaser Rz (rad)'][current_frame]
    
    # Create the animation figure with spacecraft
    fig = create_animation_figure(px, py, rz)
    
    # Status message
    status = html.Div(f"Frame: {current_frame}, Position: ({px:.2f}, {py:.2f}), Rotation: {rz:.2f} rad", 
                     style={'color': 'blue'})
    
    return fig, current_frame, status

def create_empty_animation():
    # Create empty animation figure with table
    fig = go.Figure()
    
    # Set fixed figure size and range
    fig.update_layout(
        title='Spacecraft Animation',
        xaxis=dict(range=[-1.5, 1.5], title='X Position (m)'),
        yaxis=dict(range=[-2.5, 2.5], title='Y Position (m)'),
        template='plotly_white',
        height=600,
        margin=dict(l=50, r=50, t=80, b=50),
        # Make sure x and y axis are at the same scale
        yaxis_scaleanchor="x",
        yaxis_scaleratio=1,
    )
    
    # Add table (gray rectangle in background)
    fig.add_shape(
        type="rect",
        x0=-1.2, y0=-2.2,
        x1=1.2, y1=2.2,
        fillcolor="gray",
        opacity=0.3,
        line=dict(width=1, color="gray"),
    )
    
    return fig

def create_animation_figure(px, py, rz):
    # Create figure with table
    fig = create_empty_animation()
    
    # Define spacecraft size
    spacecraft_size = 0.3
    
    # Calculate spacecraft corners based on position and rotation
    corners = get_rotated_spacecraft_corners(px, py, rz, spacecraft_size)
    
    # Add spacecraft as a filled polygon
    fig.add_trace(go.Scatter(
        x=[corners[0][0], corners[1][0], corners[2][0], corners[3][0], corners[0][0]],
        y=[corners[0][1], corners[1][1], corners[2][1], corners[3][1], corners[0][1]],
        fill="toself",
        fillcolor="blue",
        line=dict(color="darkblue", width=2),
        name="Spacecraft"
    ))
    
    # Add a marker for the center/origin of the spacecraft
    fig.add_trace(go.Scatter(
        x=[px],
        y=[py],
        mode="markers",
        marker=dict(color="red", size=8),
        name="Center"
    ))
    
    # Add a line showing the forward direction
    forward_x = px + 0.2 * math.cos(rz)
    forward_y = py + 0.2 * math.sin(rz)
    fig.add_trace(go.Scatter(
        x=[px, forward_x],
        y=[py, forward_y],
        mode="lines",
        line=dict(color="red", width=2),
        name="Direction"
    ))
    
    return fig

def get_rotated_spacecraft_corners(px, py, rz, size):
    """Calculate the corners of the spacecraft after rotation"""
    half_size = size / 2
    
    # Corners before rotation (centered at origin)
    corners = [
        [-half_size, -half_size],  # Bottom left
        [half_size, -half_size],   # Bottom right
        [half_size, half_size],    # Top right
        [-half_size, half_size]    # Top left
    ]
    
    # Apply rotation and translation
    rotated_corners = []
    for x, y in corners:
        # Rotate
        x_rot = x * math.cos(rz) - y * math.sin(rz)
        y_rot = x * math.sin(rz) + y * math.cos(rz)
        
        # Translate
        x_final = x_rot + px
        y_final = y_rot + py
        
        rotated_corners.append([x_final, y_final])
    
    return rotated_corners

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)