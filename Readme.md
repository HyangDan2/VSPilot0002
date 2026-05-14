# HD2 RS-232C Command Studio

HD2 RS-232C Command Studio is a PySide6 desktop application for spreadsheet-style serial command sequencing.

## Interface

The application uses a horizontal `60:20:20` workspace:

- Left 60%: command spreadsheet
- Center 20%: result spreadsheet
- Right 20%: status terminal log

All serial-port settings, including CR/LF line endings, are managed from the `Port Settings` menu.

## Features

- Excel-like command table for serial command sequencing
- Menu-driven logical port configuration
- Structured result capture for each command execution
- Live terminal log for connection state, TX/RX traffic, and errors
- JSON project save/load
- CSV and log export

## Requirements

- Python 3.8 or higher
- PySide6
- pyserial

## Installation

```bash
pip install -r requirements.txt
python main.py
```

## Key Menus

- `File`: project open/save/export
- `Port Settings`: all logical port and serial settings
- `Run`: execution controls
- `View`: layout reset helpers
- `Tools`: validation and clearing utilities

## Documentation

- [Usage Guide](docs/USAGE.md)
- [Architecture Notes](docs/ARCHITECTURE.md)
