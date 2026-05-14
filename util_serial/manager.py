"""
Manager for logical serial sessions.
"""

from __future__ import annotations

from typing import Dict, List

import serial.tools.list_ports
from PySide6.QtCore import QObject, Signal

from util_serial.project_config import SerialPortConfig
from util_serial.session import SerialSession


class SerialPortManager(QObject):
    """Coordinates port configuration and live sessions."""

    log_message = Signal(str)
    data_received = Signal(int, bytes)
    port_state_changed = Signal(int, bool, str)

    def __init__(self):
        super().__init__()
        self._configs: Dict[int, SerialPortConfig] = {}
        self._sessions: Dict[int, SerialSession] = {}
        self._forwarded_rx_counts: Dict[int, int] = {}
        self._forwarded_rx_bytes: Dict[int, int] = {}

    def set_port_configs(self, configs: List[SerialPortConfig]) -> None:
        self.disconnect_all()
        self._configs = {config.port_no: config for config in configs}
        self._forwarded_rx_counts = {config.port_no: 0 for config in configs}
        self._forwarded_rx_bytes = {config.port_no: 0 for config in configs}
        self.log_message.emit(f"Loaded {len(self._configs)} logical port setting(s).")

    def get_port_configs(self) -> List[SerialPortConfig]:
        return [self._configs[key] for key in sorted(self._configs)]

    def scan_available_ports(self) -> List[str]:
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect_all(self) -> None:
        for config in self.get_port_configs():
            if config.enabled and config.device:
                self.ensure_connected(config.port_no)

    def disconnect_all(self) -> None:
        for port_no in list(self._sessions):
            self.disconnect_port(port_no)

    def disconnect_port(self, port_no: int) -> None:
        session = self._sessions.pop(port_no, None)
        if session:
            session.close_session()
            session.deleteLater()

    def ensure_connected(self, port_no: int) -> SerialSession:
        config = self._configs.get(port_no)
        if config is None:
            raise KeyError(f"Logical Port #{port_no} is not defined in Port Settings.")

        session = self._sessions.get(port_no)
        if session and session.is_connected():
            return session

        if session:
            session.deleteLater()

        session = SerialSession(config)
        session.log_message.connect(self.log_message.emit)
        session.data_received.connect(self._handle_session_data_received)
        session.state_changed.connect(self.port_state_changed.emit)
        session.open_session()
        self._sessions[port_no] = session
        return session

    def execute_command(self, port_no: int, command: str, timeout_ms: int) -> bytes:
        session = self.ensure_connected(port_no)
        session.send_command(command)
        return session.wait_for_response(timeout_ms)

    def _handle_session_data_received(self, port_no: int, data: bytes) -> None:
        self._forwarded_rx_counts[port_no] = self._forwarded_rx_counts.get(port_no, 0) + 1
        self._forwarded_rx_bytes[port_no] = self._forwarded_rx_bytes.get(port_no, 0) + len(data)
        self.log_message.emit(
            f"[RX DEBUG Port {port_no}] manager forwarded chunk={len(data)} "
            f"total_chunks={self._forwarded_rx_counts[port_no]} total_bytes={self._forwarded_rx_bytes[port_no]}"
        )
        self.data_received.emit(port_no, data)

    def get_rx_debug_snapshot(self) -> List[dict]:
        snapshots: List[dict] = []
        for config in self.get_port_configs():
            port_no = config.port_no
            session = self._sessions.get(port_no)
            session_snapshot = session.get_debug_snapshot() if session else {
                "port_no": port_no,
                "device": config.device,
                "connected": False,
                "rx_chunks": 0,
                "rx_bytes": 0,
                "buffer_size": 0,
                "wait_calls": 0,
                "wait_timeouts": 0,
                "last_wait_bytes": 0,
                "last_rx_age_ms": None,
            }
            session_snapshot["manager_forwarded_chunks"] = self._forwarded_rx_counts.get(port_no, 0)
            session_snapshot["manager_forwarded_bytes"] = self._forwarded_rx_bytes.get(port_no, 0)
            snapshots.append(session_snapshot)
        return snapshots
