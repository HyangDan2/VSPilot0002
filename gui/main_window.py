"""
Main window for the spreadsheet-style RS-232C workflow.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
)

from gui.port_settings_dialog import PortSettingsDialog
from util_serial.executor import CommandExecutor, CommandStep
from util_serial.manager import SerialPortManager
from util_serial.project_config import ProjectConfig, SerialPortConfig


class HD2SerialCommunicator(QMainWindow):
    """Spreadsheet-style main application window."""

    COMMAND_COLUMNS = [
        "Enable",
        "Command #",
        "Port #",
        "Command",
        "Wait Time (ms)",
        "Next Command #",
        "Timeout (ms)",
        "Memo",
    ]
    RESULT_COLUMNS = [
        "Time",
        "Command #",
        "Port #",
        "Result Data",
        "Status",
        "Elapsed (ms)",
    ]

    def __init__(self):
        super().__init__()
        self.current_project_path: Optional[Path] = None
        self.project_config = ProjectConfig.default()
        self.port_manager = SerialPortManager()
        self.executor_thread: Optional[CommandExecutor] = None
        self._ui_rx_counts: Dict[int, int] = {}
        self._ui_rx_bytes: Dict[int, int] = {}

        self.setup_ui()
        self.setup_menus()
        self.setup_manager_connections()
        self.apply_project_config(self.project_config)

    def setup_ui(self) -> None:
        """Build the horizontal 60:20:20 workspace."""
        self.setWindowTitle("HD2 RS-232C Command Studio")
        self.resize(1600, 900)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.splitter = splitter

        self.command_panel = self.build_command_panel()
        self.result_panel = self.build_result_panel()
        self.log_panel = self.build_log_panel()

        splitter.addWidget(self.command_panel)
        splitter.addWidget(self.result_panel)
        splitter.addWidget(self.log_panel)
        splitter.setSizes([960, 320, 320])

        self.setCentralWidget(splitter)

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

        duplicate_btn = QPushButton("Duplicate Row")
        duplicate_btn.clicked.connect(self.duplicate_selected_command_row)
        toolbar.addWidget(duplicate_btn)

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
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.command_table)

        return widget

    def build_result_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        title = QLabel("Result View")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        self.result_table = QTableWidget(0, len(self.RESULT_COLUMNS))
        self.result_table.setHorizontalHeaderLabels(self.RESULT_COLUMNS)
        self.result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.verticalHeader().setVisible(False)
        result_header = self.result_table.horizontalHeader()
        result_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        result_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        result_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        result_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        result_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        result_header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.result_table)

        return widget

    def build_log_panel(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        title = QLabel("Status Terminal Log")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_terminal)
        toolbar.addWidget(clear_btn)

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_terminal_log)
        toolbar.addWidget(export_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.log_terminal = QPlainTextEdit()
        self.log_terminal.setReadOnly(True)
        layout.addWidget(self.log_terminal)

        return widget

    def setup_menus(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        self.add_menu_action(file_menu, "New Project", self.new_project)
        self.add_menu_action(file_menu, "Open Project...", self.open_project)
        self.add_menu_action(file_menu, "Save Project", self.save_project)
        self.add_menu_action(file_menu, "Save Project As...", self.save_project_as)
        file_menu.addSeparator()
        self.add_menu_action(file_menu, "Export Result Table...", self.export_results)
        self.add_menu_action(file_menu, "Export Terminal Log...", self.export_terminal_log)
        file_menu.addSeparator()
        self.add_menu_action(file_menu, "Exit", self.close)

        port_menu = menu_bar.addMenu("Port Settings")
        self.add_menu_action(port_menu, "Configure Ports...", self.open_port_settings)
        port_menu.addSeparator()
        self.add_menu_action(port_menu, "Scan Available Ports", self.scan_ports)
        self.add_menu_action(port_menu, "Connect All", self.connect_all_ports)
        self.add_menu_action(port_menu, "Disconnect All", self.disconnect_all_ports)
        self.add_menu_action(port_menu, "Reconnect Ports", self.reconnect_ports)

        run_menu = menu_bar.addMenu("Run")
        self.add_menu_action(run_menu, "Run All", self.run_all_commands)
        self.add_menu_action(run_menu, "Run Selected", self.run_selected_commands)
        self.add_menu_action(run_menu, "Run From Current Row", self.run_from_current_row)
        run_menu.addSeparator()
        self.add_menu_action(run_menu, "Stop", self.stop_executor)

        view_menu = menu_bar.addMenu("View")
        self.add_menu_action(view_menu, "Reset 60:20:20 Layout", self.reset_layout)
        self.add_menu_action(view_menu, "Reset Table Widths", self.reset_table_widths)

        tools_menu = menu_bar.addMenu("Tools")
        self.add_menu_action(tools_menu, "Validate Command Links", self.validate_command_links)
        self.add_menu_action(tools_menu, "Show RX Debug Snapshot", self.show_rx_debug_snapshot)
        self.add_menu_action(tools_menu, "Clear Results", self.clear_results)
        self.add_menu_action(tools_menu, "Clear Terminal", self.clear_terminal)

        help_menu = menu_bar.addMenu("Help")
        self.add_menu_action(help_menu, "About", self.show_about)

        quick_bar = QToolBar("Quick Actions", self)
        quick_bar.setMovable(False)
        self.addToolBar(quick_bar)
        quick_bar.addAction(self.make_action("Run All", self.run_all_commands))
        quick_bar.addAction(self.make_action("Stop", self.stop_executor))
        quick_bar.addSeparator()
        quick_bar.addAction(self.make_action("Port Settings", self.open_port_settings))

    def setup_manager_connections(self) -> None:
        self.port_manager.log_message.connect(self.append_log_message)
        self.port_manager.data_received.connect(self.on_port_data_received)
        self.port_manager.port_state_changed.connect(self.on_port_state_changed)

    def add_menu_action(self, menu: QMenu, text: str, handler) -> QAction:
        action = self.make_action(text, handler)
        menu.addAction(action)
        return action

    def make_action(self, text: str, handler) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(handler)
        return action

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
            str(values.get("wait_time_ms", 0)),
            "" if values.get("next_command_no") in (None, "") else str(values.get("next_command_no")),
            str(values.get("timeout_ms", 1000)),
            values.get("memo", ""),
        ]
        for column_offset, value in enumerate(defaults, start=1):
            self.command_table.setItem(row, column_offset, QTableWidgetItem(value))

    def duplicate_selected_command_row(self) -> None:
        selected = self.command_table.selectionModel().selectedRows()
        if not selected:
            return
        source_row = selected[-1].row()
        self.add_command_row(self.command_row_to_dict(source_row))

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
            "wait_time_ms": self.table_text(row, 4),
            "next_command_no": self.table_text(row, 5),
            "timeout_ms": self.table_text(row, 6),
            "memo": self.table_text(row, 7),
        }

    def table_text(self, row: int, column: int) -> str:
        item = self.command_table.item(row, column)
        return item.text().strip() if item else ""

    def collect_command_steps(self, selected_rows: Optional[List[int]] = None) -> List[CommandStep]:
        rows = selected_rows if selected_rows is not None else list(range(self.command_table.rowCount()))
        steps: List[CommandStep] = []

        for row in rows:
            try:
                row_data = self.command_row_to_dict(row)
                if not row_data["enabled"]:
                    continue

                command_text = str(row_data["command"]).strip()
                if not command_text:
                    continue

                next_raw = str(row_data["next_command_no"]).strip()
                steps.append(
                    CommandStep(
                        command_no=int(row_data["command_no"]),
                        port_no=int(row_data["port_no"]),
                        command=command_text,
                        wait_time_ms=int(row_data["wait_time_ms"] or 0),
                        next_command_no=int(next_raw) if next_raw else None,
                        timeout_ms=int(row_data["timeout_ms"] or 1000),
                        memo=str(row_data["memo"]),
                    )
                )
            except ValueError as exc:
                raise ValueError(f"Invalid numeric value in command row {row + 1}: {exc}") from exc

        return steps

    def apply_project_config(self, config: ProjectConfig) -> None:
        self.project_config = config
        self.port_manager.set_port_configs(config.ports)
        self._ui_rx_counts = {port.port_no: 0 for port in config.ports}
        self._ui_rx_bytes = {port.port_no: 0 for port in config.ports}

        self.command_table.setRowCount(0)
        for row in config.commands:
            self.add_command_row(row)

        if self.command_table.rowCount() == 0:
            self.add_command_row()

        self.result_table.setRowCount(0)
        self.clear_terminal()

        ui = config.ui
        width = int(ui.get("width", 1600))
        height = int(ui.get("height", 900))
        self.resize(width, height)
        splitter_sizes = ui.get("splitter_sizes", [960, 320, 320])
        if isinstance(splitter_sizes, list) and len(splitter_sizes) == 3:
            QTimer.singleShot(0, lambda: self.splitter.setSizes([int(size) for size in splitter_sizes]))

    def build_project_config(self) -> ProjectConfig:
        commands = [self.command_row_to_dict(row) for row in range(self.command_table.rowCount())]
        ui = {
            "width": self.width(),
            "height": self.height(),
            "splitter_sizes": self.splitter.sizes(),
        }
        return ProjectConfig(ui=ui, ports=self.port_manager.get_port_configs(), commands=commands)

    def new_project(self) -> None:
        self.stop_executor()
        self.disconnect_all_ports()
        self.current_project_path = None
        self.apply_project_config(ProjectConfig.default())
        self.append_log_message("Created a new empty project.")

    def open_project(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            str(Path.cwd()),
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return

        try:
            config = ProjectConfig.load(Path(file_path))
        except Exception as exc:
            QMessageBox.critical(self, "Open Error", f"Failed to open project:\n{exc}")
            return

        self.stop_executor()
        self.disconnect_all_ports()
        self.current_project_path = Path(file_path)
        self.apply_project_config(config)
        self.append_log_message(f"Loaded project: {self.current_project_path}")

    def save_project(self) -> None:
        if self.current_project_path is None:
            self.save_project_as()
            return
        self.write_project(self.current_project_path)

    def save_project_as(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            str(Path.cwd() / "rs232_project.json"),
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return
        self.current_project_path = Path(file_path)
        self.write_project(self.current_project_path)

    def write_project(self, path: Path) -> None:
        try:
            config = self.build_project_config()
            config.save(path)
            self.project_config = config
            self.append_log_message(f"Saved project: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Failed to save project:\n{exc}")

    def open_port_settings(self) -> None:
        dialog = PortSettingsDialog(self.port_manager.get_port_configs(), self.port_manager.scan_available_ports(), self)
        if dialog.exec():
            self.port_manager.set_port_configs(dialog.get_configs())
            self.append_log_message("Updated logical port settings from Port Settings menu.")

    def scan_ports(self) -> None:
        ports = self.port_manager.scan_available_ports()
        port_list = ", ".join(ports) if ports else "No ports found"
        self.append_log_message(f"Scan complete: {port_list}")

    def connect_all_ports(self) -> None:
        try:
            self.port_manager.connect_all()
        except Exception as exc:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect ports:\n{exc}")

    def disconnect_all_ports(self) -> None:
        self.port_manager.disconnect_all()

    def reconnect_ports(self) -> None:
        self.disconnect_all_ports()
        self.connect_all_ports()

    def run_all_commands(self) -> None:
        try:
            steps = self.collect_command_steps()
        except ValueError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return
        self.start_executor(steps, "Run All")

    def run_selected_commands(self) -> None:
        selected_rows = [index.row() for index in self.command_table.selectionModel().selectedRows()]
        if not selected_rows:
            QMessageBox.information(self, "Run Selected", "Select one or more command rows first.")
            return
        try:
            steps = self.collect_command_steps(selected_rows)
        except ValueError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return
        self.start_executor(steps, "Run Selected")

    def run_from_current_row(self) -> None:
        current_row = self.command_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Run From Current Row", "Select a command row first.")
            return
        try:
            steps = self.collect_command_steps(list(range(current_row, self.command_table.rowCount())))
        except ValueError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return
        self.start_executor(steps, f"Run From Row {current_row + 1}")

    def start_executor(self, steps: List[CommandStep], label: str) -> None:
        if not steps:
            QMessageBox.information(self, label, "There are no enabled command rows to run.")
            return
        if self.executor_thread and self.executor_thread.isRunning():
            QMessageBox.warning(self, label, "A command run is already in progress.")
            return

        self.executor_thread = CommandExecutor(steps, self.port_manager)
        self.executor_thread.result_ready.connect(self.append_result_row)
        self.executor_thread.log_message.connect(self.append_log_message)
        self.executor_thread.finished_state.connect(self.on_executor_finished)
        self.executor_thread.start()
        self.append_log_message(f"{label} started with {len(steps)} command(s).")

    def stop_executor(self) -> None:
        if self.executor_thread and self.executor_thread.isRunning():
            self.executor_thread.stop()
            self.executor_thread.wait()
            self.append_log_message("Command execution stopped by user.")
        self.executor_thread = None

    def append_result_row(self, result: Dict[str, Any]) -> None:
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        values = [
            str(result.get("time", "")),
            str(result.get("command_no", "")),
            str(result.get("port_no", "")),
            str(result.get("result_data", "")),
            str(result.get("status", "")),
            str(result.get("elapsed_ms", "")),
        ]
        for column, value in enumerate(values):
            self.result_table.setItem(row, column, QTableWidgetItem(value))
        self.result_table.scrollToBottom()

    def append_log_message(self, message: str) -> None:
        self.log_terminal.appendPlainText(message)
        self.log_terminal.verticalScrollBar().setValue(self.log_terminal.verticalScrollBar().maximum())

    def on_port_data_received(self, port_no: int, data: bytes) -> None:
        self._ui_rx_counts[port_no] = self._ui_rx_counts.get(port_no, 0) + 1
        self._ui_rx_bytes[port_no] = self._ui_rx_bytes.get(port_no, 0) + len(data)
        self.append_log_message(
            f"[RX DEBUG Port {port_no}] UI received chunk={len(data)} "
            f"total_chunks={self._ui_rx_counts[port_no]} total_bytes={self._ui_rx_bytes[port_no]}"
        )
        preview = data.decode("utf-8", errors="replace").strip()
        if preview:
            self.append_log_message(f"[RX Port {port_no}] {preview}")

    def on_port_state_changed(self, port_no: int, connected: bool, message: str) -> None:
        state = "CONNECTED" if connected else "DISCONNECTED"
        self.append_log_message(f"[Port {port_no} {state}] {message}")

    def on_executor_finished(self, success: bool, message: str) -> None:
        self.append_log_message(message)
        if self.executor_thread:
            self.executor_thread.deleteLater()
        self.executor_thread = None
        if not success:
            QMessageBox.warning(self, "Execution Finished", message)

    def export_results(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Results",
            str(Path.cwd() / "results.csv"),
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return

        lines = [",".join(self.RESULT_COLUMNS)]
        for row in range(self.result_table.rowCount()):
            values = []
            for column in range(self.result_table.columnCount()):
                item = self.result_table.item(row, column)
                text = item.text() if item else ""
                values.append(f'"{text.replace(chr(34), chr(34) * 2)}"')
            lines.append(",".join(values))
        Path(file_path).write_text("\n".join(lines), encoding="utf-8")
        self.append_log_message(f"Exported results to {file_path}")

    def export_terminal_log(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Terminal Log",
            str(Path.cwd() / "terminal.log"),
            "Log Files (*.log *.txt);;All Files (*)",
        )
        if not file_path:
            return
        Path(file_path).write_text(self.log_terminal.toPlainText(), encoding="utf-8")
        self.append_log_message(f"Exported terminal log to {file_path}")

    def clear_results(self) -> None:
        self.result_table.setRowCount(0)
        self.append_log_message("Cleared result view.")

    def clear_terminal(self) -> None:
        self.log_terminal.clear()

    def reset_layout(self) -> None:
        self.splitter.setSizes([960, 320, 320])
        self.append_log_message("Restored horizontal 60:20:20 layout.")

    def reset_table_widths(self) -> None:
        self.command_table.resizeColumnsToContents()
        self.result_table.resizeColumnsToContents()
        self.append_log_message("Reset table widths.")

    def validate_command_links(self) -> None:
        try:
            steps = self.collect_command_steps()
        except ValueError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return

        command_numbers = {step.command_no for step in steps}
        invalid = [step.command_no for step in steps if step.next_command_no is not None and step.next_command_no not in command_numbers]
        if invalid:
            QMessageBox.warning(
                self,
                "Command Validation",
                "Invalid Next Command # found in command(s): " + ", ".join(str(value) for value in invalid),
            )
            return
        QMessageBox.information(self, "Command Validation", "All enabled command links are valid.")

    def show_rx_debug_snapshot(self) -> None:
        snapshots = self.port_manager.get_rx_debug_snapshot()
        if not snapshots:
            QMessageBox.information(self, "RX Debug Snapshot", "No logical ports are configured.")
            return

        lines = []
        for snapshot in snapshots:
            port_no = snapshot["port_no"]
            lines.append(
                " | ".join(
                    [
                        f"Port #{port_no}",
                        f"device={snapshot['device'] or '-'}",
                        f"connected={snapshot['connected']}",
                        f"session_rx_chunks={snapshot['rx_chunks']}",
                        f"session_rx_bytes={snapshot['rx_bytes']}",
                        f"manager_chunks={snapshot['manager_forwarded_chunks']}",
                        f"manager_bytes={snapshot['manager_forwarded_bytes']}",
                        f"ui_chunks={self._ui_rx_counts.get(port_no, 0)}",
                        f"ui_bytes={self._ui_rx_bytes.get(port_no, 0)}",
                        f"buffer={snapshot['buffer_size']}",
                        f"wait_calls={snapshot['wait_calls']}",
                        f"wait_timeouts={snapshot['wait_timeouts']}",
                        f"last_wait_bytes={snapshot['last_wait_bytes']}",
                        f"last_rx_age_ms={snapshot['last_rx_age_ms']}",
                    ]
                )
            )

        message = "\n".join(lines)
        self.append_log_message("[RX DEBUG SNAPSHOT]")
        for line in lines:
            self.append_log_message(line)
        QMessageBox.information(self, "RX Debug Snapshot", message)

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            "HD2 RS-232C Command Studio\n\n"
            "Spreadsheet-style command sequencing with menu-driven port settings,\n"
            "structured result capture, and live terminal logging.",
        )

    def closeEvent(self, event) -> None:
        self.stop_executor()
        self.disconnect_all_ports()
        event.accept()
