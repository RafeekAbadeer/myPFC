from PyQt5.QtWidgets import QHeaderView, QTableWidget, QApplication
from PyQt5.QtCore import Qt
import sys

app = QApplication(sys.argv)

# Create a temporary QTableWidget and QHeaderView to access default styles
temp_table = QTableWidget()
temp_header = QHeaderView(Qt.Horizontal, temp_table)

# Print default QHeaderView style sheet (if any)
default_style_sheet = temp_header.styleSheet()
print(f"Default QHeaderView style sheet: {default_style_sheet}")

sys.exit()