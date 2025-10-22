"""
Test script for ESP-Drone Controller Application

This script allows testing the controller UI without connecting to a real drone.
It mocks the DroneConnection class to simulate drone responses.

Usage:
    python test.py

Features:
    - Simulates drone connection (always succeeds)
    - Logs all commands to console
    - Tests keyboard controls safely
    - No hardware required
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk as sv
from unittest.mock import Mock, MagicMock
import sys


class MockCommander:
    """Mock commander object that simulates cflib commander."""

    def __init__(self):
        self.last_setpoint = None
        self.stop_called = False
        self.setpoint_count = 0

    def send_setpoint(self, roll, pitch, yawrate, thrust):
        """Simulate sending a setpoint."""
        self.last_setpoint = {
            'roll': roll,
            'pitch': pitch,
            'yawrate': yawrate,
            'thrust': thrust
        }
        self.setpoint_count += 1

        # Only print every 50th setpoint to avoid flooding console (0.5 second intervals)
        if self.setpoint_count % 50 == 0:
            print(f"[MOCK] Setpoint #{self.setpoint_count}: roll={roll:.1f}° pitch={pitch:.1f}° yaw={yawrate:.1f}°/s thrust={thrust}")

    def send_stop_setpoint(self):
        """Simulate sending stop setpoint."""
        self.stop_called = True
        self.setpoint_count = 0
        print("[MOCK] STOP setpoint sent")


class MockCrazyflie:
    """Mock Crazyflie object."""

    def __init__(self):
        self.commander = MockCommander()
        self.param = Mock()
        self.param.is_updated = True

    def send_packet(self, data, port, channel):
        """Simulate sending a packet."""
        if len(data) > 0:
            cmd = data[0]
            payload = data[1:] if len(data) > 1 else b''
            print(f"[MOCK] Packet sent: port=0x{port:02X} channel={channel} cmd={cmd} payload={payload.hex()}")


class MockDroneConnection:
    """Mock DroneConnection that simulates drone without real hardware."""

    def __init__(self):
        self.connected = False
        self.cf = None
        self.uri = None
        self.manual_override_enabled = False
        print("[MOCK] DroneConnection initialized (test mode)")

    def connect(self, ip_address: str, port: int = 2390) -> bool:
        """Simulate connecting to drone."""
        print(f"\n[MOCK] Connecting to {ip_address}:{port}...")

        # Simulate connection
        self.uri = f"udp://{ip_address}:{port}"
        self.cf = MockCrazyflie()
        self.connected = True

        print(f"[MOCK] ✓ Successfully connected to {ip_address}:{port}\n")
        return True

    def disconnect(self):
        """Simulate disconnecting from drone."""
        print("\n[MOCK] Disconnecting...")
        self.connected = False
        self.cf = None
        self.manual_override_enabled = False
        print("[MOCK] ✓ Disconnected\n")

    def is_connected(self) -> bool:
        """Check if connected."""
        return self.connected and self.cf is not None

    def send_shape(self, shape_id: int):
        """Simulate sending shape command."""
        shape_names = {
            1: "Square",
            2: "Rectangle",
            3: "Oval",
            4: "Triangle",
            5: "Pentagon"
        }
        shape_name = shape_names.get(shape_id, "Unknown")
        print(f"\n[MOCK] 📐 Shape command sent: {shape_name} (ID={shape_id})\n")

    def send_stop(self):
        """Simulate sending stop command."""
        print("\n[MOCK] 🛑 EMERGENCY STOP command sent\n")

    def send_altitude(self, altitude_mm: int):
        """Simulate setting altitude."""
        print(f"\n[MOCK] ↕️  Altitude set to {altitude_mm}mm ({altitude_mm/1000:.2f}m)\n")

    def send_manual_override(self, enable: bool):
        """Simulate manual override command."""
        self.manual_override_enabled = enable
        mode = "ENABLED" if enable else "DISABLED"
        cmd = 10 if enable else 11
        icon = "🎮" if enable else "🤖"

        if enable:
            print(f"\n[MOCK] {icon} Manual override {mode} (cmd={cmd})")
            print("[MOCK]    → Autonomous flight PAUSED")
            print("[MOCK]    → Keyboard control READY\n")
        else:
            print(f"\n[MOCK] {icon} Manual override {mode} (cmd={cmd})")
            print("[MOCK]    → Autonomous flight RESUMED")
            print("[MOCK]    → Keyboard control DISABLED\n")

    def send_manual_control(self, roll: float, pitch: float, yawrate: float, thrust: int):
        """Simulate sending manual control setpoint."""
        if not self.is_connected():
            return

        # Clamp values (same as real implementation)
        roll = max(-30, min(30, roll))
        pitch = max(-30, min(30, pitch))
        yawrate = max(-200, min(200, yawrate))
        thrust = max(0, min(65535, thrust))

        # Send to mock commander (which will throttle output)
        self.cf.commander.send_setpoint(roll, pitch, yawrate, thrust)

    def send_stop_setpoint(self):
        """Simulate sending stop setpoint."""
        if not self.is_connected():
            return

        self.cf.commander.send_stop_setpoint()


# Patch the drone_connection module
import drone_connection
drone_connection.DroneConnection = MockDroneConnection

# Now import and run the main app
import main

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" " * 15 + "ESP-Drone Controller - TEST MODE")
    print("=" * 70)
    print()
    print("  📋 Test Environment Features:")
    print("     • Simulated drone connection (always succeeds)")
    print("     • All commands logged to console")
    print("     • Keyboard controls fully functional")
    print("     • No hardware required")
    print()
    print("  🎮 Testing Tips:")
    print("     • Use any IP address to 'connect'")
    print("     • Test all autonomous flight buttons")
    print("     • Enable manual control and try keyboard controls")
    print("     • Watch console for command output")
    print()
    print("  ⌨️  Keyboard Controls (when Manual Control enabled):")
    print("     • W/S = Pitch forward/back")
    print("     • A/D = Roll left/right")
    print("     • ↑/↓ = Increase/decrease thrust")
    print("     • ←/→ = Yaw left/right")
    print("     • Space = Reset to hover")
    print()
    print("=" * 70)
    print()

    main.main()
