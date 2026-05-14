#!/usr/bin/env python3
"""
Generic RS232C Communicator V0.01

Single-file integrated version of the current degraded-branch application.
"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import serial
import serial.tools.list_ports
from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


@dataclass
class SerialPortConfig:
    enabled: bool = True
    port_no: int = 1
    alias: str = ""
    device: str = ""
    baudrate: int = 9600
    data_bits: int = 8
    parity: str = "None"
    stop_bits: float = 1.0
    timeout_ms: int = 1000
    write_timeout_ms: int = 1000
    encoding: str = "utf-8"
    line_ending: str = "CRLF"
    flow_control: str = "None"


class SerialWorker(QThread):
    """Continuously reads bytes from an open serial connection."""

    data_received = Signal(bytes)
    error_occurred = Signal(str)

    def __init__(self, serial_connection: serial.Serial):
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


class SerialSession(QObject):
    """Wrap a serial connection plus its background reader."""

    data_received = Signal(int, bytes)
    state_changed = Signal(int, bool, str)

    def __init__(self, config: SerialPortConfig):
        super().__init__()
        self.config = config
        self.connection: Optional[serial.Serial] = None
        self.worker: Optional[SerialWorker] = None
        self._buffer = bytearray()
        self._buffer_lock = threading.Lock()
        self._data_event = threading.Event()
        self._last_rx_time = 0.0

    def open_session(self) -> None:
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

    def close_session(self) -> None:
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

    def wait_for_response(self, timeout_ms: int) -> bytes:
        timeout_s = max(timeout_ms, 0) / 1000.0
        if timeout_s == 0:
            with self._buffer_lock:
                data = bytes(self._buffer)
                self._buffer.clear()
            return data

        deadline = time.monotonic() + timeout_s
        first_chunk_arrived = self._data_event.wait(timeout_s)
        if not first_chunk_arrived:
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
        self._data_event.set()
        self.data_received.emit(self.config.port_no, data)

    def on_error(self, _error_message: str) -> None:
        self.close_session()


class SerialPortManager(QObject):
    """Coordinates port configuration and live sessions."""

    data_received = Signal(int, bytes)
    port_state_changed = Signal(int, bool, str)

    def __init__(self):
        super().__init__()
        self._configs: Dict[int, SerialPortConfig] = {}
        self._sessions: Dict[int, SerialSession] = {}

    def set_port_configs(self, configs: List[SerialPortConfig]) -> None:
        self.disconnect_all()
        self._configs = {config.port_no: config for config in configs}

    def get_port_configs(self) -> List[SerialPortConfig]:
        return [self._configs[key] for key in sorted(self._configs)]

    def scan_available_ports(self) -> List[str]:
        return [port.device for port in serial.tools.list_ports.comports()]

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
        session.data_received.connect(self.data_received.emit)
        session.state_changed.connect(self.port_state_changed.emit)
        session.open_session()
        self._sessions[port_no] = session
        return session

    def execute_command(self, port_no: int, command: str, timeout_ms: int) -> bytes:
        session = self.ensure_connected(port_no)
        session.send_command(command)
        return session.wait_for_response(timeout_ms)


@dataclass
class CommandStep:
    command_no: int
    port_no: int
    command: str
    timeout_ms: int = 1000


class CommandExecutor(QThread):
    """Runs enabled command rows in order on a worker thread."""

    result_ready = Signal(dict)
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

        for current in self.steps:
            if not self._running:
                self.finished_state.emit(False, "Execution stopped by user.")
                return

            started = time.monotonic()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                raw_response = self.manager.execute_command(current.port_no, current.command, current.timeout_ms)
                decoded_response = raw_response.decode("utf-8", errors="replace").strip()
                status = "OK"
                result_data = decoded_response
            except Exception as exc:
                status = "ERROR"
                result_data = str(exc)
                elapsed_ms = int((time.monotonic() - started) * 1000)
                self.result_ready.emit(
                    {
                        "time": timestamp,
                        "command_no": current.command_no,
                        "port_no": current.port_no,
                        "command": current.command,
                        "result_data": result_data,
                        "status": status,
                        "elapsed_ms": elapsed_ms,
                    }
                )
                self.finished_state.emit(False, f"Execution stopped at Command #{current.command_no}: {exc}")
                return

            elapsed_ms = int((time.monotonic() - started) * 1000)
            self.result_ready.emit(
                {
                    "time": timestamp,
                    "command_no": current.command_no,
                    "port_no": current.port_no,
                    "command": current.command,
                    "result_data": result_data,
                    "status": status,
                    "elapsed_ms": elapsed_ms,
                }
            )

        self.finished_state.emit(True, "Execution finished successfully.")


class PortSettingsDialog(QDialog):
    """Editable table for all port settings."""

    COLUMNS = [
        "Enabled",
        "Port #",
        "Alias",
        "Device",
        "Baud",
        "Data Bits",
        "Parity",
        "Stop Bits",
        "Timeout (ms)",
        "Write Timeout (ms)",
        "Encoding",
        "Line Ending",
        "Flow Control",
    ]

    def __init__(self, configs: List[SerialPortConfig], available_ports: List[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.available_ports = available_ports
        self.setWindowTitle("Port Settings")
        self.resize(1200, 520)
        self.setup_ui()

        for config in configs:
            self.add_row(config)
        if self.table.rowCount() == 0:
            self.add_row()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        description = QLabel("Command rows reference logical Port # values defined here.")
        description.setWordWrap(True)
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        add_btn = QPushButton("Add Port")
        add_btn.clicked.connect(self.add_row)
        toolbar.addWidget(add_btn)

        remove_btn = QPushButton("Remove Port")
        remove_btn.clicked.connect(self.remove_selected_rows)
        toolbar.addWidget(remove_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        for column in range(len(self.COLUMNS)):
            mode = QHeaderView.ResizeMode.Stretch if column in (2, 3) else QHeaderView.ResizeMode.ResizeToContents
            header.setSectionResizeMode(column, mode)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_row(self, config: SerialPortConfig | None = None) -> None:
        cfg = config or SerialPortConfig(port_no=self.table.rowCount() + 1)
        row = self.table.rowCount()
        self.table.insertRow(row)

        enabled_item = QTableWidgetItem()
        enabled_item.setFlags(enabled_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        enabled_item.setCheckState(Qt.CheckState.Checked if cfg.enabled else Qt.CheckState.Unchecked)
        self.table.setItem(row, 0, enabled_item)
        self.table.setItem(row, 1, QTableWidgetItem(str(cfg.port_no)))
        self.table.setItem(row, 2, QTableWidgetItem(cfg.alias))

        device_combo = QComboBox()
        device_combo.setEditable(True)
        device_combo.addItem("")
        device_combo.addItems(self.available_ports)
        device_combo.setCurrentText(cfg.device)
        self.table.setCellWidget(row, 3, device_combo)

        baud_combo = QComboBox()
        baud_combo.setEditable(True)
        baud_combo.addItems(["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])
        baud_combo.setCurrentText(str(cfg.baudrate))
        self.table.setCellWidget(row, 4, baud_combo)

        data_bits_combo = QComboBox()
        data_bits_combo.addItems(["5", "6", "7", "8"])
        data_bits_combo.setCurrentText(str(cfg.data_bits))
        self.table.setCellWidget(row, 5, data_bits_combo)

        parity_combo = QComboBox()
        parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"])
        parity_combo.setCurrentText(cfg.parity)
        self.table.setCellWidget(row, 6, parity_combo)

        stop_bits_combo = QComboBox()
        stop_bits_combo.addItems(["1", "1.5", "2"])
        stop_bits_combo.setCurrentText(str(cfg.stop_bits))
        self.table.setCellWidget(row, 7, stop_bits_combo)

        self.table.setItem(row, 8, QTableWidgetItem(str(cfg.timeout_ms)))
        self.table.setItem(row, 9, QTableWidgetItem(str(cfg.write_timeout_ms)))

        encoding_combo = QComboBox()
        encoding_combo.setEditable(True)
        encoding_combo.addItems(["utf-8", "ascii", "latin-1"])
        encoding_combo.setCurrentText(cfg.encoding)
        self.table.setCellWidget(row, 10, encoding_combo)

        line_ending_combo = QComboBox()
        line_ending_combo.addItems(["None", "CR", "LF", "CRLF"])
        line_ending_combo.setCurrentText(cfg.line_ending)
        self.table.setCellWidget(row, 11, line_ending_combo)

        flow_control_combo = QComboBox()
        flow_control_combo.addItems(["None", "XON/XOFF", "RTS/CTS", "DSR/DTR"])
        flow_control_combo.setCurrentText(cfg.flow_control)
        self.table.setCellWidget(row, 12, flow_control_combo)

    def remove_selected_rows(self) -> None:
        rows = sorted((index.row() for index in self.table.selectionModel().selectedRows()), reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def get_configs(self) -> List[SerialPortConfig]:
        configs: List[SerialPortConfig] = []
        for row in range(self.table.rowCount()):
            try:
                enabled_item = self.table.item(row, 0)
                port_no_item = self.table.item(row, 1)
                alias_item = self.table.item(row, 2)
                timeout_item = self.table.item(row, 8)
                write_timeout_item = self.table.item(row, 9)

                config = SerialPortConfig(
                    enabled=enabled_item.checkState() == Qt.CheckState.Checked if enabled_item else True,
                    port_no=int(port_no_item.text().strip()) if port_no_item else row + 1,
                    alias=alias_item.text().strip() if alias_item else "",
                    device=self.combo_text(row, 3),
                    baudrate=int(self.combo_text(row, 4) or "9600"),
                    data_bits=int(self.combo_text(row, 5) or "8"),
                    parity=self.combo_text(row, 6) or "None",
                    stop_bits=float(self.combo_text(row, 7) or "1"),
                    timeout_ms=int(timeout_item.text().strip()) if timeout_item and timeout_item.text().strip() else 1000,
                    write_timeout_ms=int(write_timeout_item.text().strip()) if write_timeout_item and write_timeout_item.text().strip() else 1000,
                    encoding=self.combo_text(row, 10) or "utf-8",
                    line_ending=self.combo_text(row, 11) or "CRLF",
                    flow_control=self.combo_text(row, 12) or "None",
                )
            except ValueError as exc:
                raise ValueError(f"Invalid port settings in row {row + 1}: {exc}") from exc
            configs.append(config)
        return configs

    def combo_text(self, row: int, column: int) -> str:
        combo = self.table.cellWidget(row, column)
        return combo.currentText().strip() if isinstance(combo, QComboBox) else ""

    def accept(self) -> None:
        try:
            configs = self.get_configs()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Port Settings", str(exc))
            return

        port_numbers = [config.port_no for config in configs]
        if len(set(port_numbers)) != len(port_numbers):
            QMessageBox.warning(self, "Invalid Port Settings", "Logical Port # values must be unique.")
            return

        super().accept()


class GenericRS232CCommunicator(QMainWindow):
    """Minimal command/result communicator UI."""

    COMMAND_COLUMNS = [
        "Enable",
        "Command #",
        "Port #",
        "Command",
        "Timeout (ms)",
    ]
    RESULT_COLUMNS = [
        "Time",
        "Command #",
        "Port #",
        "Command",
        "Result Data",
        "Status",
        "Elapsed (ms)",
    ]
    RESULT_DATA_COLUMN = 4

    def __init__(self):
        super().__init__()
        self.port_manager = SerialPortManager()
        self.executor_thread: Optional[CommandExecutor] = None

        self.setup_ui()
        self.apply_default_config()

    def setup_ui(self) -> None:
        self.setWindowTitle("Generic RS232C Communicator V0.01")
        self.resize(1600, 900)

        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)

        top_bar = QHBoxLayout()
        run_btn = QPushButton("Run All")
        run_btn.clicked.connect(self.run_all_commands)
        top_bar.addWidget(run_btn)

        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self.stop_executor)
        top_bar.addWidget(stop_btn)

        port_settings_btn = QPushButton("Port Settings")
        port_settings_btn.clicked.connect(self.open_port_settings)
        top_bar.addWidget(port_settings_btn)

        top_bar.addStretch()
        central_layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self.build_command_panel())
        splitter.addWidget(self.build_result_panel())
        splitter.setSizes([800, 800])

        central_layout.addWidget(splitter)
        self.setCentralWidget(central_widget)

    def build_command_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        title = QLabel("Command Window")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        add_btn = QPushButton("Add Row")
        add_btn.clicked.connect(self.add_command_row)
        toolbar.addWidget(add_btn)

        remove_btn = QPushButton("Remove Row")
        remove_btn.clicked.connect(self.remove_selected_command_rows)
        toolbar.addWidget(remove_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.command_table = QTableWidget(0, len(self.COMMAND_COLUMNS))
        self.command_table.setHorizontalHeaderLabels(self.COMMAND_COLUMNS)
        self.command_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.command_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.command_table.setAlternatingRowColors(True)
        self.command_table.verticalHeader().setVisible(False)
        header = self.command_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.command_table)

        return widget

    def build_result_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        title = QLabel("Result View")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_results)
        toolbar.addWidget(export_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.result_table = QTableWidget(0, len(self.RESULT_COLUMNS))
        self.result_table.setHorizontalHeaderLabels(self.RESULT_COLUMNS)
        self.result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.cellDoubleClicked.connect(self.open_result_data_dialog)
        result_header = self.result_table.horizontalHeader()
        result_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        result_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        result_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        result_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        result_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        result_header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        result_header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.result_table.setColumnWidth(3, 220)
        layout.addWidget(self.result_table)

        return widget

    def apply_default_config(self) -> None:
        self.port_manager.set_port_configs([SerialPortConfig(port_no=1)])
        self.add_command_row()

    def add_command_row(self, row_data: Optional[Dict[str, Any]] = None) -> None:
        row = self.command_table.rowCount()
        self.command_table.insertRow(row)
        values = row_data or {}

        enabled_item = QTableWidgetItem()
        enabled_item.setFlags(enabled_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        enabled_item.setCheckState(Qt.CheckState.Checked if values.get("enabled", True) else Qt.CheckState.Unchecked)
        self.command_table.setItem(row, 0, enabled_item)

        defaults = [
            str(values.get("command_no", row + 1)),
            str(values.get("port_no", 1)),
            values.get("command", ""),
            str(values.get("timeout_ms", 1000)),
        ]
        for column_offset, value in enumerate(defaults, start=1):
            self.command_table.setItem(row, column_offset, QTableWidgetItem(value))

    def remove_selected_command_rows(self) -> None:
        rows = sorted((index.row() for index in self.command_table.selectionModel().selectedRows()), reverse=True)
        for row in rows:
            self.command_table.removeRow(row)

    def command_row_to_dict(self, row: int) -> Dict[str, Any]:
        enabled_item = self.command_table.item(row, 0)
        return {
            "enabled": enabled_item.checkState() == Qt.CheckState.Checked if enabled_item else True,
            "command_no": self.table_text(row, 1),
            "port_no": self.table_text(row, 2),
            "command": self.table_text(row, 3),
            "timeout_ms": self.table_text(row, 4),
        }

    def table_text(self, row: int, column: int) -> str:
        item = self.command_table.item(row, column)
        return item.text().strip() if item else ""

    def collect_command_steps(self) -> List[CommandStep]:
        steps: List[CommandStep] = []
        for row in range(self.command_table.rowCount()):
            try:
                row_data = self.command_row_to_dict(row)
                if not row_data["enabled"]:
                    continue
                command_text = str(row_data["command"]).strip()
                if not command_text:
                    continue
                steps.append(
                    CommandStep(
                        command_no=int(row_data["command_no"]),
                        port_no=int(row_data["port_no"]),
                        command=command_text,
                        timeout_ms=int(row_data["timeout_ms"] or 1000),
                    )
                )
            except ValueError as exc:
                raise ValueError(f"Invalid numeric value in command row {row + 1}: {exc}") from exc
        return steps

    def open_port_settings(self) -> None:
        dialog = PortSettingsDialog(
            self.port_manager.get_port_configs(),
            self.port_manager.scan_available_ports(),
            self,
        )
        if dialog.exec():
            self.port_manager.set_port_configs(dialog.get_configs())

    def run_all_commands(self) -> None:
        try:
            steps = self.collect_command_steps()
        except ValueError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return

        if not steps:
            QMessageBox.information(self, "Run All", "There are no enabled command rows to run.")
            return
        if self.executor_thread and self.executor_thread.isRunning():
            QMessageBox.warning(self, "Run All", "A command run is already in progress.")
            return

        self.executor_thread = CommandExecutor(steps, self.port_manager)
        self.executor_thread.result_ready.connect(self.append_result_row)
        self.executor_thread.finished_state.connect(self.on_executor_finished)
        self.executor_thread.start()

    def stop_executor(self) -> None:
        if self.executor_thread and self.executor_thread.isRunning():
            self.executor_thread.stop()
            self.executor_thread.wait()
        self.executor_thread = None

    def append_result_row(self, result: Dict[str, Any]) -> None:
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        values = [
            str(result.get("time", "")),
            str(result.get("command_no", "")),
            str(result.get("port_no", "")),
            str(result.get("command", "")),
            str(result.get("result_data", "")),
            str(result.get("status", "")),
            str(result.get("elapsed_ms", "")),
        ]
        for column, value in enumerate(values):
            self.result_table.setItem(row, column, QTableWidgetItem(value))
        self.result_table.scrollToBottom()

    def export_results(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Results",
            "results.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return

        try:
            lines = [",".join(self.RESULT_COLUMNS)]
            for row in range(self.result_table.rowCount()):
                values = []
                for column in range(self.result_table.columnCount()):
                    item = self.result_table.item(row, column)
                    text = item.text() if item else ""
                    values.append(f'"{text.replace(chr(34), chr(34) * 2)}"')
                lines.append(",".join(values))
            with open(file_path, "w", encoding="utf-8") as export_file:
                export_file.write("\n".join(lines))
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", f"Failed to export results:\n{exc}")

    def on_executor_finished(self, success: bool, message: str) -> None:
        if self.executor_thread:
            self.executor_thread.deleteLater()
        self.executor_thread = None
        if not success:
            QMessageBox.warning(self, "Execution Finished", message)

    def open_result_data_dialog(self, row: int, column: int) -> None:
        if column != self.RESULT_DATA_COLUMN:
            return
        item = self.result_table.item(row, column)
        if item is None:
            return

        command_item = self.result_table.item(row, 1)
        port_item = self.result_table.item(row, 2)
        title = "Result Data Detail"
        if command_item and port_item:
            title = f"Result Data - Command #{command_item.text()} / Port #{port_item.text()}"

        dialog = ResultDataDialog(title, item.text(), self)
        dialog.exec()

    def closeEvent(self, event) -> None:
        self.stop_executor()
        self.port_manager.disconnect_all()
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Generic RS232C Communicator V0.01")
    app.setOrganizationName("Generic RS232C")

    window = GenericRS232CCommunicator()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
