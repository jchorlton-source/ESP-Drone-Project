"""
Drone connection module using cflib (Crazyflie Python Library).

This module provides a simple interface to connect to the ESP-Drone
over Wi-Fi (UDP) and send AutoNav commands.
"""

import struct
import logging
import cflib.crtp
from cflib.crazyflie import Crazyflie

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
        self.cf = None
        self.connected = False
        self.uri = None
        self.connection_callback = None  # Callback for when connection completes
        self.link_established = False  # Track if link is up even if TOC not complete

        # Initialize cflib drivers (only needs to be done once)
        cflib.crtp.init_drivers()

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def connect(self, ip_address: str, port: int = 2390, callback=None) -> None:
        """
        Connect to the drone via Wi-Fi (UDP). This is asynchronous.

        Args:
            ip_address: Drone's IP address (e.g., "192.168.4.1")
            port: UDP port (default: 2390, from firmware)
            callback: Function to call when connection completes (success: bool)
        """
        # Store callback for later
        self.connection_callback = callback

        try:
            # Build UDP URI for cflib
            self.uri = f"udp://{ip_address}:{port}"
            self.logger.info(f"Connecting to drone at {self.uri}...")

            # Create Crazyflie instance with read-only cache to speed up connection
            # This prevents waiting for param/log TOC if not needed
            self.cf = Crazyflie(ro_cache='./cache', rw_cache='./cache')

            # Register connection callbacks
            self.cf.connected.add_callback(self._on_connected)
            self.cf.disconnected.add_callback(self._on_disconnected)
            self.cf.connection_failed.add_callback(self._on_connection_failed)

            # Also add link quality callback to detect when link is established
            # Use the newer API if available
            try:
                self.cf.link_statistics.link_quality_updated.add_callback(self._on_link_quality)
            except AttributeError:
                # Fallback to old API
                self.cf.link_quality_updated.add_callback(self._on_link_quality)

            # Add console callback - this will fire when we receive console messages
            # which indicates the link is working
            self.cf.console.receivedChar.add_callback(self._on_console_data)

            # Open the link (asynchronous)
            self.cf.open_link(self.uri)

            # Start a timer to check connection status after 2 seconds
            # This is a fallback if callbacks don't fire
            import threading
            self.connection_timer = threading.Timer(2.0, self._check_connection_status)
            self.connection_timer.start()

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.connected = False
            self.cf = None
            if self.connection_callback:
                self.connection_callback(False, str(e))

    def _on_connected(self, uri):
        """Callback when full connection (including TOC) is established."""
        self.logger.info(f"Fully connected to {uri}")
        self.connected = True
        self.link_established = True
        if self.connection_callback:
            self.connection_callback(True, None)
            self.connection_callback = None  # Clear callback after calling

    def _on_link_quality(self, percentage):
        """
        Callback for link quality updates.
        This fires once the link is established, even if TOC isn't complete yet.
        """
        if not self.link_established and self.cf and self.cf.is_connected():
            self.logger.info(f"Link established (quality: {percentage}%)")
            self._mark_link_ready()

    def _on_console_data(self, text):
        """
        Callback for console data.
        Receiving console data means the link is working.
        """
        if not self.link_established and self.cf:
            self.logger.info(f"Received console data - link is active")
            self._mark_link_ready()

    def _check_connection_status(self):
        """
        Fallback timer to check if connection is up.
        Called after a delay if other callbacks haven't fired.
        """
        if not self.link_established and self.cf:
            # Log detailed status for debugging
            self.logger.info(f"Checking connection status...")
            self.logger.info(f"  CF object exists: {self.cf is not None}")
            if self.cf:
                self.logger.info(f"  Has link attr: {hasattr(self.cf, 'link')}")
                if hasattr(self.cf, 'link'):
                    self.logger.info(f"  Link object: {self.cf.link}")
                self.logger.info(f"  Has commander: {hasattr(self.cf, 'commander')}")

            # Check if the link layer is connected, even if TOC isn't complete
            try:
                # If we have a cf object and the link driver is active, consider it connected
                if hasattr(self.cf, 'link') and self.cf.link is not None:
                    self.logger.info("Link appears to be connected (detected by timer)")
                    self._mark_link_ready()
                    return
            except Exception as e:
                self.logger.debug(f"Error checking link status: {e}")

            # Fallback: if we still have a cf object after 2 seconds, assume connection is working
            # since cflib would have called connection_failed if it truly failed
            self.logger.info("Assuming link is ready (no failure reported after 2s)")
            self._mark_link_ready()
        elif not self.link_established:
            self.logger.warning("Connection timeout - no Crazyflie object")
            if self.connection_callback:
                self.connection_callback(False, "Connection timeout")
                self.connection_callback = None

    def _mark_link_ready(self):
        """Mark the link as ready and notify callback."""
        if self.link_established:
            return  # Already marked

        self.link_established = True
        self.connected = True

        # Call the connection callback even if TOC isn't done
        # This allows sending commands while TOC exchange continues in background
        if self.connection_callback:
            self.logger.info("Enabling controls (link ready, TOC may still be loading)")
            self.connection_callback(True, None)
            self.connection_callback = None  # Clear callback after calling

    def _on_disconnected(self, uri):
        """Callback when disconnected."""
        self.logger.info(f"Disconnected from {uri}")
        self.connected = False
        self.link_established = False

    def _on_connection_failed(self, uri, msg):
        """Callback when connection fails."""
        self.logger.error(f"Connection to {uri} failed: {msg}")
        self.connected = False
        self.link_established = False
        if self.connection_callback:
            self.connection_callback(False, msg)
            self.connection_callback = None  # Clear callback after calling

    def disconnect(self):
        """Disconnect from the drone."""
        if self.cf:
            try:
                self.cf.close_link()
                self.logger.info("Disconnected from drone")
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")

        self.connected = False
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
            # Build CRTP packet
            from cflib.crtp.crtpstack import CRTPPacket

            # Create packet with port and channel
            packet = CRTPPacket()
            packet.port = AUTONAV_CRTP_PORT
            packet.channel = AUTONAV_CRTP_CHANNEL

            # Set data: [command_byte] + payload
            packet.data = bytes([command]) + payload

            # Send packet
            self.cf.send_packet(packet)
            self.logger.debug(f"Sent AutoNav command: {command}, payload: {payload.hex() if payload else 'none'}")

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

    def test_motors(self, duration: float = 5.0):
        """
        Test motors by sending low thrust commands for a specified duration.

        This sends continuous setpoint commands at a low thrust level (15000)
        which should spin the motors but not lift off.

        Args:
            duration: How long to run the test in seconds (default: 5.0)
        """
        if not self.is_connected():
            self.logger.error("Cannot test motors: not connected")
            return

        import time

        self.logger.info(f"Starting motor test for {duration}s...")
        self.logger.info(f"CF object: {self.cf}")
        self.logger.info(f"CF link: {self.cf.link if hasattr(self.cf, 'link') else 'no link attr'}")
        self.logger.info(f"CF commander: {self.cf.commander if hasattr(self.cf, 'commander') else 'no commander'}")

        # Low thrust value - enough to spin motors but not lift
        test_thrust = 15000
        start_time = time.time()

        try:
            # Send setpoints continuously for the duration
            count = 0
            while time.time() - start_time < duration:
                # Send setpoint with zero angles and low thrust
                self.cf.commander.send_setpoint(0, 0, 0, test_thrust)
                count += 1
                if count % 100 == 0:
                    self.logger.info(f"Sent {count} setpoints...")
                time.sleep(0.01)  # 100 Hz update rate

            # Stop the motors
            self.cf.commander.send_stop_setpoint()
            self.logger.info(f"Motor test complete - sent {count} setpoints total")

        except Exception as e:
            self.logger.error(f"Motor test failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            # Try to stop motors on error
            try:
                self.cf.commander.send_stop_setpoint()
            except:
                pass
            raise
