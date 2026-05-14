"""
Dialog for menu-driven logical port configuration.
"""

from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from util_serial.project_config import SerialPortConfig


class PortSettingsDialog(QDialog):
    """Editable table for all port settings from the menu bar."""

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

        description = QLabel(
            "All serial-port behavior lives here. Command rows only reference logical Port # values."
        )
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
