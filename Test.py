from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeView, QTableView, QWidget, QVBoxLayout, QToolBar, QSplitter
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtCore import Qt, QSize
import sys


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mailbox View Example")
        self.setGeometry(300, 100, 800, 600)

        # Create the main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left Frame: TreeView
        left_frame = QWidget()
        left_layout = QVBoxLayout(left_frame)

        # TreeView Widget
        self.tree_view = QTreeView()
        left_layout.addWidget(self.tree_view)
        splitter.addWidget(left_frame)

        # Right Frame: Split into upper and lower frames
        right_frame = QWidget()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setSpacing(0)  # Reduce the distance between frames

        # Upper Frame: Icon Bar
        upper_frame = QWidget()
        upper_layout = QVBoxLayout(upper_frame)
        upper_layout.setSpacing(0)

        # Create a toolbar for the icons
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.addAction(QIcon("path/to/add_icon.png"), "Add")
        toolbar.addAction(QIcon("path/to/edit_icon.png"), "Edit")
        toolbar.addAction(QIcon("path/to/delete_icon.png"), "Delete")
        toolbar.addAction(QIcon("path/to/filter_icon.png"), "Filter")
        upper_layout.addWidget(toolbar)
        right_layout.addWidget(upper_frame)

        # Lower Frame: TableView
        lower_frame = QWidget()
        lower_layout = QVBoxLayout(lower_frame)
        lower_layout.setSpacing(0)

        self.table_view = QTableView()
        lower_layout.addWidget(self.table_view)
        right_layout.addWidget(lower_frame)

        splitter.addWidget(right_frame)
        splitter.setStretchFactor(0, 1)  # Set stretch factor for the left frame
        splitter.setStretchFactor(1, 4)  # Set stretch factor for the right frame

        self.setCentralWidget(splitter)

        # Set up the custom model for the TreeView
        tree_model = QStandardItemModel()
        tree_model.setHorizontalHeaderLabels(["Mailbox Items"])

        parent1 = QStandardItem("Parent 1")
        child1 = QStandardItem("Child 1.1")
        child2 = QStandardItem("Child 1.2")
        parent1.appendRow(child1)
        parent1.appendRow(child2)

        parent2 = QStandardItem("Parent 2")
        child3 = QStandardItem("Child 2.1")
        child4 = QStandardItem("Child 2.2")
        parent2.appendRow(child3)
        parent2.appendRow(child4)

        tree_model.appendRow(parent1)
        tree_model.appendRow(parent2)

        self.tree_view.setModel(tree_model)
        self.tree_view.expandAll()
        self.tree_view.setHeaderHidden(True)

        # Set up the table model for the TableView
        table_model = QStandardItemModel()
        table_model.setHorizontalHeaderLabels(["Column 1", "Column 2", "Column 3"])

        for i in range(5):
            row = [QStandardItem(f"Item {i + 1}-{j + 1}") for j in range(3)]
            table_model.appendRow(row)

        self.table_view.setModel(table_model)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
