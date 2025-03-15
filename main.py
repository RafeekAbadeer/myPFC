import sys
from PyQt5.QtWidgets import QApplication
from gui.general_gui import Application

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Application()
    window.showMaximized()  # Replace the window.show() line with this
    sys.exit(app.exec_())
