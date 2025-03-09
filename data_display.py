import sqlite3
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeView, QVBoxLayout, QWidget, QMessageBox, QToolBar, QAction, QTableView, QHeaderView, QCheckBox, QSizePolicy
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtCore import Qt
from column_headers import column_headers
from custom_queries import custom_queries

def display_data(table_name, content_frame, toolbar):

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

    # for action in toolbar.actions():
    #     widget = toolbar.widgetForAction(action)
    #     if isinstance(widget, QCheckBox) or (isinstance(widget, QWidget) and widget.sizePolicy().horizontalPolicy() == QSizePolicy.Expanding):
    #         continue
    #     toolbar.removeAction(action)


    # Add buttons to the toolbar
    filter_action = QAction(QIcon('icons/filter.png'), 'Filter', toolbar)
    toolbar.insertAction(toolbar.actions()[0],filter_action)
    delete_action = QAction(QIcon('icons/delete.png'), "Delete", toolbar)
    toolbar.insertAction(toolbar.actions()[0],delete_action)
    edit_action = QAction(QIcon('icons/edit.png'), "Edit", toolbar)
    toolbar.insertAction(toolbar.actions()[0],edit_action)
    add_action = QAction(QIcon('icons/add.png'), "Add", toolbar)
    toolbar.insertAction(toolbar.actions()[0],add_action)

    # Connect actions to functions
    action_handlers = {
        "cat": {
            "add": lambda: add_category_dialog(database, data_table, content_frame),
            "edit": lambda: edit_category_dialog(database, data_table, content_frame),
            "delete": lambda: delete_category_dialog(database, data_table, content_frame)
        },
        "accounts": {
            "add": lambda: add_account_dialog(database, data_table, content_frame),
            "edit": lambda: edit_account_dialog(database, data_table, content_frame),
            "delete": lambda: delete_account_dialog(database, data_table, content_frame)
        },
        "currency": {
            "add": lambda: add_currency_dialog(database, data_table, content_frame),
            "edit": lambda: edit_currency_dialog(database, data_table, content_frame),
            "delete": lambda: delete_currency_dialog(database, data_table, content_frame)
        },
        "ccards": {
            "add": lambda: add_credit_card_dialog(database, data_table, content_frame),
            "edit": lambda: edit_credit_card_dialog(database, data_table, content_frame),
            "delete": lambda: delete_credit_card_dialog(database, data_table, content_frame)
        }
    }

    if table_name in action_handlers:
        add_action.triggered.connect(action_handlers[table_name]["add"])
        edit_action.triggered.connect(action_handlers[table_name]["edit"])
        delete_action.triggered.connect(action_handlers[table_name]["delete"])

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


def get_selected_row_data(table_view):
    """Helper function to get data from selected row"""
    if not table_view.selectionModel().hasSelection():
        return None

    model = table_view.model()
    row = table_view.selectionModel().currentIndex().row()
    columns = model.columnCount()
    row_data = []

    for col in range(columns):
        row_data.append(model.item(row, col).text())

    return row_data


def add_category_dialog(database, table_view, parent):
    name, ok = QInputDialog.getText(parent, "Add Category", "Category Name:")
    if ok and name:
        try:
            database.insert_category(name)
            # Refresh the table
            display_data("cat", parent, parent.findChild(QToolBar), database)
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add category: {e}")


def edit_category_dialog(database, table_view, parent):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a category to edit.")
        return

    category_id = int(row_data[0])
    current_name = row_data[1]

    new_name, ok = QInputDialog.getText(parent, "Edit Category",
                                        "Category Name:", QLineEdit.Normal,
                                        current_name)
    if ok and new_name:
        try:
            database.update_category(category_id, new_name)
            # Refresh the table
            display_data("cat", parent, parent.findChild(QToolBar), database)
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to update category: {e}")


def delete_category_dialog(database, table_view, parent):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a category to delete.")
        return

    category_id = int(row_data[0])
    category_name = row_data[1]

    reply = QMessageBox.question(parent, "Confirm Deletion",
                                 f"Are you sure you want to delete the category '{category_name}'?",
                                 QMessageBox.Yes | QMessageBox.No)

    if reply == QMessageBox.Yes:
        try:
            database.delete_category(category_id)
            # Refresh the table
            display_data("cat", parent, parent.findChild(QToolBar), database)
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to delete category: {e}")

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
