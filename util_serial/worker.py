"""
Serial Worker Module
Handles serial communication in a separate thread
"""

from serial import Serial
from PySide6.QtCore import QThread, Signal
from typing import Optional


class SerialWorker(QThread):
    """Worker thread for handling serial communication"""
    
    data_received = Signal(int, str)  # port_index, data
    error_occurred = Signal(int, str)  # port_index, error_message
    
    def __init__(self, port_index: int, serial_connection: Serial):
        super().__init__()
        self.port_index = port_index
        self.serial_connection = serial_connection
        self.running = False
        
    def run(self):
        """Main thread loop for reading serial data"""
        self.running = True
        while self.running and self.serial_connection.is_open:
            try:
                if self.serial_connection.in_waiting > 0:
                    data = self.serial_connection.read(self.serial_connection.in_waiting)
                    decoded_data = data.decode('utf-8', errors='ignore')
                    self.data_received.emit(self.port_index, decoded_data)
                self.msleep(10)  # Small delay to prevent high CPU usage
            except Exception as e:
                self.error_occurred.emit(self.port_index, str(e))
                break
                
    def stop(self):
        """Stop the worker thread"""
        self.running = False
        self.wait()