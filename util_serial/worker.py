"""
Background reader thread for serial sessions.
"""

from __future__ import annotations

from serial import Serial
from PySide6.QtCore import QThread, Signal


class SerialWorker(QThread):
    """Continuously reads bytes from an open serial connection."""

    data_received = Signal(bytes)
    error_occurred = Signal(str)

    def __init__(self, serial_connection: Serial):
        super().__init__()
        self.serial_connection = serial_connection
        self.running = False

    def run(self) -> None:
        self.running = True
        while self.running and self.serial_connection.is_open:
            try:
                waiting = self.serial_connection.in_waiting
                if waiting:
                    self.data_received.emit(self.serial_connection.read(waiting))
                else:
                    self.msleep(20)
            except Exception as exc:
                self.error_occurred.emit(str(exc))
                break

    def stop(self) -> None:
        self.running = False
        self.wait(1000)
