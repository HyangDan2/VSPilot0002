# HD2 GUI RS-232C Serial Communicator

A PySide6-based GUI application for RS-232C serial communication with multiple ports support.

## Features

- **Multi-port Support**: Connect to up to 4 RS-232C devices simultaneously
- **Automatic Port Detection**: Scans and lists available serial ports every 5 seconds
- **Configurable Communication Parameters**: 
  - Baud rate (9600, 19200, 38400, 57600, 115200)
  - Data bits (7, 8)
  - Parity (None, Even, Odd)
  - Stop bits (1, 2)
- **Real-time Communication**: Send commands and receive responses in real-time
- **Threaded Architecture**: Non-blocking serial communication using worker threads
- **User-friendly Interface**: Clean, intuitive GUI with status indicators

## Screenshots

![Main Interface](screenshots/main_interface.png)
*Main application interface with 4 port configuration panels*

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/hd2-serial-communicator.git
   cd hd2-serial-communicator
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

### Alternative Installation Methods

#### Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

#### Using Poetry

```bash
# Install poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Run application
poetry run python main.py
```

## Usage

### Basic Operation

1. **Launch the application**:
   ```bash
   python main.py
   ```

2. **Connect to a device**:
   - Click "Scan RS-232C Devices" to refresh available ports
   - Select a port from the dropdown menu
   - Configure communication parameters (baud rate, data bits, etc.)
   - Click "Connect"

3. **Send commands**:
   - Type your command in the "Command" field
   - Press Enter or click "Send"
   - Responses will appear in the "Return Value" area

4. **Monitor communication**:
   - Sent commands are prefixed with `>>>`
   - Received data is prefixed with `<<<`
   - Errors are clearly marked

### Advanced Features

#### Multiple Port Management
- Each port can be configured independently
- Different communication parameters per port
- Simultaneous connections to multiple devices

#### Auto-scanning
- Ports are automatically scanned every 5 seconds
- New devices are automatically detected
- Disconnected devices are handled gracefully

## Project Structure

```
hd2-serial-communicator/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── GIT_COMMIT_GUIDE.md    # Git commit guidelines
│
├── gui/                   # GUI modules
│   ├── __init__.py
│   ├── main_window.py     # Main application window
│   └── serial_port_frame.py  # Individual port frame
│
├── serial/                # Serial communication modules
│   ├── __init__.py
│   └── worker.py          # Serial worker thread
│
└── screenshots/           # Application screenshots
    └── main_interface.png
```

## Architecture

### Core Components

1. **MainWindow** (`gui/main_window.py`):
   - Main application window
   - Manages multiple port frames
   - Handles port scanning and UI updates

2. **SerialPortFrame** (`gui/serial_port_frame.py`):
   - Individual port configuration and communication
   - Handles connection management
   - Processes send/receive operations

3. **SerialWorker** (`serial/worker.py`):
   - Background thread for serial communication
   - Non-blocking data reading
   - Error handling and reporting

### Design Patterns

- **Observer Pattern**: Qt signals/slots for communication between components
- **Worker Thread Pattern**: Background processing for serial I/O
- **Modular Design**: Separation of concerns between GUI and serial logic

## Configuration

### Default Settings

- **Baud Rate**: 9600
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **Port Scan Interval**: 5 seconds
- **Serial Timeout**: 1 second

### Customization

Settings can be modified in the respective module files:

- Communication parameters: `gui/serial_port_frame.py`
- Scan interval: `gui/main_window.py`
- UI layout: Individual GUI modules

## Troubleshooting

### Common Issues

1. **Port Access Denied**:
   - Ensure no other application is using the port
   - Check user permissions (may need admin/sudo)
   - Verify cable connections

2. **Device Not Detected**:
   - Check physical connections
   - Verify device is powered on
   - Try different USB ports
   - Update device drivers

3. **Communication Errors**:
   - Verify communication parameters match device settings
   - Check cable integrity
   - Ensure proper ground connections

### Debug Mode

Enable debug logging by modifying the worker thread:

```python
# In serial/worker.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Development

### Setting Up Development Environment

1. **Fork and clone the repository**
2. **Create a virtual environment**
3. **Install development dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-qt  # For testing
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gui --cov=