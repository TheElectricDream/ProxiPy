import customtkinter as ctk
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from customtkinter import filedialog
import tkinter as tk

# Set appearance and color theme (optional)
ctk.set_appearance_mode("System")  # Options: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"
# Set proper widget scaling (fixes text scaling issues)
ctk.set_widget_scaling(2.0)  # Adjust value between 0.5 and 2.0 as needed
ctk.set_window_scaling(2.0)  # Adjust value between 0.5 and 2.0 as needed

# Create the main application window
app = ctk.CTk()
app.geometry("800x600")
app.title("CustomTkinter Tabbed GUI")

# Create a CTkTabview widget
tabview = ctk.CTkTabview(app, width=780, height=580)
tabview.pack(padx=10, pady=10)

# Add five tabs with specified names:
tabview.add("Initialize Parameters")
tabview.add("Setup & Run Simulations")
tabview.add("Setup & Run Experiments")
tabview.add("Hardware Control")
tabview.add("Data Inspector")

# Get the "Initialize Parameters" tab
init_tab = tabview.tab("Initialize Parameters")
# Get the "Data Inspector" tab
data_inspector_tab = tabview.tab("Data Inspector")

# Variables to store data
loaded_data = {}
selected_x_key = ctk.StringVar()
selected_y_key = ctk.StringVar()

# Function to load NPY data
def load_npy_data():
    filepath = filedialog.askopenfilename(
        title="Select NPY File",
        filetypes=[("NumPy Files", "*.npy")]
    )
    if filepath:
        global loaded_data
        try:
            loaded_data = np.load(filepath, allow_pickle=True).item()
            if isinstance(loaded_data, dict):
                # Update dropdowns with dictionary keys
                keys = list(loaded_data.keys())
                x_dropdown.configure(values=keys)
                y_dropdown.configure(values=keys)
                if keys:
                    selected_x_key.set(keys[0])
                    selected_y_key.set(keys[0])
                    plot_data()
                status_label.configure(text=f"Loaded: {os.path.basename(filepath)}")
            else:
                status_label.configure(text="Error: File is not a dictionary")
        except Exception as e:
            status_label.configure(text=f"Error: {str(e)}")

# Function to export plot to PDF
def export_to_pdf():
    if not hasattr(plot_data, 'current_fig'):
        status_label.configure(text="No plot to export")
        return
    
    filepath = filedialog.asksaveasfilename(
        title="Save Plot as PDF",
        defaultextension=".pdf",
        filetypes=[("PDF Files", "*.pdf")]
    )
    
    if filepath:
        try:
            plot_data.current_fig.savefig(filepath, format='pdf', bbox_inches='tight')
            status_label.configure(text=f"Plot exported to: {os.path.basename(filepath)}")
        except Exception as e:
            status_label.configure(text=f"Error exporting: {str(e)}")

# Function to plot selected data with matplotlib
def plot_data():
    x_key = selected_x_key.get()
    y_key = selected_y_key.get()
    
    if not x_key or not y_key or x_key not in loaded_data or y_key not in loaded_data:
        return
    
    x_data = loaded_data[x_key]
    y_data = loaded_data[y_key]
    
    # Clear the previous plot by destroying the frame
    for widget in plot_frame.winfo_children():
        widget.destroy()
    
    # Import matplotlib and backend for tkinter
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    
    # Create matplotlib figure with dark theme
    plt.style.use('dark_background')
    fig = Figure(figsize=(5, 4), dpi=100, facecolor='#333333')
    ax = fig.add_subplot(111)
    ax.set_facecolor('#333333')
    
    # Increase font sizes
    font_size = 14
    title_font_size = 16
    
    # Handle different data types
    if isinstance(y_data, np.ndarray):
        if y_data.ndim == 1:
            # 1D array - line plot
            if isinstance(x_data, np.ndarray) and x_data.ndim == 1 and len(x_data) == len(y_data):
                ax.plot(x_data, y_data, '-', color='#5599ff', linewidth=1.5)
            else:
                ax.plot(y_data, '-', color='#5599ff', linewidth=1.5)
                
            ax.set_title(f"{y_key} vs {x_key}", color='white', fontsize=title_font_size)
            ax.set_xlabel(x_key, color='white', fontsize=font_size)
            ax.set_ylabel(y_key, color='white', fontsize=font_size)
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.tick_params(colors='white', labelsize=font_size)
        elif y_data.ndim == 2:
            # 2D array - heatmap
            img = ax.imshow(y_data, cmap='plasma', aspect='auto')
            ax.set_title(y_key, color='white', fontsize=title_font_size)
            ax.set_xlabel('X Dimension', color='white', fontsize=font_size)
            ax.set_ylabel('Y Dimension', color='white', fontsize=font_size)
            ax.tick_params(colors='white', labelsize=font_size)
            cbar = fig.colorbar(img, ax=ax)
            cbar.ax.yaxis.set_tick_params(color='white', labelsize=font_size)
            cbar.outline.set_edgecolor('white')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white', fontsize=font_size)
        else:
            ax.text(0.5, 0.5, f"Cannot display {y_data.ndim}D array", 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, color='white', fontsize=font_size)
    else:
        ax.text(0.5, 0.5, f"Data type: {type(y_data)}", 
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes, color='white', fontsize=font_size)
    
    # Set grid and spine colors
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_color('white') 
    ax.spines['right'].set_color('white')
    ax.spines['left'].set_color('white')
    
    # Save the current figure for export
    plot_data.current_fig = fig
    
    # Create canvas and add to frame
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

# Create frame for controls in the Data Inspector tab
controls_frame = ctk.CTkFrame(data_inspector_tab)
controls_frame.pack(fill="x", padx=10, pady=10)

# Add load button
load_button = ctk.CTkButton(controls_frame, text="Load NPY Data", command=load_npy_data)
load_button.pack(side="left", padx=5)

# X-axis dropdown selector with label
x_label = ctk.CTkLabel(controls_frame, text="X:")
x_label.pack(side="left", padx=(10, 2))
x_dropdown = ctk.CTkComboBox(controls_frame, variable=selected_x_key, values=[], 
                            command=lambda x: plot_data(), width=120)
x_dropdown.pack(side="left", padx=2)

# Y-axis dropdown selector with label
y_label = ctk.CTkLabel(controls_frame, text="Y:")
y_label.pack(side="left", padx=(10, 2))
y_dropdown = ctk.CTkComboBox(controls_frame, variable=selected_y_key, values=[], 
                            command=lambda x: plot_data(), width=120)
y_dropdown.pack(side="left", padx=2)

# Add export to PDF button
export_button = ctk.CTkButton(controls_frame, text="Export to PDF", command=export_to_pdf)
export_button.pack(side="left", padx=10)

# Status label
status_label = ctk.CTkLabel(controls_frame, text="No file loaded")
status_label.pack(side="left", padx=10)

# Create a frame for the plot in the Data Inspector tab
plot_frame = ctk.CTkFrame(data_inspector_tab)
plot_frame.pack(fill="both", expand=True, padx=10, pady=10)

# Initialize Parameters tab content (left empty for now)
init_label = ctk.CTkLabel(init_tab, text="Initialize Parameters")
init_label.pack(pady=20)

# Optionally, set the default active tab
tabview.set("Data Inspector")

# Start the GUI event loop
app.mainloop()
