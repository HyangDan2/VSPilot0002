#!/usr/bin/env python3
"""
HD2 GUI RS-232C Serial Communicator
Main application entry point
"""

import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import HD2SerialCommunicator


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("HD2 Serial Communicator")
    app.setOrganizationName("HD2")
    
    # Create and show main window
    window = HD2SerialCommunicator()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()