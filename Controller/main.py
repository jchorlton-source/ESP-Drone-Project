"""
ESP-Drone Controller Application

Desktop controller for ESP-Drone using Wi-Fi (UDP) communication.
Supports AutoNav autonomous flight commands.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk as sv
from drone_connection import DroneConnection

# Default drone settings (ESP32 AP mode defaults)
DEFAULT_IP = "192.168.4.1"
DEFAULT_PORT = 2390
DEFAULT_ALTITUDE_MM = 1200  # 1.2 meters


class DroneControllerApp:
    """Main application class for the drone controller."""

    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.drone = DroneConnection()
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        # Window configuration
        self.root.title("ESP-Drone Controller")
        self.root.geometry('900x500')

        # Connection Frame
        self.create_connection_frame()

        # Flight Paths Frame
        self.create_flight_paths_frame()

        # Settings Frame
        self.create_settings_frame()

        # Status Frame
        self.create_status_frame()

    def create_connection_frame(self):
        """Create the connection controls frame."""
        frame = ttk.LabelFrame(self.root, text='Drone Communication', padding=10)
        frame.pack(fill='x', padx=10, pady=5)

        # IP Address
        ttk.Label(frame, text='Drone IP Address:').pack(side='left', padx=(0, 5))
        self.ip_entry = ttk.Entry(frame, width=15)
        self.ip_entry.insert(0, DEFAULT_IP)
        self.ip_entry.pack(side='left', padx=5)

        # Port
        ttk.Label(frame, text='Port:').pack(side='left', padx=(10, 5))
        self.port_entry = ttk.Entry(frame, width=8)
        self.port_entry.insert(0, str(DEFAULT_PORT))
        self.port_entry.pack(side='left', padx=5)

        # Connect Button
        self.connect_btn = ttk.Button(frame, text='Connect', command=self.connect)
        self.connect_btn.pack(side='left', padx=10)

        # Disconnect Button
        self.disconnect_btn = ttk.Button(frame, text='Disconnect',
                                         command=self.disconnect, state='disabled')
        self.disconnect_btn.pack(side='left', padx=5)

        # Emergency Stop
        self.stop_btn = ttk.Button(frame, text='EMERGENCY STOP',
                                   command=self.emergency_stop, state='disabled')
        self.stop_btn.pack(side='right', padx=5)

        # Manual Override
        self.override_btn = ttk.Button(frame, text='Manual Override',
                                       command=self.toggle_override, state='disabled')
        self.override_btn.pack(side='right', padx=5)

    def create_flight_paths_frame(self):
        """Create the autonomous flight paths frame."""
        frame = ttk.LabelFrame(self.root, text="Autonomous Flight Paths", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        info_label = ttk.Label(frame,
                              text="⚠️ Only send flight commands when drone is stationary and in the air!",
                              foreground="orange")
        info_label.pack(pady=(0, 10))

        # Create buttons for all firmware-supported shapes
        shapes = [
            (1, 'Square', 'Fly a square pattern'),
            (2, 'Rectangle', 'Fly a rectangular pattern'),
            (3, 'Oval', 'Fly an oval pattern'),
            (4, 'Triangle', 'Fly a triangular pattern'),
            (5, 'Pentagon', 'Fly a pentagon pattern'),
        ]

        button_frame = ttk.Frame(frame)
        button_frame.pack(expand=True)

        self.shape_buttons = []
        for shape_id, name, tooltip in shapes:
            btn = ttk.Button(button_frame, text=name, width=20,
                           command=lambda sid=shape_id, n=name: self.send_shape(sid, n),
                           state='disabled')
            btn.pack(pady=5)
            self.shape_buttons.append(btn)

    def create_settings_frame(self):
        """Create the settings frame."""
        frame = ttk.LabelFrame(self.root, text="Settings", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        # Altitude setting
        ttk.Label(frame, text='Target Altitude (mm):').pack(side='left', padx=(0, 5))
        self.altitude_entry = ttk.Entry(frame, width=10)
        self.altitude_entry.insert(0, str(DEFAULT_ALTITUDE_MM))
        self.altitude_entry.pack(side='left', padx=5)

        self.altitude_btn = ttk.Button(frame, text='Set Altitude',
                                      command=self.set_altitude, state='disabled')
        self.altitude_btn.pack(side='left', padx=10)

        ttk.Label(frame, text='(Default: 1200mm = 1.2m)').pack(side='left', padx=5)

    def create_status_frame(self):
        """Create the status display frame."""
        frame = ttk.LabelFrame(self.root, text="Status", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        self.status_label = ttk.Label(frame, text="Status: Not Connected", foreground="red")
        self.status_label.pack()

    def connect(self):
        """Connect to the drone."""
        ip = self.ip_entry.get().strip()
        port_str = self.port_entry.get().strip()

        if not ip:
            messagebox.showerror("Error", "Please enter a valid IP address")
            return

        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid port number")
            return

        # Attempt connection
        success = self.drone.connect(ip, port)

        if success:
            self.status_label.config(text=f"Status: Connected to {ip}:{port}",
                                   foreground="green")
            self.enable_controls(True)
            messagebox.showinfo("Success", f"Connected to drone at {ip}:{port}")
        else:
            self.status_label.config(text="Status: Connection Failed", foreground="red")
            messagebox.showerror("Error",
                               f"Failed to connect to {ip}:{port}\n\n"
                               "Make sure:\n"
                               "1. You're connected to the drone's Wi-Fi (ESP-DRONE)\n"
                               "2. The IP address is correct (usually 192.168.4.1)\n"
                               "3. The drone is powered on")

    def disconnect(self):
        """Disconnect from the drone."""
        self.drone.disconnect()
        self.status_label.config(text="Status: Disconnected", foreground="red")
        self.enable_controls(False)

    def enable_controls(self, enabled: bool):
        """Enable or disable control buttons based on connection status."""
        state = 'normal' if enabled else 'disabled'
        inv_state = 'disabled' if enabled else 'normal'

        # Connection buttons
        self.connect_btn.config(state=inv_state)
        self.disconnect_btn.config(state=state)

        # Flight controls
        for btn in self.shape_buttons:
            btn.config(state=state)

        # Other controls
        self.stop_btn.config(state=state)
        self.override_btn.config(state=state)
        self.altitude_btn.config(state=state)

    def send_shape(self, shape_id: int, shape_name: str):
        """Send a shape command to the drone."""
        if not self.drone.is_connected():
            messagebox.showerror("Error", "Not connected to drone")
            return

        # Confirmation dialog
        response = messagebox.askyesno(
            "Confirm Flight Command",
            f"Send {shape_name} flight path?\n\n"
            "⚠️ WARNING: Only proceed if:\n"
            "• Drone is stationary and hovering\n"
            "• Flight area is clear of obstacles\n"
            "• You're ready to use emergency stop if needed"
        )

        if response:
            self.drone.send_shape(shape_id)
            self.status_label.config(text=f"Status: Flying {shape_name}",
                                   foreground="blue")

    def emergency_stop(self):
        """Send emergency stop command."""
        if not self.drone.is_connected():
            return

        self.drone.send_stop()
        self.status_label.config(text="Status: STOPPED", foreground="orange")
        messagebox.showwarning("Emergency Stop", "STOP command sent to drone!")

    def toggle_override(self):
        """Toggle manual override mode."""
        if not self.drone.is_connected():
            return

        # Ask user what they want to do
        response = messagebox.askyesno(
            "Manual Override",
            "Enable Manual Override?\n\n"
            "YES = Enable manual control (pause autonomous flight)\n"
            "NO = Resume autonomous flight"
        )

        self.drone.send_manual_override(response)
        mode = "Manual Control" if response else "Autonomous"
        self.status_label.config(text=f"Status: {mode} Mode", foreground="purple")

    def set_altitude(self):
        """Set target altitude."""
        if not self.drone.is_connected():
            messagebox.showerror("Error", "Not connected to drone")
            return

        try:
            altitude_mm = int(self.altitude_entry.get().strip())
            if altitude_mm < 100 or altitude_mm > 3000:
                raise ValueError("Altitude out of range")
        except ValueError:
            messagebox.showerror("Error",
                               "Please enter a valid altitude (100-3000mm)")
            return

        self.drone.send_altitude(altitude_mm)
        messagebox.showinfo("Altitude Set",
                          f"Target altitude set to {altitude_mm}mm ({altitude_mm/1000:.2f}m)")


def main():
    """Main entry point."""
    root = tk.Tk()
    sv.set_theme("dark")
    app = DroneControllerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
