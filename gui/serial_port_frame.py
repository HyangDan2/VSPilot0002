"""
Serial Port Frame Module
Individual serial port configuration and communication frame
"""

import serial
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, 
                             QTextEdit, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt
from typing import List, Optional

from serial.worker import SerialWorker


class SerialPortFrame(QFrame):
    """Individual serial port configuration and communication frame"""
    
    def __init__(self, port_index: int, parent=None):
        super().__init__(parent)
        self.port_index = port_index
        self.serial_connection: Optional[serial.Serial] = None
        self.worker: Optional[SerialWorker] = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI for this port frame"""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setLineWidth(2)
        
        layout = QVBoxLayout()
        
        # Port selection and connection
        connection_layout = QHBoxLayout()
        connection_layout.addWidget(QLabel("Port:"))
        
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        connection_layout.addWidget(self.port_combo)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(self.connect_btn)
        
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red;")
        connection_layout.addWidget(self.status_label)
        
        layout.addLayout(connection_layout)
        
        # RS-232C Communication Properties
        props_group = QGroupBox("RS-232C Properties")
        props_layout = QGridLayout()
        
        # Baud Rate
        props_layout.addWidget(QLabel("Baud Rate:"), 0, 0)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("9600")
        props_layout.addWidget(self.baud_combo, 0, 1)
        
        # Data Bits
        props_layout.addWidget(QLabel("Data Bits:"), 0, 2)
        self.data_bits_combo = QComboBox()
        self.data_bits_combo.addItems(["7", "8"])
        self.data_bits_combo.setCurrentText("8")
        props_layout.addWidget(self.data_bits_combo, 0, 3)
        
        # Parity
        props_layout.addWidget(QLabel("Parity:"), 1, 0)
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd"])
        props_layout.addWidget(self.parity_combo, 1, 1)
        
        # Stop Bits
        props_layout.addWidget(QLabel("Stop Bits:"), 1, 2)
        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(["1", "2"])
        props_layout.addWidget(self.stop_bits_combo, 1, 3)
        
        props_group.setLayout(props_layout)
        layout.addWidget(props_group)
        
        # Command Input
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("Command:"))
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter RS-232C command...")
        self.command_input.returnPressed.connect(self.send_command)
        cmd_layout.addWidget(self.command_input)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_command)
        self.send_btn.setEnabled(False)
        cmd_layout.addWidget(self.send_btn)
        
        layout.addLayout(cmd_layout)
        
        # Return Value Display
        self.return_value_text = QTextEdit()
        self.return_value_text.setMaximumHeight(150)
        self.return_value_text.setPlaceholderText("Return values will appear here...")
        self.return_value_text.setReadOnly(True)
        layout.addWidget(QLabel("Return Value:"))
        layout.addWidget(self.return_value_text)
        
        self.setLayout(layout)
        
    def update_ports(self, ports: List[str]):
        """Update available ports in the combo box"""
        current_port = self.port_combo.currentText()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        
        # Try to restore previous selection
        if current_port in ports:
            self.port_combo.setCurrentText(current_port)
            
    def toggle_connection(self):
        """Toggle serial connection"""
        if self.serial_connection and self.serial_connection.is_open:
            self.disconnect_serial()
        else:
            self.connect_serial()
            
    def connect_serial(self):
        """Connect to selected serial port"""
        port = self.port_combo.currentText()
        if not port:
            QMessageBox.warning(self, "Warning", "Please select a port first.")
            return
            
        try:
            # Parse parity
            parity_map = {"None": serial.PARITY_NONE, 
                         "Even": serial.PARITY_EVEN, 
                         "Odd": serial.PARITY_ODD}
            
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=int(self.baud_combo.currentText()),
                bytesize=int(self.data_bits_combo.currentText()),
                parity=parity_map[self.parity_combo.currentText()],
                stopbits=int(self.stop_bits_combo.currentText()),
                timeout=1
            )
            
            # Start worker thread for reading data
            self.worker = SerialWorker(self.port_index, self.serial_connection)
            self.worker.data_received.connect(self.on_data_received)
            self.worker.error_occurred.connect(self.on_error)
            self.worker.start()
            
            self.connect_btn.setText("Disconnect")
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: green;")
            self.send_btn.setEnabled(True)
            
            # Disable property changes when connected
            self.baud_combo.setEnabled(False)
            self.data_bits_combo.setEnabled(False)
            self.parity_combo.setEnabled(False)
            self.stop_bits_combo.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect: {str(e)}")
            
    def disconnect_serial(self):
        """Disconnect from serial port"""
        if self.worker:
            self.worker.stop()
            self.worker = None
            
        if self.serial_connection:
            self.serial_connection.close()
            self.serial_connection = None
            
        self.connect_btn.setText("Connect")
        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet("color: red;")
        self.send_btn.setEnabled(False)
        
        # Re-enable property changes
        self.baud_combo.setEnabled(True)
        self.data_bits_combo.setEnabled(True)
        self.parity_combo.setEnabled(True)
        self.stop_bits_combo.setEnabled(True)
        
    def send_command(self):
        """Send command through serial port"""
        if not self.serial_connection or not self.serial_connection.is_open:
            return
            
        command = self.command_input.text().strip()
        if not command:
            return
            
        try:
            # Add carriage return and line feed if not present
            if not command.endswith(('\r', '\n', '\r\n')):
                command += '\r\n'
                
            self.serial_connection.write(command.encode('utf-8'))
            self.command_input.clear()
            
            # Add sent command to return value display
            self.return_value_text.append(f">>> {command.strip()}")
            
        except Exception as e:
            QMessageBox.critical(self, "Send Error", f"Failed to send command: {str(e)}")
            
    def on_data_received(self, port_index: int, data: str):
        """Handle received data from serial port"""
        if port_index == self.port_index:
            self.return_value_text.append(f"<<< {data.strip()}")
            # Auto-scroll to bottom
            self.return_value_text.verticalScrollBar().setValue(
                self.return_value_text.verticalScrollBar().maximum()
            )
            
    def on_error(self, port_index: int, error_message: str):
        """Handle serial communication errors"""
        if port_index == self.port_index:
            self.return_value_text.append(f"ERROR: {error_message}")
            self.disconnect_serial()
            
    def closeEvent(self, event):
        """Clean up when frame is closed"""
        self.disconnect_serial()
        event.accept()