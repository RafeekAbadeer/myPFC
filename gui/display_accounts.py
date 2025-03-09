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


def display_accounts(content_frame, toolbar):
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
    add_action.triggered.connect(lambda: add_account(content_frame, table_view))
    edit_action.triggered.connect(lambda: edit_account(content_frame, table_view))
    delete_action.triggered.connect(lambda: delete_account(content_frame, table_view))
    filter_action.triggered.connect(lambda: filter_accounts(content_frame, table_view))

    # Load data
    load_accounts(table_view)


def load_accounts(table_view):
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["ID", "Name", "Category", "Currency"])

    # Get accounts from database
    accounts = db.get_all_accounts()

    for account in accounts:
        account_id, name, category_name, currency_name = account
        id_item = QStandardItem(str(account_id))
        name_item = QStandardItem(name)
        category_item = QStandardItem(category_name)
        currency_item = QStandardItem(currency_name)

        # Set alignment for the ID column
        id_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Set UserRole data for proper sorting
        id_item.setData(int(account_id), Qt.UserRole)  # Sort ID as number
        name_item.setData(name.lower(), Qt.UserRole)  # Sort name case-insensitive
        category_item.setData(category_name.lower(), Qt.UserRole)  # Sort category case-insensitive
        currency_item.setData(currency_name.lower(), Qt.UserRole)  # Sort currency case-insensitive

        model.appendRow([id_item, name_item, category_item, currency_item])

    # Create proxy model for sorting
    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model)
    proxy_model.setSortRole(Qt.UserRole)  # Use UserRole for all columns

    # Set the proxy model to the table view
    table_view.setModel(proxy_model)
    table_view.setColumnWidth(0, 60)
    table_view.setColumnWidth(1, 200)
    table_view.setColumnWidth(2, 150)
    table_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

def add_account(parent, table_view):
    # Get categories and currencies for dropdown
    categories = [cat[1] for cat in db.get_all_categories()]
    currencies = [curr[1] for curr in db.get_all_currencies()]

    fields = [
        {'id': 'name', 'label': 'Account Name', 'type': 'text', 'required': True},
        {'id': 'category', 'label': 'Category', 'type': 'combobox', 'options': categories, 'required': True},
        {'id': 'currency', 'label': 'Default Currency', 'type': 'combobox', 'options': currencies, 'required': True},
        {'id': 'is_credit_card', 'label': 'Is Credit Card', 'type': 'checkbox', 'required': False},
        {'id': 'credit_limit', 'label': 'Credit Limit', 'type': 'number', 'required': False,
         'depends_on': ('is_credit_card', True)},
        {'id': 'close_day', 'label': 'Statement Close Day', 'type': 'integer', 'required': False,
         'depends_on': ('is_credit_card', True)},
        {'id': 'due_day', 'label': 'Payment Due Day', 'type': 'integer', 'required': False,
         'depends_on': ('is_credit_card', True)}
    ]

    data = show_entity_dialog(parent, "Add Account", fields)
    if data:
        try:
            # Get category and currency IDs
            category_id = db.get_category_id(data['category'])
            currency_id = db.get_currency_id(data['currency'])

            # Insert account
            account_id = db.insert_account(data['name'], category_id, currency_id)

            # If it's a credit card, add credit card details
            if data.get('is_credit_card', False):
                credit_limit = data.get('credit_limit', 0)
                close_day = data.get('close_day', 1)
                due_day = data.get('due_day', 15)
                db.insert_credit_card(account_id, credit_limit, close_day, due_day)

            load_accounts(table_view)
            QMessageBox.information(parent, "Success", "Account added successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add account: {e}")


