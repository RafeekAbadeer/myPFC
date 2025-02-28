import sqlite3
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeView, QVBoxLayout, QWidget, QMessageBox, QToolBar, QAction, QTableView, QHeaderView, QCheckBox, QSizePolicy
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt
from column_headers import column_headers
from custom_queries import custom_queries

def display_data(table_name, content_frame, toolbar):
    # Get the main window and its toolbar
    #main_window = content_frame.parent().parent()

    # Clear the content frame
    layout = content_frame.layout()
    if layout is not None:
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
    else:
        layout = QVBoxLayout(content_frame)
        content_frame.setLayout(layout)

    #toolbar.clear()  # Remove any existing actions

    for action in toolbar.actions():
        widget = toolbar.widgetForAction(action)
        if isinstance(widget, QCheckBox) or (isinstance(widget, QWidget) and widget.sizePolicy().horizontalPolicy() == QSizePolicy.Expanding):
            continue
        toolbar.removeAction(action)


    # Add buttons to the toolbar

    delete_action = QAction("Delete", toolbar)
    toolbar.insertAction(toolbar.actions()[0],delete_action)
    edit_action = QAction("Edit", toolbar)
    toolbar.insertAction(toolbar.actions()[0],edit_action)
    add_action = QAction("Add", toolbar)
    toolbar.insertAction(toolbar.actions()[0],add_action)



    # Create a table to display the data
    data_table = QTableView()
    layout.addWidget(data_table)


    try:
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()

        # Use custom query if available; otherwise, use the general query
        query = custom_queries.get(table_name, f"SELECT * FROM {table_name}")
        cursor.execute(query)

        # Get the column names from the cursor
        column_names = [description[0] for description in cursor.description]

        # Set up the model for the table view
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels([column_headers.get(column, column) for column in column_names])
        data_table.setModel(model)
        # data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Insert the data into the table
        rows = cursor.fetchall()
        for row in rows:
            items = [QStandardItem(str(item)) for item in row]
            model.appendRow(items)

        # Resize columns to fit content and header
        header = data_table.horizontalHeader()
        for col in range(len(column_names)):
            header.setSectionResizeMode(col, QHeaderView.Interactive)  # Enable manual resizing
            header.resizeSection(col, max(data_table.sizeHintForColumn(col), header.sectionSizeHint(col)))

        # Adjust the last column to take up any extra space
        header.setSectionResizeMode(len(column_names) - 1, QHeaderView.Stretch)

        conn.close()
    except sqlite3.Error as e:
        QMessageBox.critical(content_frame, "Error", f"An error occurred: {e}")

if __name__ == "__main__":
    app = QApplication([])
    window = QMainWindow()
    window.setWindowTitle("Data Display Example")
    window.resize(800, 600)

    content_frame = QWidget()
    window.setCentralWidget(content_frame)

    display_data("cat", content_frame)

    window.show()
    app.exec_()
