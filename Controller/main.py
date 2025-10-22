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

        # Manual control state
        self.manual_control_active = False
        self.pressed_keys = set()
        self.control_timer = None

        # Manual control parameters
        self.base_thrust = 32000  # Approximate hover thrust
        self.thrust_step = 2000   # Thrust adjustment per key press
        self.current_thrust = 0   # Current thrust value
        self.max_angle = 15.0     # Max roll/pitch angle in degrees
        self.max_yawrate = 100.0  # Max yaw rate in degrees/s

        self.setup_ui()
        self.setup_keyboard_bindings()

    def setup_ui(self):
        """Setup the user interface."""
        # Window configuration
        self.root.title("ESP-Drone Controller")
        self.root.geometry('900x650')

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

        # Manual Control (combines override + keyboard control)
        self.manual_control_btn = ttk.Button(frame, text='Enable Manual Control',
                                             command=self.toggle_manual_control, state='disabled')
        self.manual_control_btn.pack(side='right', padx=5)

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

        # Manual control help text (initially hidden)
        self.control_help_label = ttk.Label(frame,
                                           text="Keyboard Controls: W/S=Pitch  A/D=Roll  ↑/↓=Thrust  ←/→=Yaw  Space=Reset",
                                           foreground="cyan")
        # Don't pack yet - only show when manual control is active

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
        self.altitude_btn.config(state=state)
        self.manual_control_btn.config(state=state)

        # If disconnecting, stop manual control
        if not enabled and self.manual_control_active:
            self.stop_manual_control()

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

    def setup_keyboard_bindings(self):
        """Setup keyboard event handlers for manual control."""
        self.root.bind('<KeyPress>', self.on_key_press)
        self.root.bind('<KeyRelease>', self.on_key_release)

    def on_key_press(self, event):
        """Handle key press events."""
        if not self.manual_control_active:
            return

        key = event.keysym.lower()
        self.pressed_keys.add(key)

    def on_key_release(self, event):
        """Handle key release events."""
        if not self.manual_control_active:
            return

        key = event.keysym.lower()
        self.pressed_keys.discard(key)

    def toggle_manual_control(self):
        """Toggle manual keyboard control on/off."""
        if not self.drone.is_connected():
            return

        if self.manual_control_active:
            self.stop_manual_control()
        else:
            self.start_manual_control()

    def start_manual_control(self):
        """Start manual keyboard control mode."""
        response = messagebox.askyesno(
            "Enable Manual Control",
            "Enable manual control?\n\n"
            "This will:\n"
            "• Pause autonomous flight\n"
            "• Enable keyboard control\n\n"
            "Controls:\n"
            "• W/S = Pitch forward/back\n"
            "• A/D = Roll left/right\n"
            "• ↑/↓ = Increase/decrease thrust\n"
            "• ←/→ = Yaw left/right\n"
            "• Space = Reset to zero\n\n"
            "⚠️ WARNING:\n"
            "• Drone should already be hovering\n"
            "• Start with small inputs\n"
            "• Press 'Disable Manual Control' to stop"
        )

        if not response:
            return

        # Send manual override command to pause autonomous flight
        self.drone.send_manual_override(True)

        self.manual_control_active = True
        self.current_thrust = self.base_thrust
        self.pressed_keys.clear()

        # Update UI
        self.manual_control_btn.config(text='Disable Manual Control')
        self.control_help_label.pack(pady=5)
        self.status_label.config(text="Status: MANUAL CONTROL ACTIVE (Keyboard)",
                                foreground="yellow")

        # Disable other flight controls while in manual mode
        for btn in self.shape_buttons:
            btn.config(state='disabled')

        # Start the control loop (100 Hz = every 10ms)
        self.send_control_loop()

    def stop_manual_control(self):
        """Stop manual keyboard control mode."""
        if not self.manual_control_active:
            return

        self.manual_control_active = False
        self.pressed_keys.clear()

        # Cancel the timer
        if self.control_timer:
            self.root.after_cancel(self.control_timer)
            self.control_timer = None

        # Send stop setpoint
        self.drone.send_stop_setpoint()

        # Send manual override OFF to resume autonomous flight capability
        self.drone.send_manual_override(False)

        # Update UI
        self.manual_control_btn.config(text='Enable Manual Control')
        self.control_help_label.pack_forget()
        self.status_label.config(text="Status: Manual control stopped",
                                foreground="orange")

        # Re-enable other controls
        for btn in self.shape_buttons:
            btn.config(state='normal')

    def send_control_loop(self):
        """Continuously send control setpoints based on pressed keys."""
        if not self.manual_control_active:
            return

        # Calculate control values based on pressed keys
        roll = 0.0
        pitch = 0.0
        yawrate = 0.0

        # Roll control (A/D)
        if 'a' in self.pressed_keys:
            roll = -self.max_angle
        if 'd' in self.pressed_keys:
            roll = self.max_angle

        # Pitch control (W/S)
        if 'w' in self.pressed_keys:
            pitch = self.max_angle
        if 's' in self.pressed_keys:
            pitch = -self.max_angle

        # Yaw control (Arrow keys left/right)
        if 'left' in self.pressed_keys:
            yawrate = -self.max_yawrate
        if 'right' in self.pressed_keys:
            yawrate = self.max_yawrate

        # Thrust control (Arrow keys up/down)
        if 'up' in self.pressed_keys:
            self.current_thrust = min(60000, self.current_thrust + self.thrust_step)
        if 'down' in self.pressed_keys:
            self.current_thrust = max(10001, self.current_thrust - self.thrust_step)

        # Reset (Space)
        if 'space' in self.pressed_keys:
            roll = 0.0
            pitch = 0.0
            yawrate = 0.0
            self.current_thrust = self.base_thrust

        # Send the control setpoint
        self.drone.send_manual_control(roll, pitch, yawrate, int(self.current_thrust))

        # Schedule next update (10ms = 100 Hz)
        self.control_timer = self.root.after(10, self.send_control_loop)


def main():
    """Main entry point."""
    root = tk.Tk()
    sv.set_theme("dark")
    app = DroneControllerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
