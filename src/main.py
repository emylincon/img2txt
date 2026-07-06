"""IMG2TXT application entry point."""

import sys

from PyQt6.QtWidgets import QApplication, QMainWindow


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IMG2TXT")
        self.setMinimumSize(800, 600)


def main() -> None:
    """Launch the IMG2TXT application."""
    app = QApplication(sys.argv)
    app.setApplicationName("IMG2TXT")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
