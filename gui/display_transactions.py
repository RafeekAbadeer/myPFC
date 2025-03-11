from PyQt5.QtWidgets import (QVBoxLayout, QTableView, QAction, QMessageBox, QHeaderView,
                             QWidget, QToolBar, QSplitter, QLabel, QHBoxLayout, QPushButton)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QDate
from gui.dialog_utils import show_entity_dialog
from database import db
import datetime


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


def display_transactions(content_frame, toolbar):
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

    # Create a splitter to divide the main transaction table and detail panels
    splitter = QSplitter(Qt.Vertical)
    layout.addWidget(splitter)

    # Create top widget for transactions table
    transactions_widget = QWidget()
    transactions_layout = QVBoxLayout(transactions_widget)
    transactions_widget.setLayout(transactions_layout)
    splitter.addWidget(transactions_widget)

    # Create table view for transactions
    transactions_table = QTableView()
    transactions_layout.addWidget(transactions_table)

    # Create bottom widget for transaction lines
    lines_widget = QWidget()
    lines_layout = QVBoxLayout(lines_widget)
    lines_widget.setLayout(lines_layout)
    splitter.addWidget(lines_widget)

    # Create sections for debit and credit lines
    debit_label = QLabel("<h3>Debit Lines</h3>")
    lines_layout.addWidget(debit_label)

    # Debit lines toolbar
    debit_toolbar = QToolBar()
    lines_layout.addWidget(debit_toolbar)

    # Add actions for debit lines
    add_debit_action = QAction(QIcon('icons/add.png'), "Add Debit Line", debit_toolbar)
    edit_debit_action = QAction(QIcon('icons/edit.png'), "Edit Debit Line", debit_toolbar)
    delete_debit_action = QAction(QIcon('icons/delete.png'), "Delete Debit Line", debit_toolbar)

    debit_toolbar.addAction(add_debit_action)
    debit_toolbar.addAction(edit_debit_action)
    debit_toolbar.addAction(delete_debit_action)

    # Create debit lines table
    debit_table = QTableView()
    lines_layout.addWidget(debit_table)

    credit_label = QLabel("<h3>Credit Lines</h3>")
    lines_layout.addWidget(credit_label)

    # Credit lines toolbar
    credit_toolbar = QToolBar()
    lines_layout.addWidget(credit_toolbar)

    # Add actions for credit lines
    add_credit_action = QAction(QIcon('icons/add.png'), "Add Credit Line", credit_toolbar)
    edit_credit_action = QAction(QIcon('icons/edit.png'), "Edit Credit Line", credit_toolbar)
    delete_credit_action = QAction(QIcon('icons/delete.png'), "Delete Credit Line", credit_toolbar)

    credit_toolbar.addAction(add_credit_action)
    credit_toolbar.addAction(edit_credit_action)
    credit_toolbar.addAction(delete_credit_action)

    # Create credit lines table
    credit_table = QTableView()
    lines_layout.addWidget(credit_table)

    # Hide lines widget initially (will show when transaction is selected)
    lines_widget.setVisible(False)

    # Enable sorting for all tables
    transactions_table.setSortingEnabled(True)
    debit_table.setSortingEnabled(True)
    credit_table.setSortingEnabled(True)

    # Add toolbar buttons for main transactions
    add_action = QAction(QIcon('icons/add.png'), "Add", toolbar)
    edit_action = QAction(QIcon('icons/edit.png'), "Edit", toolbar)
    delete_action = QAction(QIcon('icons/delete.png'), "Delete", toolbar)
    filter_action = QAction(QIcon('icons/filter.png'), "Filter", toolbar)

    toolbar.insertAction(actions_to_keep[0], add_action)
    toolbar.insertAction(actions_to_keep[0], edit_action)
    toolbar.insertAction(actions_to_keep[0], delete_action)
    toolbar.insertAction(actions_to_keep[0], filter_action)

    # Connect actions for main transactions
    add_action.triggered.connect(lambda: add_transaction(content_frame, transactions_table))
    edit_action.triggered.connect(lambda: edit_transaction(content_frame, transactions_table))
    delete_action.triggered.connect(lambda: delete_transaction(content_frame, transactions_table))
    filter_action.triggered.connect(lambda: filter_transactions(content_frame, transactions_table))

    # Connect actions for transaction lines
    add_debit_action.triggered.connect(
        lambda: add_transaction_line(content_frame, transactions_table, debit_table, True))
    edit_debit_action.triggered.connect(lambda: edit_transaction_line(content_frame, debit_table))
    delete_debit_action.triggered.connect(
        lambda: delete_transaction_line(content_frame, debit_table, transactions_table))

    add_credit_action.triggered.connect(
        lambda: add_transaction_line(content_frame, transactions_table, credit_table, False))
    edit_credit_action.triggered.connect(lambda: edit_transaction_line(content_frame, credit_table))
    delete_credit_action.triggered.connect(
        lambda: delete_transaction_line(content_frame, credit_table, transactions_table))

    # Load initial transaction data
    load_transactions(transactions_table)

    # Create function to handle selection changes in the transactions table
    def on_transaction_selected():
        update_transaction_lines_display(transactions_table, lines_widget, debit_table, credit_table)

    # Connect selection change signal
    transactions_table.selectionModel().selectionChanged.connect(on_transaction_selected)

    # Set sensible initial sizes for the splitter
    splitter.setSizes([500, 300])


