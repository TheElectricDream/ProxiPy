import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import tkinter as tk
from tkinter import filedialog

class SpacecraftAnimator:
    """
    Animate spacecraft positions from logged data stored in a dictionary of arrays.
    
    The NPY file is expected to contain a dictionary where each key (like 'Chaser Px (m)') 
    maps to a numpy array of values (one per time step).
    """
    
    def __init__(self, npy_file):
        """
        Initialize by loading the data and extracting positions.
        
        Parameters
        ----------
        npy_file : str
            Path to the .npy file containing the logged data.
        """
        self.npy_file = npy_file
        # Load the data; if it's stored as a 0-d array containing a dict, extract it.
        data_loaded = np.load(npy_file, allow_pickle=True)
        if isinstance(data_loaded, np.ndarray) and data_loaded.shape == ():
            self.data = data_loaded.item()
        else:
            self.data = data_loaded

        # Determine the number of frames
        self.n_frames = len(self.data['Time (s)'])
        
        # For performance, subsample frames if there are too many
        self.max_frames = 200  # Maximum number of frames for smooth animation
        self.skip = max(1, self.n_frames // self.max_frames)
        self.effective_frames = self.n_frames // self.skip
        
        # Set spacecraft size (0.3m x 0.3m)
        self.spacecraft_size = 0.3
        
        self._extract_positions()
        self.fig = None

    def _extract_positions(self):
        """
        Extract position data and rotation data for chaser, target, and optionally obstacle.
        Subsample for performance if needed.
        """
        # Extract all data first
        self.time = self.data['Time (s)']
        self.chaser_x = self.data['Chaser Px (m)']
        self.chaser_y = self.data['Chaser Py (m)']
        self.target_x = self.data['Target Px (m)']
        self.target_y = self.data['Target Py (m)']
        
        # Extract rotation data if available
        self.chaser_rot = self.data.get('Chaser Rz (rad)', np.zeros_like(self.time))
        self.target_rot = self.data.get('Target Rz (rad)', np.zeros_like(self.time))
        
        # Check if obstacle data exists
        if 'Obstacle Px (m)' in self.data and 'Obstacle Py (m)' in self.data:
            self.obstacle_x = self.data['Obstacle Px (m)']
            self.obstacle_y = self.data['Obstacle Py (m)']
            self.obstacle_rot = self.data.get('Obstacle Rz (rad)', np.zeros_like(self.time))
        else:
            self.obstacle_x = None
            self.obstacle_y = None
            self.obstacle_rot = None
            
        # Subsample data for performance
        if self.skip > 1:
            self.time = self.time[::self.skip]
            self.chaser_x = self.chaser_x[::self.skip]
            self.chaser_y = self.chaser_y[::self.skip]
            self.chaser_rot = self.chaser_rot[::self.skip]
            self.target_x = self.target_x[::self.skip]
            self.target_y = self.target_y[::self.skip]
            self.target_rot = self.target_rot[::self.skip]
            if self.obstacle_x is not None:
                self.obstacle_x = self.obstacle_x[::self.skip]
                self.obstacle_y = self.obstacle_y[::self.skip]
                self.obstacle_rot = self.obstacle_rot[::self.skip]

    def _create_square_shape(self, x, y, rotation, size, color):
        """
        Create a rotated square shape representing a spacecraft.
        
        Parameters
        ----------
        x, y : float
            Center coordinates of the square
        rotation : float
            Rotation angle in radians
        size : float
            Side length of the square in meters
        color : str
            Fill color of the square
            
        Returns
        -------
        list
            List of (x, y) coordinates for the rotated square
        """
        # Create square corners (centered at origin)
        half_size = size / 2
        corners = np.array([
            [-half_size, -half_size],
            [half_size, -half_size],
            [half_size, half_size],
            [-half_size, half_size],
            [-half_size, -half_size]  # Close the shape
        ])
        
        # Rotation matrix
        rot_matrix = np.array([
            [np.cos(rotation), -np.sin(rotation)],
            [np.sin(rotation), np.cos(rotation)]
        ])
        
        # Apply rotation and translation
        rotated_corners = np.dot(corners, rot_matrix.T)
        rotated_corners[:, 0] += x
        rotated_corners[:, 1] += y
        
        return rotated_corners

    def create_animation(self):
        """
        Create the animated Plotly figure showing spacecraft trajectories.
        
        Returns
        -------
        fig : plotly.graph_objects.Figure
            The animated figure.
        """
        # Calculate data ranges for better axis limits
        all_x = np.concatenate([self.chaser_x, self.target_x])
        all_y = np.concatenate([self.chaser_y, self.target_y])
        if self.obstacle_x is not None:
            all_x = np.concatenate([all_x, self.obstacle_x])
            all_y = np.concatenate([all_y, self.obstacle_y])
            
        # x_min, x_max = np.min(all_x), np.max(all_x)
        # y_min, y_max = np.min(all_y), np.max(all_y)
        
        # # Add padding around the data (including spacecraft size)
        # padding = max(0.5, self.spacecraft_size * 2)
        # x_min -= padding
        # x_max += padding
        # y_min -= padding
        # y_max += padding

        # With fixed ranges:
        x_min, x_max = -0.5, 4.0  # Set your desired range for x-axis
        y_min, y_max = -0.5, 2.9  # Set your desired range for y-axis
                
        # Create the base figure
        self.fig = make_subplots()

        # Create background rectangle
        rect_corners = np.array([
            [0, 0],
            [3.4, 0],
            [3.4, 2.5],
            [0, 2.5],
            [0, 0]  # Close the shape
        ])

        self.fig.add_trace(go.Scatter(
            x=rect_corners[:, 0], y=rect_corners[:, 1],
            fill="toself",
            fillcolor='rgba(200, 200, 200, 0.2)',  # Very transparent gray
            line=dict(color='black', width=2),  # Black border
            name='Workspace',
            showlegend=False
        ))

        # X-axis (red arrow)
        self.fig.add_trace(go.Scatter(
            x=[0, 0.3],
            y=[0, 0],
            mode='lines+markers',
            line=dict(color='red', width=3),
            marker=dict(size=[0, 15], symbol='arrow', angleref='previous'),
            name='X-axis',
            hoverinfo='none'
        ))

        # Y-axis (green arrow)
        self.fig.add_trace(go.Scatter(
            x=[0, 0],
            y=[0, 0.3],
            mode='lines+markers',
            line=dict(color='green', width=3),
            marker=dict(size=[0, 15], symbol='arrow', angleref='previous'),
            name='Y-axis',
            hoverinfo='none'
        ))
        
        # Create initial paths
        # Chaser path
        self.fig.add_trace(go.Scatter(
            x=[self.chaser_x[0]], y=[self.chaser_y[0]],
            mode='lines',
            line=dict(color='rgba(255, 0, 0, 0.7)', width=2),
            name='Chaser Path'
        ))
        
        # Target path
        self.fig.add_trace(go.Scatter(
            x=[self.target_x[0]], y=[self.target_y[0]],
            mode='lines',
            line=dict(color='rgba(0, 0, 0, 0.7)', width=2),
            name='Target Path'
        ))
        
        # Obstacle path (if available)
        if self.obstacle_x is not None:
            self.fig.add_trace(go.Scatter(
                x=[self.obstacle_x[0]], y=[self.obstacle_y[0]],
                mode='lines',
                line=dict(color='rgba(0, 0, 255, 0.7)', width=2),
                name='Obstacle Path'
            ))
        
        # Create initial spacecraft shapes
        # Chaser spacecraft
        chaser_corners = self._create_square_shape(
            self.chaser_x[0], self.chaser_y[0], 
            self.chaser_rot[0], self.spacecraft_size, 'red'
        )
        self.fig.add_trace(go.Scatter(
            x=chaser_corners[:, 0], y=chaser_corners[:, 1],
            fill="toself",
            fillcolor='rgba(255, 0, 0, 0.5)',
            line=dict(color='black', width=2),
            name='Chaser',
            showlegend=False
        ))
        
        # Target spacecraft
        target_corners = self._create_square_shape(
            self.target_x[0], self.target_y[0], 
            self.target_rot[0], self.spacecraft_size, 'black'
        )
        self.fig.add_trace(go.Scatter(
            x=target_corners[:, 0], y=target_corners[:, 1],
            fill="toself",
            fillcolor='rgba(0, 0, 0, 0.5)',
            line=dict(color='black', width=2),
            name='Target',
            showlegend=False
        ))
        
        # Obstacle spacecraft (if available)
        if self.obstacle_x is not None:
            obstacle_corners = self._create_square_shape(
                self.obstacle_x[0], self.obstacle_y[0], 
                self.obstacle_rot[0], self.spacecraft_size, 'blue'
            )
            self.fig.add_trace(go.Scatter(
                x=obstacle_corners[:, 0], y=obstacle_corners[:, 1],
                fill="toself",
                fillcolor='rgba(0, 0, 255, 0.5)',
                line=dict(color='black', width=2),
                name='Obstacle',
                showlegend=False
            ))
        
        # Update layout with better spacing and centering
        self.fig.update_layout(
            title={
                'text': "Spacecraft Trajectories",
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'size': 24}
            },
            xaxis={
                'range': [x_min, x_max], 
                'title': {
                    'text': "X (m)",
                    'font': {'size': 18},
                    'standoff': 15
                },
                'tickfont': {'size': 14}
            },
            yaxis={
                'range': [y_min, y_max], 
                'title': {
                    'text': "Y (m)",
                    'font': {'size': 18},
                    'standoff': 15
                },
                'tickfont': {'size': 14},
                'scaleanchor': 'x',  # Make sure x and y scales are equal
                'scaleratio': 1
            },
            width=900,
            height=700,
            margin={'l': 80, 'r': 80, 't': 100, 'b': 150},  # Increased margins
            hovermode="closest",
            legend={
                'x': 0.5,
                'y': -0.2,
                'xanchor': 'center',
                'yanchor': 'top',
                'orientation': 'h'
            },
            updatemenus=[{
                "buttons": [
                    {
                        "args": [None, {"frame": {"duration": 50, "redraw": False}, "fromcurrent": True}],
                        "label": "Play",
                        "method": "animate"
                    },
                    {
                        "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}],
                        "label": "Pause",
                        "method": "animate"
                    }
                ],
                "direction": "left",
                "pad": {"r": 10, "t": 10},
                "showactive": False,
                "type": "buttons",
                "x": 0.1,
                "xanchor": "right",
                "y": -0.1,
                "yanchor": "top"
            }],
            template="plotly_white"  # Use a cleaner template
        )
        
        # Create frames
        frames = []
        for i in range(len(self.time)):
            frame_data = []

            # Add background rectangle as first element in each frame
            frame_data.append(go.Scatter(
                x=rect_corners[:, 0], y=rect_corners[:, 1],
                fill="toself",
                fillcolor='rgba(200, 200, 200, 0.2)',  # Very transparent gray
                line=dict(color='black', width=2),  # Black border
                showlegend=False
            ))

            # X-axis (red arrow)
            frame_data.append(go.Scatter(
                x=[0, 0.3],
                y=[0, 0],
                mode='lines+markers',
                line=dict(color='red', width=3),
                marker=dict(size=[0, 15], symbol='arrow', angleref='previous'),
                hoverinfo='none'
            ))

            # Y-axis (green arrow)
            frame_data.append(go.Scatter(
                x=[0, 0],
                y=[0, 0.3],
                mode='lines+markers',
                line=dict(color='green', width=3),
                marker=dict(size=[0, 15], symbol='arrow', angleref='previous'),
                hoverinfo='none'
            ))
            
            # Chaser path
            frame_data.append(go.Scatter(
                x=self.chaser_x[:i+1],
                y=self.chaser_y[:i+1],
                mode='lines',
                line=dict(color='rgba(255, 0, 0, 0.7)', width=2, dash='dot')
            ))
            
            # Target path
            frame_data.append(go.Scatter(
                x=self.target_x[:i+1],
                y=self.target_y[:i+1],
                mode='lines',
                line=dict(color='rgba(0, 0, 0, 0.7)', width=2)
            ))
            
            # Obstacle path (if available)
            if self.obstacle_x is not None:
                frame_data.append(go.Scatter(
                    x=self.obstacle_x[:i+1],
                    y=self.obstacle_y[:i+1],
                    mode='lines',
                    line=dict(color='rgba(0, 0, 255, 0.7)', width=2)
                ))
            
            # Rotated spacecraft shapes
            # Chaser spacecraft
            chaser_corners = self._create_square_shape(
                self.chaser_x[i], self.chaser_y[i], 
                self.chaser_rot[i], self.spacecraft_size, 'red'
            )
            frame_data.append(go.Scatter(
                x=chaser_corners[:, 0], y=chaser_corners[:, 1],
                fill="toself",
                fillcolor='rgba(255, 0, 0, 0.5)',
                line=dict(color='black', width=2),
                showlegend=False
            ))
            
            # Target spacecraft
            target_corners = self._create_square_shape(
                self.target_x[i], self.target_y[i], 
                self.target_rot[i], self.spacecraft_size, 'black'
            )
            frame_data.append(go.Scatter(
                x=target_corners[:, 0], y=target_corners[:, 1],
                fill="toself",
                fillcolor='rgba(0, 0, 0, 0.5)',
                line=dict(color='black', width=2),
                showlegend=False
            ))
            
            # Obstacle spacecraft (if available)
            if self.obstacle_x is not None:
                obstacle_corners = self._create_square_shape(
                    self.obstacle_x[i], self.obstacle_y[i], 
                    self.obstacle_rot[i], self.spacecraft_size, 'blue'
                )
                frame_data.append(go.Scatter(
                    x=obstacle_corners[:, 0], y=obstacle_corners[:, 1],
                    fill="toself",
                    fillcolor='rgba(0, 0, 255, 0.5)',
                    line=dict(color='black', width=2),
                    showlegend=False
                ))
                
            frames.append(go.Frame(data=frame_data, name=str(i)))
        
        self.fig.frames = frames
        
        # Create a more efficient slider - only show key frames
        slider_steps = []
        step_size = max(1, len(frames) // 20)  # Show at most 20 slider steps
        
        for i in range(0, len(frames), step_size):
            step = {
                "args": [
                    [str(i)],
                    {"frame": {"duration": 50, "redraw": False}, "mode": "immediate"}
                ],
                "label": f"{self.time[i]:.1f}",
                "method": "animate"
            }
            slider_steps.append(step)
            
        self.fig.update_layout(
            sliders=[{
                "active": 0,
                "steps": slider_steps,
                "x": 0.5,
                "y": -0.05,
                "xanchor": "center",
                "yanchor": "top",
                "currentvalue": {
                    "font": {"size": 16},
                    "prefix": "Time: ",
                    "suffix": " s",
                    "visible": True,
                    "xanchor": "center"
                },
                "len": 0.7,
                "pad": {"b": 10, "t": 50}
            }]
        )
        
        return self.fig
    
    def show(self):
        """
        Display the animated figure.
        """
        if self.fig is None:
            self.create_animation()
        
        # Use renderer that works better for complex animations
        self.fig.show(renderer="browser")
        
    def save_html(self, filename="spacecraft_animation.html"):
        """
        Save the animation as an HTML file for better performance.
        """
        if self.fig is None:
            self.create_animation()
            
        # Set the HTML config to center the plot
        config = {
            'responsive': True,
            'displayModeBar': True,
            'displaylogo': False
        }
            
        # Add custom CSS to center the plot
        html_string = self.fig.to_html(
            include_plotlyjs=True,
            config=config,
            full_html=True
        )
        
        # Insert CSS for centering
        css_style = """
        <style>
        .plotly-graph-div {
            margin: 0 auto;
            display: block !important;
        }
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            min-height: 100vh;
        }
        .js-plotly-plot {
            background-color: white;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            padding: 10px;
        }
        </style>
        """
        
        # Insert the CSS after the opening <head> tag
        html_string = html_string.replace('<head>', '<head>' + css_style)
        
        # Write to file
        with open(filename, 'w') as f:
            f.write(html_string)
            
        print(f"Animation saved to {filename}")

# Example usage:
if __name__ == "__main__":
    
    # Create a root window but hide it
    root = tk.Tk()
    root.withdraw()
    
    # Ask the user to select the .npy file
    file_path = filedialog.askopenfilename(
        title="Select spacecraft data file",
        filetypes=[("NumPy files", "*.npy"), ("All files", "*.*")]
    )
    
    if file_path:
        animator = SpacecraftAnimator(file_path)
        # For best performance, save to HTML and open in browser
        #animator.save_html()
        # Or show directly
        animator.show()
    else:
        print("No file selected. Exiting.")