def edit_account(parent, table_view):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select an account to edit.")
        return

    account_id = int(row_data["ID"])
    is_credit_card = db.is_credit_card(account_id)

    # Get categories and currencies for dropdown
    categories = [cat[1] for cat in db.get_all_categories()]
    currencies = [curr[1] for curr in db.get_all_currencies()]

    # Start with basic fields
    fields = [
        {'id': 'name', 'label': 'Account Name', 'type': 'text', 'required': True},
        {'id': 'category', 'label': 'Category', 'type': 'combobox', 'options': categories, 'required': True},
        {'id': 'currency', 'label': 'Default Currency', 'type': 'combobox', 'options': currencies, 'required': True},
    ]

    # Add "is_credit_card" checkbox for all accounts
    fields.append({
        'id': 'is_credit_card',
        'label': 'Is Credit Card',
        'type': 'checkbox',
        'required': False
    })

    # Add conditional credit card fields
    fields.extend([
        {'id': 'credit_limit', 'label': 'Credit Limit', 'type': 'number', 'required': True,
         'depends_on': ('is_credit_card', True)},
        {'id': 'close_day', 'label': 'Statement Close Day', 'type': 'integer', 'required': True,
         'depends_on': ('is_credit_card', True)},
        {'id': 'due_day', 'label': 'Payment Due Day', 'type': 'integer', 'required': True,
         'depends_on': ('is_credit_card', True)}
    ])

    # Get account data and credit card data if applicable
    account_data = db.get_account_details(account_id)
    credit_card_data = db.get_credit_card_details(account_id) if is_credit_card else None

    # Populate initial data
    initial_data = {
        'name': row_data["Name"],
        'category': row_data["Category"],
        'currency': row_data["Currency"],
        'is_credit_card': is_credit_card
    }

    # Add credit card data if applicable
    if is_credit_card and credit_card_data:
        initial_data.update({
            'credit_limit': credit_card_data['credit_limit'],
            'close_day': credit_card_data['close_day'],
            'due_day': credit_card_data['due_day']
        })
    else:
        # Default values for new credit cards
        initial_data.update({
            'credit_limit': 1000,
            'close_day': 1,
            'due_day': 15
        })

    data = show_entity_dialog(parent, "Edit Account", fields, initial_data)

    if data:
        try:
            # Get category and currency IDs
            category_id = db.get_category_id(data['category'])
            currency_id = db.get_currency_id(data['currency'])

            # Update account
            db.update_account(account_id, data['name'], category_id, currency_id)

            # Handle credit card status change
            if data.get('is_credit_card', False):
                if is_credit_card:
                    # Update existing credit card
                    db.update_credit_card(
                        account_id,
                        data.get('credit_limit', 0),
                        data.get('close_day', 1),
                        data.get('due_day', 15)
                    )
                else:
                    # Convert regular account to credit card
                    db.insert_credit_card(
                        account_id,
                        data.get('credit_limit', 0),
                        data.get('close_day', 1),
                        data.get('due_day', 15)
                    )
            elif is_credit_card:
                # Remove credit card properties if it's no longer a credit card
                db.delete_credit_card(account_id)

            load_accounts(table_view)
            QMessageBox.information(parent, "Success", "Account updated successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to update account: {e}")


def delete_account(parent, table_view):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select an account to delete.")
        return

    account_id = int(row_data["ID"])
    account_name = row_data["Name"]

    # Check if account has transactions
    has_transactions = db.account_has_transactions(account_id)

    message = f"Are you sure you want to delete the account '{account_name}'?"
    if has_transactions:
        message += "\n\nWARNING: This account has transactions. Deleting it will also delete all associated transactions."

    reply = QMessageBox.question(
        parent,
        "Confirm Deletion",
        message,
        QMessageBox.Yes | QMessageBox.No
    )

    if reply == QMessageBox.Yes:
        try:
            # If it's a credit card, delete credit card record first
            if db.is_credit_card(account_id):
                db.delete_credit_card(account_id)

            # Delete account (this should cascade to transaction_lines)
            db.delete_account(account_id)

            load_accounts(table_view)
            QMessageBox.information(parent, "Success", "Account deleted successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to delete account: {e}")


def filter_accounts(parent, table_view):
    # Get categories for filtering
    categories = [cat[1] for cat in db.get_all_categories()]
    categories.insert(0, "All Categories")

    fields = [
        {'id': 'category_filter', 'label': 'Filter by Category', 'type': 'combobox',
         'options': categories, 'required': False},
        {'id': 'name_filter', 'label': 'Filter by Name', 'type': 'text', 'required': False}
    ]

    data = show_entity_dialog(parent, "Filter Accounts", fields)

    if data:
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["ID", "Name", "Category", "Currency"])

        # Get accounts from database with potential filters
        category_filter = None if data.get('category_filter') == "All Categories" else data.get('category_filter')
        name_filter = data.get('name_filter', '')

        accounts = db.filter_accounts(category_filter, name_filter)

        for account in accounts:
            account_id, name, category_name, currency_name = account
            id_item = QStandardItem(str(account_id))
            name_item = QStandardItem(name)
            category_item = QStandardItem(category_name)
            currency_item = QStandardItem(currency_name)

            # Set alignment for the ID column
            id_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # Set UserRole data for proper sorting
            id_item.setData(int(account_id), Qt.UserRole)  # Sort ID as number
            name_item.setData(name.lower(), Qt.UserRole)  # Sort name case-insensitive
            category_item.setData(category_name.lower(), Qt.UserRole)  # Sort category case-insensitive
            currency_item.setData(currency_name.lower(), Qt.UserRole)  # Sort currency case-insensitive

            model.appendRow([id_item, name_item, category_item, currency_item])



        # Create proxy model for sorting
        proxy_model = QSortFilterProxyModel()
        proxy_model.setSourceModel(model)
        # Then set the sort role for the proxy model
        proxy_model.setSortRole(Qt.UserRole)

        # Set the proxy model to the table view
        table_view.setModel(proxy_model)