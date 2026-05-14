"""
Command execution thread for the spreadsheet command table.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtCore import QThread, Signal

from util_serial.manager import SerialPortManager


@dataclass
class CommandStep:
    command_no: int
    port_no: int
    command: str
    wait_time_ms: int = 0
    next_command_no: Optional[int] = None
    timeout_ms: int = 1000
    memo: str = ""


class CommandExecutor(QThread):
    """Runs enabled command rows in sequence on a worker thread."""

    result_ready = Signal(dict)
    log_message = Signal(str)
    finished_state = Signal(bool, str)

    def __init__(self, steps: List[CommandStep], manager: SerialPortManager):
        super().__init__()
        self.steps = steps
        self.manager = manager
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        if not self.steps:
            self.finished_state.emit(True, "No commands to execute.")
            return

        step_lookup: Dict[int, CommandStep] = {step.command_no: step for step in self.steps}
        current = self.steps[0]

        while self._running and current:
            started = time.monotonic()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                self.log_message.emit(
                    f"Executing Command #{current.command_no} on Port #{current.port_no}: {current.command}"
                )
                raw_response = self.manager.execute_command(current.port_no, current.command, current.timeout_ms)
                decoded_response = raw_response.decode("utf-8", errors="replace").strip()
                elapsed_ms = int((time.monotonic() - started) * 1000)

                self.result_ready.emit(
                    {
                        "time": timestamp,
                        "command_no": current.command_no,
                        "port_no": current.port_no,
                        "command": current.command,
                        "result_data": decoded_response,
                        "status": "OK",
                        "elapsed_ms": elapsed_ms,
                    }
                )
            except Exception as exc:
                elapsed_ms = int((time.monotonic() - started) * 1000)
                self.result_ready.emit(
                    {
                        "time": timestamp,
                        "command_no": current.command_no,
                        "port_no": current.port_no,
                        "command": current.command,
                        "result_data": str(exc),
                        "status": "ERROR",
                        "elapsed_ms": elapsed_ms,
                    }
                )
                self.finished_state.emit(False, f"Execution stopped at Command #{current.command_no}: {exc}")
                return

            if current.wait_time_ms > 0:
                remaining = current.wait_time_ms / 1000.0
                while self._running and remaining > 0:
                    chunk = min(remaining, 0.05)
                    time.sleep(chunk)
                    remaining -= chunk

            if not self._running:
                self.finished_state.emit(False, "Execution stopped by user.")
                return

            if current.next_command_no is None:
                next_step = self.next_step_in_order(current)
            else:
                next_step = step_lookup.get(current.next_command_no)
                if next_step is None:
                    self.finished_state.emit(
                        False,
                        f"Execution stopped because Command #{current.command_no} points to missing Next Command #{current.next_command_no}.",
                    )
                    return
            current = next_step

        self.finished_state.emit(True, "Execution finished successfully.")

    def next_step_in_order(self, current: CommandStep) -> Optional[CommandStep]:
        try:
            index = self.steps.index(current)
        except ValueError:
            return None
        if index + 1 >= len(self.steps):
            return None
        return self.steps[index + 1]
