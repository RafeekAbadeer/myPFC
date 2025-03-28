from PyQt5.QtWidgets import (QVBoxLayout, QTableView, QAction, QMessageBox, QHeaderView, QWidget,
                             QToolBar, QLabel)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QSize
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

    # Create a vertical layout to hold both tables
    main_layout = layout  # Use the existing layout instead of creating a new one
    content_frame.setLayout(main_layout)

    # Add label above transactions table
    Accounts_header = QLabel("<h3>Accounts</h3>")
    main_layout.addWidget(Accounts_header)

    # Create table view
    table_view = QTableView()
    main_layout.addWidget(table_view)
    table_view.setAlternatingRowColors(True)
    # Make transactions table non-editable
    table_view.setEditTriggers(QTableView.NoEditTriggers)

    # Select entire rows
    table_view.setSelectionBehavior(QTableView.SelectRows)

    # Create classifications panel (initially hidden)
    classifications_panel = QWidget()
    classifications_layout = QVBoxLayout(classifications_panel)
    classifications_panel.setLayout(classifications_layout)
    classifications_panel.setVisible(False)
    main_layout.addWidget(classifications_panel)

    # Create classifications toolbar
    class_toolbar = QToolBar()
    class_toolbar.setIconSize(QSize(20, 20))
    classifications_layout.addWidget(class_toolbar)

    # Add label above transactions table
    classifications_header = QLabel("<h3>Associated Classifications</h3>")
    classifications_layout.addWidget(classifications_header)

    # Add actions for classifications
    add_class_action = QAction(QIcon('icons/add.png'), "Assign Classification", class_toolbar)
    remove_class_action = QAction(QIcon('icons/delete.png'), "Remove Classification", class_toolbar)

    class_toolbar.addAction(add_class_action)
    class_toolbar.addAction(remove_class_action)

    # Create classifications table
    class_table = QTableView()
    classifications_layout.addWidget(class_table)

    class_table.setAlternatingRowColors(True)
    # Make transactions table non-editable
    class_table.setEditTriggers(QTableView.NoEditTriggers)

    # Select entire rows
    class_table.setSelectionBehavior(QTableView.SelectRows)

    # Enable sorting
    table_view.setSortingEnabled(True)
    class_table.setSortingEnabled(True)

    # Set sensible column widths
    #table_view.resizeColumnsToContents()
    #class_table.resizeColumnsToContents()

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
    table_view.resizeColumnsToContents()

    # Create a proper function to handle selection changes
    def on_selection_changed():
        update_classifications_display(table_view, classifications_panel, class_table)

    # Connect selection change signal with proper function
    table_view.selectionModel().selectionChanged.connect(on_selection_changed)

    # Connect classification actions with proper account_id retrieval
    add_class_action.triggered.connect(
        lambda: assign_classification(content_frame, table_view, class_table))
    remove_class_action.triggered.connect(
        lambda: unassign_classification(content_frame, table_view, class_table))

def load_accounts(table_view):
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["ID", "Name", "Category", "Currency", "Nature"])

    # Get accounts from database
    accounts = db.get_all_accounts()

    for account in accounts:
        account_id, name, category_name, currency_name, nature = account
        id_item = QStandardItem(str(account_id))
        name_item = QStandardItem(name)
        category_item = QStandardItem(category_name)
        currency_item = QStandardItem(currency_name)
        nature_item = QStandardItem(nature)

        # Set alignment for the ID column
        id_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Set UserRole data for proper sorting
        id_item.setData(int(account_id), Qt.UserRole)  # Sort ID as number
        name_item.setData(name.lower(), Qt.UserRole)  # Sort name case-insensitive
        category_item.setData(category_name.lower(), Qt.UserRole)  # Sort category case-insensitive
        currency_item.setData(currency_name.lower(), Qt.UserRole)  # Sort currency case-insensitive
        nature_item.setData(nature.lower(), Qt.UserRole)  # Sort nature case-insensitive

        model.appendRow([id_item, name_item, category_item, currency_item, nature_item])

    # Create proxy model for sorting
    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model)
    proxy_model.setSortRole(Qt.UserRole)  # Use UserRole for all columns

    # Set the proxy model to the table view
    table_view.setModel(proxy_model)