def load_transactions(table_view, limit=20, filter_params=None):
    """Load transactions into the table view"""
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["ID", "Description", "Amount", "Date", "Currency"])

    # Get transactions from database (with limit)
    transactions = get_transactions_with_summary(limit, filter_params)

    for transaction in transactions:
        transaction_id = transaction['id']
        description = transaction['description']
        amount = transaction['amount']
        date = transaction['date']
        currency = transaction['currency']

        id_item = QStandardItem(str(transaction_id))
        description_item = QStandardItem(description)
        amount_item = QStandardItem(f"{amount:.2f}")
        date_item = QStandardItem(date)
        currency_item = QStandardItem(currency)

        # Set alignment for numeric columns
        id_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Set UserRole data for proper sorting
        id_item.setData(int(transaction_id), Qt.UserRole)
        description_item.setData(description.lower(), Qt.UserRole)
        amount_item.setData(float(amount), Qt.UserRole)

        # Set date for sorting
        try:
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            date_qdate = QDate(date_obj.year, date_obj.month, date_obj.day)
            date_item.setData(date_qdate, Qt.UserRole)
        except:
            # If date parsing fails, use a default old date
            date_item.setData(QDate(1900, 1, 1), Qt.UserRole)

        currency_item.setData(currency.lower(), Qt.UserRole)

        model.appendRow([id_item, description_item, amount_item, date_item, currency_item])

    # Create proxy model for sorting
    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model)
    proxy_model.setSortRole(Qt.UserRole)

    # Set the proxy model to the table view
    table_view.setModel(proxy_model)

    # Set sensible column widths
    table_view.setColumnWidth(0, 60)  # ID
    table_view.setColumnWidth(1, 300)  # Description
    table_view.setColumnWidth(2, 120)  # Amount
    table_view.setColumnWidth(3, 120)  # Date
    table_view.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)  # Currency

    # Sort by date descending by default (most recent first)
    table_view.sortByColumn(3, Qt.DescendingOrder)


def get_transactions_with_summary(limit=20, filter_params=None):
    """Get transactions from database with summary information"""
    # Implementation would depend on your database schema
    # Here's a mockup of what the query might do:
    # 1. Get latest transactions
    # 2. Calculate total amount for each
    # 3. Find earliest date for each

    transactions = db.get_transactions()
    result = []

    for transaction in transactions[:limit]:  # Apply limit
        transaction_id = transaction[0]
        description = transaction[1]
        currency_id = transaction[2]

        # Get currency name
        currency_data = db.get_currency_by_id(currency_id)
        currency_name = currency_data[1] if currency_data else "Unknown"

        # Get transaction lines
        lines = db.get_transaction_lines(transaction_id)

        # Calculate total amount (sum of debits or credits)
        total_debit = sum(line[3] if line[3] else 0 for line in lines)

        # Find earliest date
        dates = [line[5] for line in lines if line[5]]
        earliest_date = min(dates) if dates else "N/A"

        result.append({
            'id': transaction_id,
            'description': description,
            'amount': total_debit,  # Using debit total as the displayed amount
            'date': earliest_date,
            'currency': currency_name
        })

    return result


