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


def display_categories(content_frame, toolbar):
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
    category_header = QLabel("<h3>Categories</h3>")
    layout.addWidget(category_header)

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
    export_action = QAction(QIcon('icons/export.png'), "Export", toolbar)

    toolbar.insertAction(actions_to_keep[0], add_action)
    toolbar.insertAction(actions_to_keep[0], edit_action)
    toolbar.insertAction(actions_to_keep[0], delete_action)
    toolbar.insertAction(actions_to_keep[0], filter_action)
    toolbar.insertAction(actions_to_keep[0], export_action)

    # Connect actions
    add_action.triggered.connect(lambda: add_category(content_frame, table_view))
    edit_action.triggered.connect(lambda: edit_category(content_frame, table_view))
    delete_action.triggered.connect(lambda: delete_category(content_frame, table_view))
    filter_action.triggered.connect(lambda: filter_categories(content_frame, table_view))
    export_action.triggered.connect(lambda: export_categories_data(content_frame, table_view))

    # Load data
    load_categories(table_view)


def filter_categories(parent, table_view):
    # Placeholder for filter functionality
    # Will be implemented in a later step
    QMessageBox.information(parent, "Filter", "Filter functionality will be implemented soon.")


def export_categories_data(parent, table_view):
    """
    Export categories data to CSV, Excel, or PDF
    """
    from gui.export_utils import export_table_data

    # Get the current model (which may have filters applied)
    current_model = table_view.model()
    if not current_model or current_model.rowCount() == 0:
        QMessageBox.information(parent, "Export Info", "No data to export.")
        return

    # Export the data directly - categories table is simple enough to export as-is
    export_table_data(parent, table_view, "categories_export", "Categories List")

def load_categories(table_view):
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["ID", "Name"])

    # Get categories from database
    categories = db.get_all_categories()

    for category in categories:
        cat_id, name = category
        id_item = QStandardItem(str(cat_id))
        name_item = QStandardItem(name)
        model.appendRow([id_item, name_item])

    table_view.setModel(model)

    table_view.resizeColumnsToContents()


def add_category(parent, table_view):
    fields = [
        {'id': 'name', 'label': 'Category Name', 'type': 'text', 'required': True}
    ]

    data = show_entity_dialog(parent, "Add Category", fields)
    if data:
        try:
            db.insert_category(data['name'])
            load_categories(table_view)
            QMessageBox.information(parent, "Success", "Category added successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add category: {e}")


def edit_category(parent, table_view):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a category to edit.")
        return

    category_id = int(row_data["ID"])

    fields = [
        {'id': 'name', 'label': 'Category Name', 'type': 'text', 'required': True}
    ]

    initial_data = {'name': row_data["Name"]}
    data = show_entity_dialog(parent, "Edit Category", fields, initial_data)

    if data:
        try:
            db.update_category(category_id, data['name'])
            load_categories(table_view)
            QMessageBox.information(parent, "Success", "Category updated successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to update category: {e}")


def delete_category(parent, table_view):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a category to delete.")
        return

    category_id = int(row_data["ID"])
    category_name = row_data["Name"]

    reply = QMessageBox.question(
        parent,
        "Confirm Deletion",
        f"Are you sure you want to delete the category '{category_name}'?\n\nThis may affect accounts associated with this category.",
        QMessageBox.Yes | QMessageBox.No
    )

    if reply == QMessageBox.Yes:
        try:
            db.delete_category(category_id)
            load_categories(table_view)
            QMessageBox.information(parent, "Success", "Category deleted successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to delete category: {e}")


def filter_categories(parent, table_view):
    # Placeholder for filter functionality
    # Will be implemented in a later step
    QMessageBox.information(parent, "Filter", "Filter functionality will be implemented soon.")