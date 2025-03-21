from PyQt5.QtWidgets import QVBoxLayout, QTableView, QAction, QMessageBox, QHeaderView, QLabel
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


def display_classifications(content_frame, toolbar):
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

    # Add label above transactions table
    classification_header = QLabel("<h3>Classifications</h3>")
    layout.addWidget(classification_header)

    # Create table view
    table_view = QTableView()
    layout.addWidget(table_view)
    table_view.setAlternatingRowColors(True)
    # Make transactions table non-editable
    table_view.setEditTriggers(QTableView.NoEditTriggers)

    # Select entire rows
    table_view.setSelectionBehavior(QTableView.SelectRows)

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
    add_action.triggered.connect(lambda: add_classification(content_frame, table_view))
    edit_action.triggered.connect(lambda: edit_classification(content_frame, table_view))
    delete_action.triggered.connect(lambda: delete_classification(content_frame, table_view))
    filter_action.triggered.connect(lambda: filter_classifications(content_frame, table_view))

    # Load data
    load_classifications(table_view)


def load_classifications(table_view):
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["ID", "Name"])

    # Get classifications from database
    classifications = db.get_all_classifications()

    for classification in classifications:
        class_id, name = classification
        id_item = QStandardItem(str(class_id))
        name_item = QStandardItem(name)
        model.appendRow([id_item, name_item])

    table_view.setModel(model)
    table_view.resizeColumnsToContents()


def add_classification(parent, table_view):
    fields = [
        {'id': 'name', 'label': 'Classification Name', 'type': 'text', 'required': True}
    ]

    data = show_entity_dialog(parent, "Add Classification", fields)
    if data:
        try:
            db.insert_classification(data['name'])
            load_classifications(table_view)
            QMessageBox.information(parent, "Success", "Classification added successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add classification: {e}")


def edit_classification(parent, table_view):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a classification to edit.")
        return

    classification_id = int(row_data["ID"])

    fields = [
        {'id': 'name', 'label': 'Classification Name', 'type': 'text', 'required': True}
    ]

    initial_data = {'name': row_data["Name"]}
    data = show_entity_dialog(parent, "Edit Classification", fields, initial_data)

    if data:
        try:
            db.update_classification(classification_id, data['name'])
            load_classifications(table_view)
            QMessageBox.information(parent, "Success", "Classification updated successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to update classification: {e}")


def delete_classification(parent, table_view):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a classification to delete.")
        return

    classification_id = int(row_data["ID"])
    classification_name = row_data["Name"]

    reply = QMessageBox.question(
        parent,
        "Confirm Deletion",
        f"Are you sure you want to delete the classification '{classification_name}'?\n\nThis may affect transactions classified with this value.",
        QMessageBox.Yes | QMessageBox.No
    )

    if reply == QMessageBox.Yes:
        try:
            db.delete_classification(classification_id)
            load_classifications(table_view)
            QMessageBox.information(parent, "Success", "Classification deleted successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to delete classification: {e}")


def filter_classifications(parent, table_view):
    # Placeholder for filter functionality
    # Will be implemented in a later step
    QMessageBox.information(parent, "Filter", "Filter functionality will be implemented soon.")