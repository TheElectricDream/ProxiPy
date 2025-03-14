import os
import sys
import threading
import subprocess
import numpy as np
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc
from flask import send_file
import io
import matplotlib.pyplot as plt

# Add the project path so that lib files can be read
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Initialize the Dash application with Bootstrap styling
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.DARKLY],
    # Add custom CSS for dropdowns
    external_scripts=[
        {"src": "https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"}
    ]
)

# Add custom CSS for dropdowns and default plot theme
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* Fix dropdown text color */
            .Select-value-label, .Select-menu-outer {
                color: black !important;
            }
            /* Fix dropdown menu background */
            .VirtualizedSelectOption {
                background-color: white !important;
            }
            /* Fix dropdown arrow color */
            .Select-arrow {
                border-color: #ccc transparent transparent !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

server = app.server

# Global variables to store state
loaded_data = {}
simulation_running = False

# =============================================================================
# Helper Functions
# =============================================================================

def run_simulation():
    global simulation_running
    simulation_running = True
    
    try:
        # Run main.py located in the "main" directory
        process = subprocess.Popen(
            ["python", "main.py"],
            cwd=os.path.join(os.getcwd(), "main")
        )
        process.wait()
    except Exception as e:
        print("Error running simulation:", e)
    
    simulation_running = False
    return "Simulation completed"

# Create a default dark-themed empty plot
def create_empty_plot():
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor='#333333',
        paper_bgcolor='#333333',
        xaxis=dict(
            showgrid=True,
            gridcolor='rgba(255, 255, 255, 0.2)'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(255, 255, 255, 0.2)'
        ),
        margin=dict(l=40, r=40, t=40, b=40),
        height=550
    )
    # Add a text annotation to the empty plot
    fig.add_annotation(
        text="No data loaded",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(color="white", size=16)
    )
    return fig

# =============================================================================
# Application Layout
# =============================================================================

# Create the tabs
tabs = dbc.Tabs([
    # Initialize Parameters Tab
    dbc.Tab([
        html.Div([
            html.H3("Initialize Parameters"),
            html.P("Parameter initialization options will appear here.")
        ], className="p-4")
    ], label="Initialize Parameters"),
    
    # Setup & Run Simulations Tab
    dbc.Tab([
        html.Div([
            html.H3("Setup & Run Simulations"),
            dbc.Button("Run Simulation", id="run-sim-button", color="primary", className="mb-3"),
            html.Div(id="simulation-status"),
            dbc.Progress(id="simulation-progress", value=0, striped=True, animated=True, 
                         style={"display": "none"})
        ], className="p-4")
    ], label="Setup & Run Simulations"),
    
    # Setup & Run Experiments Tab
    dbc.Tab([
        html.Div([
            html.H3("Setup & Run Experiments"),
            html.P("Experiment options coming soon.")
        ], className="p-4")
    ], label="Setup & Run Experiments"),
    
    # Hardware Control Tab
    dbc.Tab([
        html.Div([
            html.H3("Hardware Control"),
            html.P("Hardware control options coming soon.")
        ], className="p-4")
    ], label="Hardware Control"),
    
    # Data Inspector Tab
    dbc.Tab([
        html.Div([
            html.H3("Data Inspector"),
            dbc.Row([
                dbc.Col([
                    dbc.Button("Load NPY Data", id="load-data-button", color="primary", className="me-2"),
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px 0'
                        },
                        multiple=False
                    ),
                    html.Div(id="upload-status")
                ], width=12),
            ]),
            dbc.Row([
                dbc.Col([
                    html.Label("X:", style={"color": "white"}),
                    dcc.Dropdown(
                        id="x-dropdown", 
                        options=[], 
                        value=None,
                        style={"color": "black"}
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Y:", style={"color": "white"}),
                    dcc.Dropdown(
                        id="y-dropdown", 
                        options=[], 
                        value=None,
                        style={"color": "black"}
                    )
                ], width=3),
                dbc.Col([
                    dbc.Button("Export to PDF", id="export-pdf-button", color="secondary", 
                               className="mt-4", disabled=True)
                ], width=3),
                dbc.Col([
                    html.Div(id="export-status")
                ], width=3)
            ], className="mb-4"),
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id="data-plot", style={"height": "60vh"}, figure=create_empty_plot())
                ])
            ])
        ], className="p-4")
    ], label="Data Inspector"),
], id="tabs")

# Main layout
app.layout = dbc.Container([
    html.H1("ProxiPy Web Interface", className="my-4 text-center"),
    tabs,
    dcc.Store(id="store-data-keys"),
    dcc.Interval(id="sim-progress-interval", interval=500, disabled=True),
    dcc.Download(id="download-pdf")
], fluid=True)

# =============================================================================
# Callbacks
# =============================================================================

