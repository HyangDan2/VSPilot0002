"""
Main window for the simplified generic RS232C communicator.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
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

from gui.port_settings_dialog import PortSettingsDialog
from util_serial.executor import CommandExecutor, CommandStep
from util_serial.manager import SerialPortManager
from util_serial.project_config import SerialPortConfig


class ResultDataDialog(QDialog):
    """Read-only popup for full result-cell contents."""

    def __init__(self, title: str, content: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 500)

        layout = QVBoxLayout(self)
        viewer = QPlainTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(content)
        layout.addWidget(viewer)


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
        self.splitter = splitter

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
                next_raw = str(row_data["next_command_no"]).strip()
                steps.append(
                    CommandStep(
                        command_no=int(row_data["command_no"]),
                        port_no=int(row_data["port_no"]),
                        command=command_text,
                        wait_time_ms=0,
                        next_command_no=None,
                        timeout_ms=int(row_data["timeout_ms"] or 1000),
                        memo="",
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
