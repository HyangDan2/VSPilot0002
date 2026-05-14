"""
Serial session wrapper for one logical port.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

import serial
from PySide6.QtCore import QObject, Signal

from util_serial.project_config import SerialPortConfig
from util_serial.worker import SerialWorker


class SerialSession(QObject):
    """Wrap a serial connection plus its background reader."""

    data_received = Signal(int, bytes)
    state_changed = Signal(int, bool, str)
    log_message = Signal(str)

    def __init__(self, config: SerialPortConfig):
        super().__init__()
        self.config = config
        self.connection: Optional[serial.Serial] = None
        self.worker: Optional[SerialWorker] = None
        self._buffer = bytearray()
        self._buffer_lock = threading.Lock()
        self._data_event = threading.Event()
        self._last_rx_time = 0.0
        self._rx_chunks = 0
        self._rx_bytes = 0
        self._wait_calls = 0
        self._wait_timeouts = 0
        self._last_wait_bytes = 0

    def connect(self) -> None:
        if self.connection and self.connection.is_open:
            return
        if not self.config.device:
            raise ValueError(f"Logical Port #{self.config.port_no} has no physical device assigned.")

        parity_map = {
            "None": serial.PARITY_NONE,
            "Even": serial.PARITY_EVEN,
            "Odd": serial.PARITY_ODD,
            "Mark": serial.PARITY_MARK,
            "Space": serial.PARITY_SPACE,
        }
        bytesize_map = {
            5: serial.FIVEBITS,
            6: serial.SIXBITS,
            7: serial.SEVENBITS,
            8: serial.EIGHTBITS,
        }
        stopbits_map = {
            1.0: serial.STOPBITS_ONE,
            1.5: serial.STOPBITS_ONE_POINT_FIVE,
            2.0: serial.STOPBITS_TWO,
        }
        flow = self.config.flow_control

        self.connection = serial.Serial(
            port=self.config.device,
            baudrate=self.config.baudrate,
            bytesize=bytesize_map[self.config.data_bits],
            parity=parity_map[self.config.parity],
            stopbits=stopbits_map[self.config.stop_bits],
            timeout=max(self.config.timeout_ms / 1000.0, 0.05),
            write_timeout=max(self.config.write_timeout_ms / 1000.0, 0.05),
            xonxoff=flow == "XON/XOFF",
            rtscts=flow == "RTS/CTS",
            dsrdtr=flow == "DSR/DTR",
        )

        self.worker = SerialWorker(self.connection)
        self.worker.data_received.connect(self.on_data_received)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
        self.state_changed.emit(self.config.port_no, True, f"{self.config.device} connected")
        self.log_message.emit(
            f"Logical Port #{self.config.port_no} connected to {self.config.device} "
            f"({self.config.baudrate}, {self.config.data_bits}{self.config.parity[0] if self.config.parity else 'N'}{self.config.stop_bits})."
        )

    def disconnect(self) -> None:
        if self.worker:
            self.worker.stop()
            self.worker.deleteLater()
            self.worker = None
        if self.connection and self.connection.is_open:
            self.connection.close()
        self.connection = None
        self.state_changed.emit(self.config.port_no, False, f"{self.config.device or 'Unassigned port'} disconnected")

    def is_connected(self) -> bool:
        return bool(self.connection and self.connection.is_open)

    def send_command(self, command: str) -> None:
        if not self.connection or not self.connection.is_open:
            raise RuntimeError(f"Logical Port #{self.config.port_no} is not connected.")

        payload = command.encode(self.config.encoding, errors="replace") + self.line_ending_bytes()
        with self._buffer_lock:
            self._buffer.clear()
        self._data_event.clear()
        self._last_rx_time = 0.0
        self.connection.write(payload)
        self.log_message.emit(f"[TX Port {self.config.port_no}] {command}")

    def wait_for_response(self, timeout_ms: int) -> bytes:
        self._wait_calls += 1
        timeout_s = max(timeout_ms, 0) / 1000.0
        if timeout_s == 0:
            with self._buffer_lock:
                data = bytes(self._buffer)
                self._buffer.clear()
            self._last_wait_bytes = len(data)
            return data

        deadline = time.monotonic() + timeout_s
        first_chunk_arrived = self._data_event.wait(timeout_s)
        if not first_chunk_arrived:
            self._wait_timeouts += 1
            self._last_wait_bytes = 0
            self.log_message.emit(
                f"[RX DEBUG Port {self.config.port_no}] wait_for_response timed out after {timeout_ms} ms with no data event."
            )
            return b""

        quiet_period_s = 0.12
        while time.monotonic() < deadline:
            if time.monotonic() - self._last_rx_time >= quiet_period_s:
                break
            time.sleep(0.02)

        with self._buffer_lock:
            data = bytes(self._buffer)
            self._buffer.clear()
        self._data_event.clear()
        self._last_wait_bytes = len(data)
        self.log_message.emit(
            f"[RX DEBUG Port {self.config.port_no}] wait_for_response collected {len(data)} byte(s)."
        )
        return data

    def line_ending_bytes(self) -> bytes:
        mapping = {
            "None": b"",
            "CR": b"\r",
            "LF": b"\n",
            "CRLF": b"\r\n",
        }
        return mapping.get(self.config.line_ending, b"\r\n")

    def on_data_received(self, data: bytes) -> None:
        with self._buffer_lock:
            self._buffer.extend(data)
            self._last_rx_time = time.monotonic()
            self._rx_chunks += 1
            self._rx_bytes += len(data)
            buffer_size = len(self._buffer)
        self._data_event.set()
        preview_hex = data[:24].hex(" ").upper()
        preview_text = data.decode(self.config.encoding, errors="replace").replace("\r", "\\r").replace("\n", "\\n")
        self.log_message.emit(
            f"[RX DEBUG Port {self.config.port_no}] worker->session chunk={len(data)} total_bytes={self._rx_bytes} "
            f"buffer={buffer_size} hex={preview_hex} text={preview_text[:80]}"
        )
        self.data_received.emit(self.config.port_no, data)

    def on_error(self, error_message: str) -> None:
        self.log_message.emit(f"[ERROR Port {self.config.port_no}] {error_message}")
        self.disconnect()

    def get_debug_snapshot(self) -> dict:
        with self._buffer_lock:
            buffer_size = len(self._buffer)
        return {
            "port_no": self.config.port_no,
            "device": self.config.device,
            "connected": self.is_connected(),
            "rx_chunks": self._rx_chunks,
            "rx_bytes": self._rx_bytes,
            "buffer_size": buffer_size,
            "wait_calls": self._wait_calls,
            "wait_timeouts": self._wait_timeouts,
            "last_wait_bytes": self._last_wait_bytes,
            "last_rx_age_ms": int((time.monotonic() - self._last_rx_time) * 1000) if self._last_rx_time else None,
        }
