# ESP-Drone Controller

Desktop application for controlling the ESP-Drone over Wi-Fi using AutoNav autonomous flight commands.

## Features

✅ **Wi-Fi/UDP Communication** - Connects to ESP-Drone via Wi-Fi using CRTP protocol
✅ **Autonomous Flight Paths** - Supports all firmware-implemented shapes:
- Square
- Rectangle
- Oval
- Triangle
- Pentagon

✅ **Safety Features**
- Emergency stop button
- Manual override mode
- Altitude control (100-3000mm)
- Safety confirmation dialogs

## Setup

### Prerequisites

1. Python 3.12+
2. `uv` package manager (recommended) or `pip`

### Installation

Using `uv` (recommended):
```bash
# Add cflib dependency
uv add cflib

# Install all dependencies
uv sync
```

Using `pip`:
```bash
pip install cflib sv-ttk
```

## Usage

### 1. Connect to Drone's Wi-Fi

First, connect your computer to the drone's Wi-Fi network:
- **SSID**: `ESP-DRONE`
- **Password**: `12345678`
- **Drone IP**: `192.168.4.1` (default ESP32 AP mode)

### 2. Run the Controller

```bash
# Using uv
uv run python main.py

# Using python directly
python main.py
```

### 3. Connect to Drone

1. The application will pre-fill the default IP (`192.168.4.1`) and port (`2390`)
2. Click **Connect**
3. Wait for confirmation message

### 4. Send Commands

Once connected, you can:
- **Send Shape Commands** - Click any shape button (Square, Rectangle, etc.)
  - ⚠️ Only send when drone is hovering and stationary!
- **Set Altitude** - Enter altitude in millimeters (default: 1200mm = 1.2m)
- **Emergency Stop** - Immediately stops autonomous flight
- **Manual Override** - Pause autonomous flight for manual control

## Architecture

### Files

- **`main.py`** - Main GUI application using Tkinter
- **`drone_connection.py`** - Drone connection manager using cflib
- **`pyproject.toml`** - Project dependencies

### Communication Protocol

The controller uses **CRTP (Crazy RealTime Protocol)** over **UDP**:

1. **Transport Layer**: Wi-Fi UDP (port 2390)
2. **Protocol Layer**: CRTP packets
3. **Application Layer**: AutoNav commands

#### CRTP Configuration
- **Port**: `0x0D` (CRTP_PORT_PLATFORM)
- **Channel**: `0`

#### AutoNav Commands (from firmware)

| Command | ID | Description |
|---------|----|----|
| STOP | 0 | Stop autonomous flight |
| SQUARE | 1 | Fly square pattern |
| RECTANGLE | 2 | Fly rectangular pattern |
| OVAL | 3 | Fly oval pattern |
| TRIANGLE | 4 | Fly triangular pattern |
| PENTAGON | 5 | Fly pentagon pattern |
| SET_ALT_MM | 5 | Set target altitude (with uint16 payload) |
| OVERRIDE_ON | 10 | Enable manual override |
| OVERRIDE_OFF | 11 | Resume autonomous flight |

### Implementation Details

#### Using cflib

The controller uses the official **Crazyflie Python Library (cflib)** which provides:
- ✅ CRTP packet encoding/decoding
- ✅ UDP socket management
- ✅ Connection handling
- ✅ Async callbacks

**Benefits over manual implementation:**
- Tested and maintained by Bitcraze
- Handles protocol edge cases
- Compatible with other Crazyflie tools
- Easier to extend

#### Connection Flow

```python
# 1. Initialize cflib drivers (once)
cflib.crtp.init_drivers()

# 2. Create connection URI
uri = "udp://192.168.4.1:2390"

# 3. Connect using SyncCrazyflie
scf = SyncCrazyflie(uri)
scf.open_link()

# 4. Send CRTP packet
scf.cf.send_packet(
    data=bytes([command]) + payload,
    port=0x0D,  # CRTP_PORT_PLATFORM
    channel=0
)
```

## Troubleshooting

### Connection Failed

**Problem**: Cannot connect to drone

**Solutions**:
1. Verify you're connected to drone's Wi-Fi (`ESP-DRONE`)
2. Check drone is powered on and firmware is running
3. Ping the drone: `ping 192.168.4.1`
4. Check firewall isn't blocking UDP port 2390
5. Try changing IP if drone uses different address

### Commands Not Working

**Problem**: Connected but commands have no effect

**Solutions**:
1. Check drone firmware has AutoNav enabled
2. Verify CRTP port/channel match firmware (0x0D/0)
3. Check drone logs for received packets
4. Ensure drone is in correct state (not in IDLE on ground)

### Module Import Errors

**Problem**: `ModuleNotFoundError: No module named 'cflib'`

**Solution**:
```bash
# Install cflib
uv add cflib
# or
pip install cflib
```

## Safety Notes

⚠️ **IMPORTANT SAFETY GUIDELINES:**

1. **Pre-flight Checks**:
   - Clear flight area of obstacles and people
   - Verify emergency stop works
   - Test connection before flight

2. **During Flight**:
   - Only send shape commands when drone is stable and hovering
   - Keep emergency stop button accessible
   - Monitor drone at all times
   - Be ready to use manual override

3. **Emergency Procedures**:
   - Click **EMERGENCY STOP** to immediately halt autonomous flight
   - Use **Manual Override** to take manual control
   - Have physical kill switch ready as backup

## Future Enhancements

Potential features to add:
- [ ] Real-time telemetry display (altitude, battery, etc.)
- [ ] Custom flight path designer
- [ ] Video feed integration
- [ ] Flight data logging
- [ ] Multiple drone support
- [ ] Keyboard shortcuts for emergency stop

## References

- [ESP-Drone Firmware](../Firmware/esp-drone/)
- [Crazyflie Python Library (cflib)](https://github.com/bitcraze/crazyflie-lib-python)
- [CRTP Protocol Documentation](https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/crtp/)
- [AutoNav Implementation](../Firmware/esp-drone/components/core/crazyflie/modules/src/autonav.c)
