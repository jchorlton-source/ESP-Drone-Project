"""
Drone connection module using cflib (Crazyflie Python Library).

This module provides a simple interface to connect to the ESP-Drone
over Wi-Fi (UDP) and send AutoNav commands.
"""

import struct
import logging
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

# AutoNav CRTP configuration (matches firmware)
AUTONAV_CRTP_PORT = 0x0D  # CRTP_PORT_PLATFORM
AUTONAV_CRTP_CHANNEL = 0

# AutoNav command codes (from firmware autonav_crtp.h)
class AutoNavCommand:
    STOP = 0
    SQUARE = 1
    RECT = 2
    OVAL = 3
    TRI = 4
    PENTAGON = 5  # Shape ID 5 for pentagon
    SET_ALT_MM = 5
    OVERRIDE_ON = 10
    OVERRIDE_OFF = 11


class DroneConnection:
    """Manages connection to ESP-Drone and AutoNav command sending."""

    def __init__(self):
        """Initialize the drone connection manager."""
        self.scf = None
        self.cf = None
        self.connected = False
        self.uri = None

        # Initialize cflib drivers (only needs to be done once)
        cflib.crtp.init_drivers()

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def connect(self, ip_address: str, port: int = 2390) -> bool:
        """
        Connect to the drone via Wi-Fi (UDP).

        Args:
            ip_address: Drone's IP address (e.g., "192.168.4.1")
            port: UDP port (default: 2390, from firmware)

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Build UDP URI for cflib
            self.uri = f"udp://{ip_address}:{port}"
            self.logger.info(f"Connecting to drone at {self.uri}...")

            # Create SyncCrazyflie instance for synchronous operations
            self.scf = SyncCrazyflie(self.uri, connection_timeout=5.0)
            self.scf.open_link()
            self.cf = self.scf.cf

            # Verify connection by checking if we can get parameters
            # The drone should respond to parameter requests if it's actually connected
            self.logger.info("Verifying drone connection...")

            # Try to access the parameter table of contents (TOC)
            # This will fail if the drone is not actually responding
            if not self.cf.param.is_updated:
                # Wait up to 3 seconds for parameter TOC to be fetched
                import time
                timeout = 3.0
                start_time = time.time()
                while not self.cf.param.is_updated and (time.time() - start_time) < timeout:
                    time.sleep(0.1)

                if not self.cf.param.is_updated:
                    raise Exception("Drone not responding - parameter TOC not received")

            self.connected = True
            self.logger.info(f"Successfully connected and verified {self.uri}")
            return True

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.connected = False
            # Clean up if connection failed
            if self.scf:
                try:
                    self.scf.close_link()
                except:
                    pass
                self.scf = None
            self.cf = None
            return False

    def disconnect(self):
        """Disconnect from the drone."""
        if self.scf:
            try:
                self.scf.close_link()
                self.logger.info("Disconnected from drone")
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")

        self.connected = False
        self.scf = None
        self.cf = None

    def is_connected(self) -> bool:
        """Check if connected to drone."""
        return self.connected and self.cf is not None

    def _send_autonav_command(self, command: int, payload: bytes = b''):
        """
        Send an AutoNav command to the drone.

        Args:
            command: AutoNav command code
            payload: Optional additional data
        """
        if not self.is_connected():
            self.logger.error("Cannot send command: not connected")
            return

        try:
            # Build CRTP packet data: [command_byte] + payload
            data = bytes([command]) + payload

            # Send via cflib's send_packet
            self.cf.send_packet(
                data=data,
                port=AUTONAV_CRTP_PORT,
                channel=AUTONAV_CRTP_CHANNEL
            )
            self.logger.debug(f"Sent AutoNav command: {command}, payload: {payload.hex()}")

        except Exception as e:
            self.logger.error(f"Failed to send command: {e}")

    def send_shape(self, shape_id: int):
        """
        Send a shape command to start autonomous flight.

        Args:
            shape_id: Shape to fly (1=Square, 2=Rectangle, 3=Oval, 4=Triangle, 5=Pentagon)
        """
        shape_names = {
            1: "Square",
            2: "Rectangle",
            3: "Oval",
            4: "Triangle",
            5: "Pentagon"
        }

        if shape_id not in shape_names:
            self.logger.error(f"Invalid shape ID: {shape_id}")
            return

        self.logger.info(f"Sending shape command: {shape_names[shape_id]}")
        self._send_autonav_command(shape_id)

    def send_stop(self):
        """Send STOP command to halt autonomous flight."""
        self.logger.info("Sending STOP command")
        self._send_autonav_command(AutoNavCommand.STOP)

    def send_altitude(self, altitude_mm: int):
        """
        Set target altitude in millimeters.

        Args:
            altitude_mm: Target altitude (e.g., 1200 = 1.2m)
        """
        self.logger.info(f"Setting altitude to {altitude_mm}mm ({altitude_mm/1000:.2f}m)")
        # Pack altitude as uint16 little-endian
        payload = struct.pack('<H', altitude_mm)
        self._send_autonav_command(AutoNavCommand.SET_ALT_MM, payload)

    def send_manual_override(self, enable: bool):
        """
        Enable or disable manual override mode.

        Args:
            enable: True to enable override, False to resume autonomous flight
        """
        cmd = AutoNavCommand.OVERRIDE_ON if enable else AutoNavCommand.OVERRIDE_OFF
        mode = "ENABLED" if enable else "DISABLED"
        self.logger.info(f"Manual override {mode}")
        self._send_autonav_command(cmd)

    def send_manual_control(self, roll: float, pitch: float, yawrate: float, thrust: int):
        """
        Send manual control setpoint to the drone.

        This must be called continuously (every 10ms recommended) to maintain control.
        If setpoints stop arriving, the drone will automatically stop for safety.

        Args:
            roll: Roll angle in degrees (-30 to 30, positive = right)
            pitch: Pitch angle in degrees (-30 to 30, positive = forward)
            yawrate: Yaw rate in degrees/second (-200 to 200, positive = clockwise)
            thrust: Thrust value (0 to 65535, where ~35000 = hover, 10001 = min)
        """
        if not self.is_connected():
            self.logger.error("Cannot send manual control: not connected")
            return

        try:
            # Clamp values to safe ranges
            roll = max(-30, min(30, roll))
            pitch = max(-30, min(30, pitch))
            yawrate = max(-200, min(200, yawrate))
            thrust = max(0, min(65535, thrust))

            # Send setpoint via cflib commander
            self.cf.commander.send_setpoint(roll, pitch, yawrate, thrust)

        except Exception as e:
            self.logger.error(f"Failed to send manual control: {e}")

    def send_stop_setpoint(self):
        """
        Send stop setpoint to cut motors.

        This is the proper way to stop manual control - it tells the drone
        to stop the motors safely.
        """
        if not self.is_connected():
            return

        try:
            self.cf.commander.send_stop_setpoint()
            self.logger.info("Sent stop setpoint")
        except Exception as e:
            self.logger.error(f"Failed to send stop setpoint: {e}")
