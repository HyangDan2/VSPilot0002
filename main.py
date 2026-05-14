#!/usr/bin/env python3
"""
Generic RS232C Communicator V0.01
Main application entry point
"""

import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import GenericRS232CCommunicator


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Generic RS232C Communicator V0.01")
    app.setOrganizationName("Generic RS232C")
    
    # Create and show main window
    window = GenericRS232CCommunicator()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