def load_transaction_lines(table_view, transaction_id, is_debit=True):
    """Load transaction lines into the appropriate table view"""
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["ID", "Account", "Amount", "Date", "Classification"])

    # Get transaction lines from database
    lines = db.get_transaction_lines(transaction_id)

    for line in lines:
        line_id = line[0]
        account_id = line[2]
        debit = line[3] if line[3] else 0
        credit = line[4] if line[4] else 0
        date = line[5]

        # Skip lines that don't match the requested type (debit/credit)
        if is_debit and not debit:
            continue
        if not is_debit and not credit:
            continue

        # Get account name
        account_data = db.get_account_by_id(account_id)
        account_name = account_data[1] if account_data else "Unknown"

        # Get classification name if available
        classification_id = line[6] if len(line) > 6 else None
        classification_name = ""
        if classification_id:
            classification_data = db.get_classification_by_id(classification_id)
            classification_name = classification_data[1] if classification_data else ""

        id_item = QStandardItem(str(line_id))
        account_item = QStandardItem(account_name)
        amount_item = QStandardItem(f"{debit if is_debit else credit:.2f}")
        date_item = QStandardItem(date)
        classification_item = QStandardItem(classification_name)

        # Set alignment
        id_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Set UserRole data for proper sorting
        id_item.setData(int(line_id), Qt.UserRole)
        account_item.setData(account_name.lower(), Qt.UserRole)
        amount_item.setData(float(debit if is_debit else credit), Qt.UserRole)

        # Parse date for sorting
        try:
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            date_qdate = QDate(date_obj.year, date_obj.month, date_obj.day)
            date_item.setData(date_qdate, Qt.UserRole)
        except:
            date_item.setData(QDate(1900, 1, 1), Qt.UserRole)

        classification_item.setData(classification_name.lower(), Qt.UserRole)

        model.appendRow([id_item, account_item, amount_item, date_item, classification_item])

    # Create proxy model for sorting
    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model)
    proxy_model.setSortRole(Qt.UserRole)

    # Set the proxy model to the table view
    table_view.setModel(proxy_model)

    # Set column widths
    table_view.setColumnWidth(0, 60)  # ID
    table_view.setColumnWidth(1, 200)  # Account
    table_view.setColumnWidth(2, 120)  # Amount
    table_view.setColumnWidth(3, 100)  # Date
    table_view.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)  # Classification


def update_transaction_lines_display(transactions_table, lines_widget, debit_table, credit_table):
    """Update both transaction line tables when a transaction is selected"""
    row_data = get_selected_row_data(transactions_table)

    if not row_data:
        lines_widget.setVisible(False)
        return

    transaction_id = int(row_data["ID"])

    # Show the detail widget
    lines_widget.setVisible(True)

    # Load lines into appropriate tables
    load_transaction_lines(debit_table, transaction_id, is_debit=True)
    load_transaction_lines(credit_table, transaction_id, is_debit=False)


def add_transaction(parent, table_view):
    """Add a new transaction"""
    # Get currencies for dropdown
    currencies = [curr[1] for curr in db.get_all_currencies()]

    fields = [
        {'id': 'description', 'label': 'Description', 'type': 'text', 'required': True},
        {'id': 'currency', 'label': 'Currency', 'type': 'combobox', 'options': currencies, 'required': True},
    ]

    data = show_entity_dialog(parent, "Add Transaction", fields)

    if data:
        try:
            # Get currency ID
            currency_id = db.get_currency_id(data['currency'])

            # Insert transaction
            transaction_id = db.insert_transaction(data['description'], currency_id)

            # Reload transactions
            load_transactions(table_view)

            # Show message about adding transaction lines
            QMessageBox.information(parent, "Transaction Added",
                                    "Transaction added successfully. Please add transaction lines next.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add transaction: {e}")


def edit_transaction(parent, table_view):
    """Edit an existing transaction"""
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a transaction to edit.")
        return

    transaction_id = int(row_data["ID"])

    # Get currencies for dropdown
    currencies = [curr[1] for curr in db.get_all_currencies()]

    fields = [
        {'id': 'description', 'label': 'Description', 'type': 'text', 'required': True},
        {'id': 'currency', 'label': 'Currency', 'type': 'combobox', 'options': currencies, 'required': True},
    ]

    # Set initial values
    initial_data = {
        'description': row_data["Description"],
        'currency': row_data["Currency"]
    }

    data = show_entity_dialog(parent, "Edit Transaction", fields, initial_data)

    if data:
        try:
            # Get currency ID
            currency_id = db.get_currency_id(data['currency'])

            # Update transaction (we need to add this function to database.py)
            db.update_transaction(transaction_id, data['description'], currency_id)

            # Reload transactions
            load_transactions(table_view)

            QMessageBox.information(parent, "Success", "Transaction updated successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to update transaction: {e}")


