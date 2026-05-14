# Usage Guide

## Overview

The application is now organized in two levels:

- Top 80%:
  - left 50%: command spreadsheet
  - right 50%: result spreadsheet
- Bottom 20%:
  - full-width terminal log

All port-related settings are managed from the `Port Settings` menu.

## Main Workflow

1. Open `Port Settings > Configure Ports...`.
2. Create one or more logical ports.
3. Assign each logical port a physical serial device and communication settings.
4. In the command table, create rows that reference the logical `Port #`.
5. Run commands with `Run All`, `Run Selected`, or `Run From Current Row`.
6. Review structured output in the result table and live messages in the log panel.
7. Double-click a `Result Data` cell to open the full response in a separate detail window.

## Command Table Columns

- `Enable`: includes or skips the row during execution
- `Command #`: unique command step number
- `Port #`: logical port number from the port settings menu
- `Command`: text to send
- `Wait Time (ms)`: delay before the next command
- `Next Command #`: optional explicit jump to another command number
- `Timeout (ms)`: response wait period for the command
- `Memo`: free-form note for operators

Use the buttons under the command table to toggle every row's `Enable` checkbox:

- `Select All`
- `Unselect All`

## Port Settings

`Port Settings > Configure Ports...` controls all serial communication options:

- enabled state
- logical port number
- alias
- physical device
- baud rate
- data bits
- parity
- stop bits
- timeout
- write timeout
- encoding
- line ending
- flow control

This keeps CR/LF and all other port settings out of the command table.

## File Menu

- `New Project`: clears the current project
- `Open Project...`: loads a saved JSON project
- `Save Project`: saves to the current project file
- `Save Project As...`: saves to a new JSON project file
- `Export Result Table...`: writes results as CSV
- `Export Terminal Log...`: writes the terminal pane to a text file

## Result View

The Result View panel includes buttons directly under its title:

- `Clear`: clears the result table and resets measurement autosave tracking
- `Export`: exports the current result table to CSV

Each result row now includes:

- `Command #`
- `Port #`
- `Command`
- `Result Data`

Double-click the `Result Data` cell to open the full cell contents in a popup window.

## Automatic Measurement Logging

The application keeps one autosave result file and one autosave terminal log file per project/session in the `log/` folder:

- `PROJECTNAME_results.csv`
- `PROJECTNAME_terminal.log`

If the project has not been saved yet, the autosave base name is `unsaved_project`.

The files are updated automatically as new results and terminal messages arrive. When you use `Clear` in the Result View, the result autosave file is rewritten from the beginning using the cleared table state.

## Run Menu

- `Run All`: runs all enabled command rows
- `Run Selected`: runs only the selected rows
- `Run From Current Row`: runs from the active row to the end
- `Stop`: stops the current execution

## Tools Menu

- `Validate Command Links`: checks whether `Next Command #` targets exist
- `Clear Results`: empties the result spreadsheet
- `Clear Terminal`: empties the terminal log
