# HD2 RS-232C Command Studio

HD2 RS-232C Command Studio is a PySide6 desktop application for spreadsheet-style serial command sequencing.

## Interface

The application uses a split workspace:

- Top 80%:
  - left 50%: command spreadsheet
  - right 50%: result spreadsheet
- Bottom 20%:
  - full-width status terminal log

All serial-port settings, including CR/LF line endings, are managed from the `Port Settings` menu.

## Features

- Excel-like command table for serial command sequencing
- `Select All` / `Unselect All` enable toggles for the command grid
- Menu-driven logical port configuration
- Structured result capture with the originating command shown for each execution
- Double-click Result Data to open the full cell contents in a popup
- Live terminal log for connection state, TX/RX traffic, and errors
- JSON project save/load
- CSV and log export
- Project-scoped autosave into the `log/` folder for results and terminal logs

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