def add_account(parent, table_view):
    # Get categories and currencies for dropdown
    categories = [cat[1] for cat in db.get_all_categories()]
    currencies = [curr[1] for curr in db.get_all_currencies()]
    nature_options = ["both", "debit", "credit"]

    fields = [
        {'id': 'name', 'label': 'Account Name', 'type': 'text', 'required': True},
        {'id': 'category', 'label': 'Category', 'type': 'combobox', 'options': categories, 'required': True},
        {'id': 'currency', 'label': 'Default Currency', 'type': 'combobox', 'options': currencies, 'required': True},
        {'id': 'nature', 'label': 'Account Nature', 'type': 'combobox', 'options': nature_options, 'required': True},
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
            nature = data.get('nature', 'both')

            # Insert account
            account_id = db.insert_account(data['name'], category_id, currency_id, nature)

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
    nature_options = ["both", "debit", "credit"]

    # Start with basic fields
    fields = [
        {'id': 'name', 'label': 'Account Name', 'type': 'text', 'required': True},
        {'id': 'category', 'label': 'Category', 'type': 'combobox', 'options': categories, 'required': True},
        {'id': 'currency', 'label': 'Default Currency', 'type': 'combobox', 'options': currencies, 'required': True},
        {'id': 'nature', 'label': 'Account Nature', 'type': 'combobox', 'options': nature_options, 'required': True},
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
        'nature': account_data['nature'] if 'nature' in account_data else 'both',
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
            nature = data.get('nature', 'both')

            # Update account
            db.update_account(account_id, data['name'], category_id, currency_id, nature)

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

def update_classifications_display(accounts_table, classifications_panel, class_table):
    """Update the classifications table when an account is selected"""
    row_data = get_selected_row_data(accounts_table)

    if not row_data:
        classifications_panel.setVisible(False)
        return

    account_id = int(row_data["ID"])

    # Show the classifications panel
    classifications_panel.setVisible(True)

    # Load classifications for the selected account
    load_account_classifications(class_table, account_id)
    class_table.resizeColumnsToContents()

def load_account_classifications(class_table, account_id):
    """Load classifications for the selected account into the table"""
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["ID", "Classification"])

    # Get classifications from database
    classifications = db.get_classifications_for_account(account_id)

    for classification in classifications:
        class_id, class_name = classification
        id_item = QStandardItem(str(class_id))
        name_item = QStandardItem(class_name)

        # Set alignment for the ID column
        id_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Set UserRole data for proper sorting
        id_item.setData(int(class_id), Qt.UserRole)
        name_item.setData(class_name.lower(), Qt.UserRole)

        model.appendRow([id_item, name_item])

    # Create proxy model for sorting
    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model)
    proxy_model.setSortRole(Qt.UserRole)

    # Set the proxy model to the table view
    class_table.setModel(proxy_model)
    # class_table.setColumnWidth(0, 60)
    # class_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)