def delete_transaction(parent, table_view):
    """Delete an existing transaction"""
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a transaction to delete.")
        return

    transaction_id = int(row_data["ID"])
    description = row_data["Description"]

    reply = QMessageBox.question(
        parent,
        "Confirm Deletion",
        f"Are you sure you want to delete the transaction '{description}'?\n\n"
        "This will also delete all associated transaction lines.",
        QMessageBox.Yes | QMessageBox.No
    )

    if reply == QMessageBox.Yes:
        try:
            # Delete transaction (we need to add this function to database.py)
            db.delete_transaction(transaction_id)

            # Reload transactions
            load_transactions(table_view)

            QMessageBox.information(parent, "Success", "Transaction deleted successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to delete transaction: {e}")


def add_transaction_line(parent, transactions_table, lines_table, is_debit=True):
    """Add a new transaction line"""
    # First check if a transaction is selected
    row_data = get_selected_row_data(transactions_table)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a transaction first.")
        return

    transaction_id = int(row_data["ID"])

    # Get accounts for dropdown
    accounts = [acc[1] for acc in db.get_all_accounts()]

    # Prepare classifications dropdown for this account
    classifications = ["(None)"]  # Default option

    fields = [
        {'id': 'account', 'label': 'Account', 'type': 'combobox', 'options': accounts, 'required': True},
        {'id': 'amount', 'label': f"{'Debit' if is_debit else 'Credit'} Amount", 'type': 'number', 'required': True},
        {'id': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        {'id': 'classification', 'label': 'Classification', 'type': 'combobox',
         'options': classifications, 'required': False, 'depends_on': ('account', None)},
    ]

    # Set default date to today
    initial_data = {
        'date': datetime.date.today().strftime("%Y-%m-%d")
    }

    data = show_entity_dialog(parent, f"Add {'Debit' if is_debit else 'Credit'} Line", fields, initial_data)

    if data:
        try:
            # Get account ID
            account_id = db.get_account_id(data['account'])

            # Process classification
            classification_id = None
            if data.get('classification') and data['classification'] != "(None)":
                classification = db.get_classification_by_name(data['classification'])
                if classification:
                    classification_id = classification[0]

            # Insert transaction line
            if is_debit:
                line_id = db.insert_transaction_line(
                    transaction_id, account_id,
                    debit=float(data['amount']),
                    credit=None,
                    date=data['date'],
                    classification_id=classification_id
                )
            else:
                line_id = db.insert_transaction_line(
                    transaction_id, account_id,
                    debit=None,
                    credit=float(data['amount']),
                    date=data['date'],
                    classification_id=classification_id
                )

            # Reload transaction lines
            load_transaction_lines(lines_table, transaction_id, is_debit)

            # Also reload main transaction table as summary might change
            load_transactions(transactions_table)

            QMessageBox.information(parent, "Success", "Transaction line added successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add transaction line: {e}")


def edit_transaction_line(parent, lines_table):
    """Edit an existing transaction line"""
    row_data = get_selected_row_data(lines_table)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a transaction line to edit.")
        return

    line_id = int(row_data["ID"])

    # Get accounts for dropdown
    accounts = [acc[1] for acc in db.get_all_accounts()]

    # Get classifications
    classifications = ["(None)"]
    # Additional classifications would be loaded based on selected account

    fields = [
        {'id': 'account', 'label': 'Account', 'type': 'combobox', 'options': accounts, 'required': True},
        {'id': 'amount', 'label': 'Amount', 'type': 'number', 'required': True},
        {'id': 'date', 'label': 'Date', 'type': 'date', 'required': True},
        {'id': 'classification', 'label': 'Classification', 'type': 'combobox',
         'options': classifications, 'required': False},
    ]

    # Get current transaction line data
    # We need to implement this method in database.py
    line_data = db.get_transaction_line(line_id)

    if not line_data:
        QMessageBox.warning(parent, "Warning", "Transaction line not found.")
        return

    # Set initial values
    initial_data = {
        'account': row_data["Account"],
        'amount': float(row_data["Amount"]),
        'date': line_data['date'],
        'classification': row_data["Classification"] if row_data["Classification"] else "(None)"
    }

    data = show_entity_dialog(parent, "Edit Transaction Line", fields, initial_data)

    if data:
        try:
            # Get account ID
            account_id = db.get_account_id(data['account'])

            # Process classification
            classification_id = None
            if data.get('classification') and data['classification'] != "(None)":
                classification = db.get_classification_by_name(data['classification'])
                if classification:
                    classification_id = classification[0]

            # Determine if this is a debit or credit line
            is_debit = "Debit" in line_data['type']

            # Update transaction line
            # We need to implement this method in database.py
            if is_debit:
                db.update_transaction_line(
                    line_id, account_id,
                    debit=float(data['amount']),
                    credit=None,
                    date=data['date'],
                    classification_id=classification_id
                )
            else:
                db.update_transaction_line(
                    line_id, account_id,
                    debit=None,
                    credit=float(data['amount']),
                    date=data['date'],
                    classification_id=classification_id
                )

            # Get transaction ID to reload tables
            transaction_id = line_data['transaction_id']

            # Reload transaction lines
            load_transaction_lines(lines_table, transaction_id, is_debit)

            QMessageBox.information(parent, "Success", "Transaction line updated successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to update transaction line: {e}")


def delete_transaction_line(parent, lines_table, transactions_table):
    """Delete an existing transaction line"""
    row_data = get_selected_row_data(lines_table)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a transaction line to delete.")
        return

    line_id = int(row_data["ID"])
    account_name = row_data["Account"]

    # Get transaction ID for this line (needed to reload tables after deletion)
    # We need to implement this method in database.py
    line_data = db.get_transaction_line(line_id)
    if not line_data:
        QMessageBox.warning(parent, "Warning", "Transaction line not found.")
        return

    transaction_id = line_data['transaction_id']
    is_debit = "Debit" in line_data['type']

    reply = QMessageBox.question(
        parent,
        "Confirm Deletion",
        f"Are you sure you want to delete this transaction line for account '{account_name}'?",
        QMessageBox.Yes | QMessageBox.No
    )

    if reply == QMessageBox.Yes:
        try:
            # Delete transaction line
            # We need to implement this method in database.py
            db.delete_transaction_line(line_id)

            # Reload transaction lines
            load_transaction_lines(lines_table, transaction_id, is_debit)

            # Also reload main transaction table as summary might change
            load_transactions(transactions_table)

            QMessageBox.information(parent, "Success", "Transaction line deleted successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to delete transaction line: {e}")


def filter_transactions(parent, table_view):
    """Filter transactions by various criteria"""
    # Get accounts for filtering
    accounts = ["All Accounts"]
    accounts.extend([acc[1] for acc in db.get_all_accounts()])

    # Get dates for default range (last 30 days)
    today = datetime.date.today()
    thirty_days_ago = today - datetime.timedelta(days=30)

    fields = [
        {'id': 'date_from', 'label': 'From Date', 'type': 'date', 'required': False},
        {'id': 'date_to', 'label': 'To Date', 'type': 'date', 'required': False},
        {'id': 'account', 'label': 'Account', 'type': 'combobox', 'options': accounts, 'required': False},
        {'id': 'description', 'label': 'Description Contains', 'type': 'text', 'required': False},
        {'id': 'min_amount', 'label': 'Minimum Amount', 'type': 'number', 'required': False},
        {'id': 'max_amount', 'label': 'Maximum Amount', 'type': 'number', 'required': False}
    ]

    # Set initial values
    initial_data = {
        'date_from': thirty_days_ago.strftime("%Y-%m-%d"),
        'date_to': today.strftime("%Y-%m-%d")
    }

    data = show_entity_dialog(parent, "Filter Transactions", fields, initial_data)

    if data:
        # Prepare filter parameters
        filter_params = {}

        if data.get('date_from'):
            filter_params['date_from'] = data['date_from']

        if data.get('date_to'):
            filter_params['date_to'] = data['date_to']

        if data.get('account') and data['account'] != "All Accounts":
            account_id = db.get_account_id(data['account'])
            filter_params['account_id'] = account_id

        if data.get('description'):
            filter_params['description'] = data['description']

        if data.get('min_amount'):
            filter_params['min_amount'] = float(data['min_amount'])

        if data.get('max_amount'):
            filter_params['max_amount'] = float(data['max_amount'])

        # Reload transactions with filter
        load_transactions(table_view, limit=None, filter_params=filter_params)