from PyQt5.QtWidgets import QVBoxLayout, QTableView, QAction, QMessageBox, QHeaderView
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtCore import Qt, QSortFilterProxyModel
from gui.dialog_utils import show_entity_dialog
from database import db


def get_selected_row_data(table_view):
    """Helper function to get data from selected row"""
    if not table_view.selectionModel() or not table_view.selectionModel().hasSelection():
        return None

    model = table_view.model()
    row_idx = table_view.selectionModel().currentIndex().row()

    row_data = {}
    for col in range(model.columnCount()):
        col_name = model.headerData(col, Qt.Horizontal)
        value = model.data(model.index(row_idx, col))
        row_data[col_name] = value

    return row_data


def display_currencies(content_frame, toolbar):
    # Clear existing layout
    layout = content_frame.layout()
    if layout is not None:
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    else:
        layout = QVBoxLayout(content_frame)
        content_frame.setLayout(layout)

    # Clear toolbar actions except the last (dark mode toggle)
    actions_to_keep = toolbar.actions()[-2:]
    for action in toolbar.actions()[:-2]:
        toolbar.removeAction(action)

    # Create table view
    table_view = QTableView()
    layout.addWidget(table_view)

    # Enable sorting
    table_view.setSortingEnabled(True)

    # Add toolbar buttons
    add_action = QAction(QIcon('icons/add.png'), "Add", toolbar)
    edit_action = QAction(QIcon('icons/edit.png'), "Edit", toolbar)
    delete_action = QAction(QIcon('icons/delete.png'), "Delete", toolbar)
    filter_action = QAction(QIcon('icons/filter.png'), "Filter", toolbar)

    toolbar.insertAction(actions_to_keep[0], add_action)
    toolbar.insertAction(actions_to_keep[0], edit_action)
    toolbar.insertAction(actions_to_keep[0], delete_action)
    toolbar.insertAction(actions_to_keep[0], filter_action)

    # Connect actions
    add_action.triggered.connect(lambda: add_currency(content_frame, table_view))
    edit_action.triggered.connect(lambda: edit_currency(content_frame, table_view))
    delete_action.triggered.connect(lambda: delete_currency(content_frame, table_view))
    filter_action.triggered.connect(lambda: filter_currencies(content_frame, table_view))

    # Load data
    load_currencies(table_view)


def load_currencies(table_view):
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["ID", "Name", "Exchange Rate"])

    # Get currencies from database
    currencies = db.get_all_currencies()

    for currency in currencies:
        currency_id, name, exchange_rate = currency
        id_item = QStandardItem(str(currency_id))
        name_item = QStandardItem(name)
        rate_item = QStandardItem(str(exchange_rate))
        model.appendRow([id_item, name_item, rate_item])

    table_view.setModel(model)
    table_view.setColumnWidth(0, 80)
    table_view.setColumnWidth(1, 150)
    table_view.setColumnWidth(2, 150)
    table_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)


def add_currency(parent, table_view):
    fields = [
        {'id': 'name', 'label': 'Currency Name', 'type': 'text', 'required': True},
        {'id': 'exchange_rate', 'label': 'Exchange Rate', 'type': 'number', 'required': True}
    ]

    data = show_entity_dialog(parent, "Add Currency", fields)
    if data:
        try:
            db.insert_currency(data['name'], data['exchange_rate'])
            load_currencies(table_view)
            QMessageBox.information(parent, "Success", "Currency added successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add currency: {e}")


def edit_currency(parent, table_view):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a currency to edit.")
        return

    currency_id = int(row_data["ID"])

    fields = [
        {'id': 'name', 'label': 'Currency Name', 'type': 'text', 'required': True},
        {'id': 'exchange_rate', 'label': 'Exchange Rate', 'type': 'number', 'required': True}
    ]

    initial_data = {
        'name': row_data["Name"],
        'exchange_rate': float(row_data["Exchange Rate"])
    }

    data = show_entity_dialog(parent, "Edit Currency", fields, initial_data)

    if data:
        try:
            db.update_currency(currency_id, data['name'], data['exchange_rate'])
            load_currencies(table_view)
            QMessageBox.information(parent, "Success", "Currency updated successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to update currency: {e}")


def delete_currency(parent, table_view):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a currency to delete.")
        return

    currency_id = int(row_data["ID"])
    currency_name = row_data["Name"]

    reply = QMessageBox.question(
        parent,
        "Confirm Deletion",
        f"Are you sure you want to delete the currency '{currency_name}'?\n\nThis may affect accounts and transactions using this currency.",
        QMessageBox.Yes | QMessageBox.No
    )

    if reply == QMessageBox.Yes:
        try:
            db.delete_currency(currency_id)
            load_currencies(table_view)
            QMessageBox.information(parent, "Success", "Currency deleted successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to delete currency: {e}")


def filter_currencies(parent, table_view):
    # Placeholder for filter functionality
    # Will be implemented in a later step
    QMessageBox.information(parent, "Filter", "Filter functionality will be implemented soon.")