def filter_accounts(parent, table_view):
    # Get categories for filtering
    categories = [cat[1] for cat in db.get_all_categories()]
    categories.insert(0, "All Categories")

    # Add nature options for filtering
    nature_options = ["All", "both", "debit", "credit"]

    fields = [
        {'id': 'category_filter', 'label': 'Filter by Category', 'type': 'combobox',
         'options': categories, 'required': False},
        {'id': 'nature_filter', 'label': 'Filter by Nature', 'type': 'combobox',
         'options': nature_options, 'required': False},
        {'id': 'name_filter', 'label': 'Filter by Name', 'type': 'text', 'required': False}
    ]

    data = show_entity_dialog(parent, "Filter Accounts", fields)

    if data:
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["ID", "Name", "Category", "Currency", "Nature"])

        # Get accounts from database with potential filters
        category_filter = None if data.get('category_filter') == "All Categories" else data.get('category_filter')
        nature_filter = None if data.get('nature_filter') == "All" else data.get('nature_filter')
        name_filter = data.get('name_filter', '')

        # You'll need to implement this method in your database class
        accounts = db.filter_accounts(category_filter, name_filter, nature_filter)

        for account in accounts:
            account_id, name, category_name, currency_name, nature = account
            id_item = QStandardItem(str(account_id))
            name_item = QStandardItem(name)
            category_item = QStandardItem(category_name)
            currency_item = QStandardItem(currency_name)
            nature_item = QStandardItem(nature)

            # Set alignment for the ID column
            id_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # Set UserRole data for proper sorting
            id_item.setData(int(account_id), Qt.UserRole)
            name_item.setData(name.lower(), Qt.UserRole)
            category_item.setData(category_name.lower(), Qt.UserRole)
            currency_item.setData(currency_name.lower(), Qt.UserRole)
            nature_item.setData(nature.lower(), Qt.UserRole)

            model.appendRow([id_item, name_item, category_item, currency_item, nature_item])

        # Create proxy model for sorting
        proxy_model = QSortFilterProxyModel()
        proxy_model.setSourceModel(model)
        proxy_model.setSortRole(Qt.UserRole)

        # Set the proxy model to the table view
        table_view.setModel(proxy_model)

def assign_classification(parent, accounts_table, class_table):
    """Show dialog to assign a classification to the selected account"""
    # Always get the currently selected account
    row_data = get_selected_row_data(accounts_table)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select an account first.")
        return

    account_id = int(row_data["ID"])

    # Get all classifications
    all_classifications = db.get_all_classifications()

    # Get current classifications for this account
    current_classifications = db.get_classifications_for_account(account_id)
    current_class_ids = [c[0] for c in current_classifications]

    # Filter out already assigned classifications
    available_classifications = [c for c in all_classifications if c[0] not in current_class_ids]

    if not available_classifications:
        QMessageBox.information(parent, "Information", "All classifications are already assigned to this account.")
        return

    # Prepare classification options
    class_options = [c[1] for c in available_classifications]

    fields = [
        {'id': 'classification', 'label': 'Classification', 'type': 'combobox',
         'options': class_options, 'required': True},
    ]

    data = show_entity_dialog(parent, "Assign Classification", fields)

    if data:
        try:
            # Find classification ID
            selected_name = data['classification']
            selected_class = next((c for c in available_classifications if c[1] == selected_name), None)

            if selected_class:
                # Link account to classification
                db.link_account_classification(account_id, selected_class[0])

                # Refresh classifications table
                load_account_classifications(class_table, account_id)

                QMessageBox.information(parent, "Success", f"Classification '{selected_name}' assigned successfully.")
            else:
                QMessageBox.warning(parent, "Warning", "Selected classification not found.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to assign classification: {e}")

def unassign_classification(parent, accounts_table, class_table):
    """Remove a classification from the selected account"""
    # Always get the currently selected account
    account_row_data = get_selected_row_data(accounts_table)
    if not account_row_data:
        QMessageBox.warning(parent, "Warning", "Please select an account first.")
        return

        # Get the currently selected classification
    class_row_data = get_selected_row_data(class_table)
    if not class_row_data:
        QMessageBox.warning(parent, "Warning", "Please select a classification to remove.")
        return

    account_id = int(account_row_data["ID"])
    classification_id = int(class_row_data["ID"])
    classification_name = class_row_data["Classification"]

    reply = QMessageBox.question(
        parent,
        "Confirm Removal",
        f"Are you sure you want to remove classification '{classification_name}' from this account?",
        QMessageBox.Yes | QMessageBox.No
    )

    if reply == QMessageBox.Yes:
        try:
            # Add a function to remove the link between account and classification
            db.unlink_account_classification(account_id, classification_id)

            # Refresh classifications table
            load_account_classifications(class_table, account_id)

            QMessageBox.information(parent, "Success", "Classification removed successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to remove classification: {e}")