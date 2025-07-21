"""
Main Window Module
Main application window for HD2 RS-232C Serial Communicator
"""

import serial.tools.list_ports
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QGroupBox, QMessageBox,
                             QScrollArea)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont
from typing import List

from gui.serial_port_frame import SerialPortFrame


class HD2SerialCommunicator(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.port_frames: List[SerialPortFrame] = []
        self.setup_ui()
        self.setup_timer()
        
    def setup_ui(self):
        """Setup the main user interface"""
        self.setWindowTitle("HD2 GUI RS-232C Serial Communicator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # Header with scan button
        header_layout = QHBoxLayout()
        
        title_label = QLabel("HD2 RS-232C Serial Communicator")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.scan_btn = QPushButton("Scan RS-232C Devices")
        self.scan_btn.clicked.connect(self.scan_ports)
        header_layout.addWidget(self.scan_btn)
        
        main_layout.addLayout(header_layout)
        
        # Scroll area for port frames
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container for port frames
        self.ports_container = QWidget()
        self.ports_layout = QVBoxLayout()
        self.ports_container.setLayout(self.ports_layout)
        
        scroll_area.setWidget(self.ports_container)
        main_layout.addWidget(scroll_area)
        
        central_widget.setLayout(main_layout)
        
        # Create 4 port frames
        self.create_port_frames()
        
        # Initial port scan
        self.scan_ports()
        
    def create_port_frames(self):
        """Create 4 serial port frames"""
        for i in range(4):
            frame = SerialPortFrame(i)
            frame_group = QGroupBox(f"RS-232C Port {i+1}")
            frame_layout = QVBoxLayout()
            frame_layout.addWidget(frame)
            frame_group.setLayout(frame_layout)
            
            self.ports_layout.addWidget(frame_group)
            self.port_frames.append(frame)
            
    def setup_timer(self):
        """Setup timer for periodic port scanning"""
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.scan_ports)
        self.scan_timer.start(5000)  # Scan every 5 seconds
        
    def scan_ports(self):
        """Scan for available RS-232C devices"""
        try:
            # Get list of available serial ports
            ports = serial.tools.list_ports.comports()
            port_names = [port.device for port in ports]
            
            # Update all port frames
            for frame in self.port_frames:
                frame.update_ports(port_names)
                
            # Update scan button text temporarily
            original_text = self.scan_btn.text()
            self.scan_btn.setText(f"Found {len(port_names)} devices")
            
            # Reset button text after 2 seconds
            QTimer.singleShot(2000, lambda: self.scan_btn.setText(original_text))
            
        except Exception as e:
            QMessageBox.critical(self, "Scan Error", f"Failed to scan ports: {str(e)}")
            
    def closeEvent(self, event):
        """Clean up when application is closing"""
        # Disconnect all serial connections
        for frame in self.port_frames:
            frame.disconnect_serial()
            
        # Stop timer
        if hasattr(self, 'scan_timer'):
            self.scan_timer.stop()
            
        event.accept()