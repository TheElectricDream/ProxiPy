import os
import sys

# Add the project path so that lib files can be read
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

import threading
import subprocess
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk
from customtkinter import filedialog

# Optional: configure logging or appearance here
ctk.set_appearance_mode("System")  # Options: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"
ctk.set_widget_scaling(2.0)  # Adjust value between 0.5 and 2.0 as needed
ctk.set_window_scaling(2.0)  # Adjust value between 0.5 and 2.0 as needed

# =============================================================================
# Main Application Class
# =============================================================================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ProxiPy Graphical Interface")
        self.geometry("800x600")
        
        # Create a CTkTabview widget and add tabs
        self.tabview = ctk.CTkTabview(self, width=780, height=580)
        self.tabview.pack(padx=10, pady=10)
        for tab in ["Initialize Parameters", 
                    "Setup & Run Simulations", 
                    "Setup & Run Experiments", 
                    "Hardware Control", 
                    "Data Inspector"]:
            self.tabview.add(tab)

        # Create and add content to each tab:
        # --- Initialize Parameters tab (placeholder)
        init_tab = self.tabview.tab("Initialize Parameters")
        init_label = ctk.CTkLabel(init_tab, text="Initialize Parameters")
        init_label.pack(pady=20)

        # --- Setup & Run Simulations tab
        sim_tab = self.tabview.tab("Setup & Run Simulations")
        self.simulation_frame = SimulationFrame(sim_tab)
        self.simulation_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Setup & Run Experiments tab (placeholder)
        experiments_tab = self.tabview.tab("Setup & Run Experiments")
        exp_label = ctk.CTkLabel(experiments_tab, text="Experiments (Coming Soon)")
        exp_label.pack(pady=20)

        # --- Hardware Control tab (placeholder)
        hardware_tab = self.tabview.tab("Hardware Control")
        hw_label = ctk.CTkLabel(hardware_tab, text="Hardware Control (Coming Soon)")
        hw_label.pack(pady=20)

        # --- Data Inspector tab
        data_inspector_tab = self.tabview.tab("Data Inspector")
        self.data_inspector_frame = DataInspectorFrame(data_inspector_tab,  corner_radius=20)
        self.data_inspector_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Closing
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        # If you have stored any after callbacks' IDs, cancel them here:
        # self.after_cancel(self.some_callback_id)
        self.destroy()
# =============================================================================
# Simulation Tab Frame
# =============================================================================

class SimulationFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # Add a button to run the simulation
        self.run_sim_button = ctk.CTkButton(self, text="Run Simulation", command=self.run_simulation)
        self.run_sim_button.pack(pady=10, padx=10)

    def run_simulation(self):
        # Disable the button so users cannot click it again during simulation
        self.run_sim_button.configure(state="disabled")
        
        # Create a modal progress window using CTkToplevel
        # progress_window = ctk.CTkToplevel(self)
        # progress_window.title("Simulation Running")
        # progress_window.geometry("300x100")
        # progress_window.grab_set()  # Make modal

        progressbar = ctk.CTkProgressBar(app, orientation="horizontal")
        progressbar.configure(mode="indeterminate")
        progressbar.start()

        # Function to run the external script in a background thread
        def simulation_thread():
            try:
                # Run main.py located in the "main" directory
                process = subprocess.Popen(
                    ["python", "main.py"],
                    cwd=os.path.join(os.getcwd(), "main")
                )
                process.wait()
            except Exception as e:
                print("Error running simulation:", e)
            # When done, schedule the completion handler in the main thread
            self.after(0, simulation_done)

        def simulation_done():
            progressbar.stop()
            self.run_sim_button.configure(state="normal")

        # Start the simulation thread
        threading.Thread(target=simulation_thread, daemon=True).start()

# =============================================================================
# Data Inspector Tab Frame
# =============================================================================

class DataInspectorFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.loaded_data = {}
        self.selected_x_key = ctk.StringVar()
        self.selected_y_key = ctk.StringVar()

        # Create a frame for the controls
        controls_frame = ctk.CTkFrame(self)
        controls_frame.pack(fill="x", padx=10, pady=10)

        load_button = ctk.CTkButton(controls_frame, text="Load NPY Data", command=self.load_npy_data)
        load_button.pack(side="left", padx=5)

        x_label = ctk.CTkLabel(controls_frame, text="X:")
        x_label.pack(side="left", padx=(10, 2))
        self.x_dropdown = ctk.CTkComboBox(controls_frame, variable=self.selected_x_key, values=[], 
                                           command=lambda v: self.plot_data(), width=120)
        self.x_dropdown.pack(side="left", padx=2)

        y_label = ctk.CTkLabel(controls_frame, text="Y:")
        y_label.pack(side="left", padx=(10, 2))
        self.y_dropdown = ctk.CTkComboBox(controls_frame, variable=self.selected_y_key, values=[], 
                                           command=lambda v: self.plot_data(), width=120)
        self.y_dropdown.pack(side="left", padx=2)

        export_button = ctk.CTkButton(controls_frame, text="Export to PDF", command=self.export_to_pdf)
        export_button.pack(side="left", padx=10)

        self.status_label = ctk.CTkLabel(controls_frame, text="No file loaded")
        self.status_label.pack(side="left", padx=10)

        # Create a frame for the plot
        self.plot_frame = ctk.CTkFrame(self)
        self.plot_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def load_npy_data(self):
        filepath = filedialog.askopenfilename(
            title="Select NPY File",
            filetypes=[("NumPy Files", "*.npy")]
        )
        if filepath:
            try:
                self.loaded_data = np.load(filepath, allow_pickle=True).item()
                if isinstance(self.loaded_data, dict):
                    keys = list(self.loaded_data.keys())
                    self.x_dropdown.configure(values=keys)
                    self.y_dropdown.configure(values=keys)
                    if keys:
                        self.selected_x_key.set(keys[0])
                        self.selected_y_key.set(keys[0])
                        self.plot_data()
                    self.status_label.configure(text=f"Loaded: {os.path.basename(filepath)}")
                else:
                    self.status_label.configure(text="Error: File is not a dictionary")
            except Exception as e:
                self.status_label.configure(text=f"Error: {str(e)}")

    def export_to_pdf(self):
        if not hasattr(self, 'current_fig'):
            self.status_label.configure(text="No plot to export")
            return

        filepath = filedialog.asksaveasfilename(
            title="Save Plot as PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if filepath:
            try:
                self.current_fig.savefig(filepath, format='pdf', bbox_inches='tight')
                self.status_label.configure(text=f"Plot exported to: {os.path.basename(filepath)}")
            except Exception as e:
                self.status_label.configure(text=f"Error exporting: {str(e)}")

    def plot_data(self):
        x_key = self.selected_x_key.get()
        y_key = self.selected_y_key.get()
        if not x_key or not y_key or x_key not in self.loaded_data or y_key not in self.loaded_data:
            return

        x_data = self.loaded_data[x_key]
        y_data = self.loaded_data[y_key]

        # Clear any previous plot
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        # Create a matplotlib figure and axis
        fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
        ax.set_facecolor('#333333')
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
            else:
                ax.text(0.5, 0.5, f"Cannot display {y_data.ndim}D array",
                        horizontalalignment='center', verticalalignment='center',
                        color='white', fontsize=14)
        else:
            ax.text(0.5, 0.5, f"Data type: {type(y_data)}",
                    horizontalalignment='center', verticalalignment='center',
                    color='white', fontsize=14)

        # Save figure for later export
        self.current_fig = fig

        # Create a canvas widget to display the matplotlib figure
        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        canvas_widget = canvas.get_tk_widget()
        canvas_widget.configure(bg="#404049")  # or use self.plot_frame.cget("fg_color") if you've set it
        fig.patch.set_facecolor("#404049")

# =============================================================================
# Run the Application
# =============================================================================

if __name__ == "__main__":
    app = App()
    app.mainloop()