# Simulation tab callbacks
@app.callback(
    [Output("simulation-status", "children"),
     Output("simulation-progress", "style"),
     Output("run-sim-button", "disabled"),
     Output("sim-progress-interval", "disabled")],
    [Input("run-sim-button", "n_clicks"),
     Input("sim-progress-interval", "n_intervals")],
    prevent_initial_call=True
)
def handle_simulation(n_clicks, n_intervals):
    triggered_id = ctx.triggered_id
    
    if triggered_id == "run-sim-button" and n_clicks:
        # Start simulation in a separate thread
        threading.Thread(target=run_simulation, daemon=True).start()
        return "Simulation running...", {"display": "block"}, True, False
    
    if triggered_id == "sim-progress-interval":
        if simulation_running:
            return "Simulation running...", {"display": "block"}, True, False
        else:
            return "Simulation completed!", {"display": "none"}, False, True
    
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Data inspector tab callbacks
@app.callback(
    [Output("upload-status", "children"),
     Output("x-dropdown", "options"),
     Output("y-dropdown", "options"),
     Output("store-data-keys", "data")],
    [Input("upload-data", "contents")],
    [State("upload-data", "filename")]
)
def update_data_options(contents, filename):
    global loaded_data
    
    if contents is None:
        return "No file loaded", [], [], None
    
    if not filename.endswith('.npy'):
        return "Please upload a .npy file", [], [], None
    
    # Process the uploaded content
    try:
        # Decode the content
        content_type, content_string = contents.split(',')
        import base64
        import tempfile
        
        # Create a temporary file to save the decoded content
        with tempfile.NamedTemporaryFile(delete=False, suffix='.npy') as temp_file:
            temp_file.write(base64.b64decode(content_string))
            temp_path = temp_file.name
        
        # Load the data from the temporary file
        loaded_data = np.load(temp_path, allow_pickle=True).item()
        os.unlink(temp_path)  # Delete the temporary file
        
        if isinstance(loaded_data, dict):
            keys = list(loaded_data.keys())
            options = [{"label": key, "value": key} for key in keys]
            return f"Loaded: {filename}", options, options, keys
        else:
            return "Error: File is not a dictionary", [], [], None
    except Exception as e:
        return f"Error: {str(e)}", [], [], None

@app.callback(
    [Output("data-plot", "figure"),
     Output("export-pdf-button", "disabled")],
    [Input("x-dropdown", "value"),
     Input("y-dropdown", "value")],
    [State("store-data-keys", "data")]
)
def update_plot(x_key, y_key, keys):
    global loaded_data
    
    if not x_key or not y_key or not loaded_data:
        return create_empty_plot(), True
    
    x_data = loaded_data[x_key]
    y_data = loaded_data[y_key]
    
    fig = go.Figure()
    
    if isinstance(y_data, np.ndarray):
        if y_data.ndim == 1:
            if isinstance(x_data, np.ndarray) and x_data.ndim == 1 and len(x_data) == len(y_data):
                fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='lines', line=dict(color='#5599ff', width=2)))
            else:
                fig.add_trace(go.Scatter(y=y_data, mode='lines', line=dict(color='#5599ff', width=2)))
            
            fig.update_layout(
                title=f"{y_key} vs {x_key}",
                xaxis_title=x_key,
                yaxis_title=y_key,
                template="plotly_dark",
                plot_bgcolor='#333333',
                paper_bgcolor='#333333',
                xaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(255, 255, 255, 0.2)'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(255, 255, 255, 0.2)'
                )
            )
        elif y_data.ndim == 2:
            fig.add_trace(go.Heatmap(z=y_data, colorscale='Plasma'))
            
            fig.update_layout(
                title=y_key,
                xaxis_title='X Dimension',
                yaxis_title='Y Dimension',
                template="plotly_dark",
                plot_bgcolor='#333333',
                paper_bgcolor='#333333'
            )
        else:
            fig = create_empty_plot()
            fig.add_annotation(
                text=f"Cannot display {y_data.ndim}D array",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(color="white", size=14)
            )
    else:
        fig = create_empty_plot()
        fig.add_annotation(
            text=f"Data type: {type(y_data)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(color="white", size=14)
        )
    
    return fig, False

@app.callback(
    Output("download-pdf", "data"),
    Input("export-pdf-button", "n_clicks"),
    [State("x-dropdown", "value"), State("y-dropdown", "value")],
    prevent_initial_call=True
)
def export_plot_to_pdf(n_clicks, x_key, y_key):
    if n_clicks is None or not x_key or not y_key:
        return dash.no_update
    
    # Create a matplotlib figure for PDF export
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_facecolor('#333333')
    fig.patch.set_facecolor('#333333')
    
    x_data = loaded_data[x_key]
    y_data = loaded_data[y_key]
    
    if isinstance(y_data, np.ndarray):
        if y_data.ndim == 1:
            if isinstance(x_data, np.ndarray) and x_data.ndim == 1 and len(x_data) == len(y_data):
                ax.plot(x_data, y_data, '-', color='#5599ff', linewidth=1.5)
            else:
                ax.plot(y_data, '-', color='#5599ff', linewidth=1.5)
            ax.set_title(f"{y_key} vs {x_key}", color='white', fontsize=16)
            ax.set_xlabel(x_key, color='white', fontsize=14)
            ax.set_ylabel(y_key, color='white', fontsize=14)
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.tick_params(colors='white', labelsize=14)
        elif y_data.ndim == 2:
            img = ax.imshow(y_data, cmap='plasma', aspect='auto')
            ax.set_title(y_key, color='white', fontsize=16)
            ax.set_xlabel('X Dimension', color='white', fontsize=14)
            ax.set_ylabel('Y Dimension', color='white', fontsize=14)
            ax.tick_params(colors='white', labelsize=14)
            fig.colorbar(img, ax=ax)
    
    # Save figure to a BytesIO object
    buf = io.BytesIO()
    fig.savefig(buf, format='pdf', bbox_inches='tight')
    buf.seek(0)
    
    # Close the figure to free memory
    plt.close(fig)
    
    # Return the PDF as a download
    return dcc.send_bytes(buf.getvalue(), f"{y_key}_vs_{x_key}.pdf")

# =============================================================================
# Run the Application
# =============================================================================

if __name__ == "__main__":
    app.run_server(debug=True, host='0.0.0.0')