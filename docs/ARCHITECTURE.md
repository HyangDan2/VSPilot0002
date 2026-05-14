# Architecture Notes

## UI

- `gui/main_window.py`
  Main spreadsheet-style application window with a 50:50 top split, bottom terminal log,
  result detail popup, and project-scoped measurement autosave hooks
- `gui/port_settings_dialog.py`
  Menu-driven dialog for all logical port settings

## Serial Backend

- `util_serial/project_config.py`
  JSON project structure and serial-port dataclasses
- `util_serial/manager.py`
  Owns logical port definitions and active sessions
- `util_serial/session.py`
  Wraps one serial connection and manages line ending, encoding, and response capture
- `util_serial/worker.py`
  Background serial reader thread
- `util_serial/executor.py`
  Runs command-table rows in sequence

## Execution Flow

1. A command row references a logical `Port #`.
2. The executor requests that port from the manager.
3. The manager ensures the corresponding session is connected.
4. The session sends the command using the port settings from the menu.
5. Returned data is captured in the result spreadsheet and mirrored to the terminal log.
6. Result and terminal data are continuously mirrored into project-scoped autosave files under `log/`.

## Project File

The JSON project stores:

- window size
- splitter sizes
- logical port settings
- command table rows

This allows the workspace and serial configuration to be restored together.
