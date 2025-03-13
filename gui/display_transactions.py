from PyQt5.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QTableView, QAction, QMessageBox,
                             QHeaderView, QWidget, QToolBar, QSplitter, QLabel, QHBoxLayout, QPushButton,
                             QDialog, QGroupBox, QGridLayout, QLineEdit, QDateEdit,QComboBox, QDialogButtonBox,
                             QScrollArea, QFrame)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon, QDoubleValidator, QPixmap
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QDate, QTimer, QObject, QEvent
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

    # Make transactions table non-editable
    transactions_table.setEditTriggers(QTableView.NoEditTriggers)

    # Select entire rows
    transactions_table.setSelectionBehavior(QTableView.SelectRows)

    # Create bottom widget for transaction lines
    lines_widget = QWidget()
    lines_layout = QVBoxLayout(lines_widget)
    lines_widget.setLayout(lines_layout)
    splitter.addWidget(lines_widget)

    # Create sections for debit and credit lines
    debit_label = QLabel("<h3>Debit Lines</h3>")
    lines_layout.addWidget(debit_label)

    # Create debit lines table
    debit_table = QTableView()
    lines_layout.addWidget(debit_table)

    # Make debit lines table non-editable
    debit_table.setEditTriggers(QTableView.NoEditTriggers)

    # Select entire rows
    debit_table.setSelectionBehavior(QTableView.SelectRows)

    credit_label = QLabel("<h3>Credit Lines</h3>")
    lines_layout.addWidget(credit_label)

    # Create credit lines table
    credit_table = QTableView()
    lines_layout.addWidget(credit_table)

    # Make credit lines table non-editable
    credit_table.setEditTriggers(QTableView.NoEditTriggers)

    # Select entire rows
    credit_table.setSelectionBehavior(QTableView.SelectRows)

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
    add_action.triggered.connect(lambda: add_transaction_wizard(content_frame, transactions_table))
    edit_action.triggered.connect(lambda: edit_transaction(content_frame, transactions_table))
    delete_action.triggered.connect(lambda: delete_transaction(content_frame, transactions_table))
    filter_action.triggered.connect(lambda: filter_transactions(content_frame, transactions_table))

    # Load initial transaction data
    load_transactions(transactions_table)

    # Create function to handle selection changes in the transactions table
    def on_transaction_selected():
        update_transaction_lines_display(transactions_table, lines_widget, debit_table, credit_table)

    # Store the function on the table_view for later reconnection
    transactions_table._on_transaction_selected = on_transaction_selected

    # Connect selection change signal
    transactions_table.selectionModel().selectionChanged.connect(on_transaction_selected)

    # Set sensible initial sizes for the splitter
    splitter.setSizes([500, 300])

def load_transactions(table_view, limit=20, filter_params=None, select_transaction_id=None):
    """Load transactions into the table view"""
    # Store the on_transaction_selected function for reconnection
    on_transaction_selected = None
    if hasattr(table_view, '_on_transaction_selected'):
        on_transaction_selected = table_view._on_transaction_selected

    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["ID", "Date", "Description", "Amount", "Currency"])

    # Get transactions from database (with limit)
    transactions = get_transactions_with_summary(limit, filter_params)

    for transaction in transactions:
        transaction_id = transaction['id']
        date = transaction['date']
        description = transaction['description']
        amount = transaction['amount']
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
        date_item.setData(QDate.fromString(date, "yyyy-MM-dd"), Qt.UserRole)
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

        model.appendRow([id_item, date_item, description_item, amount_item, currency_item])

    # Create proxy model for sorting
    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model)
    proxy_model.setSortRole(Qt.UserRole)

    # Store the current selection if any and no specific selection is requested
    selected_transaction_id = None
    if select_transaction_id is None and table_view.model() and table_view.selectionModel() and table_view.selectionModel().hasSelection():
        idx = table_view.selectionModel().currentIndex()
        selected_transaction_id = table_view.model().data(table_view.model().index(idx.row(), 0))
    else:
        selected_transaction_id = select_transaction_id

    # Set the proxy model to the table view
    table_view.setModel(proxy_model)

    # Reconnect the selection change signal
    if on_transaction_selected:
        table_view._on_transaction_selected = on_transaction_selected
        table_view.selectionModel().selectionChanged.connect(on_transaction_selected)

    # Resize columns
    table_view.resizeColumnsToContents()

    # Sort by date descending by default (most recent first)
    table_view.sortByColumn(0, Qt.DescendingOrder)
    table_view.sortByColumn(1, Qt.DescendingOrder)

    # Hide the ID column
    #table_view.hideColumn(0)

    # Restore selection if possible
    if selected_transaction_id:
        for row in range(proxy_model.rowCount()):
            if str(proxy_model.data(proxy_model.index(row, 0))) == str(selected_transaction_id):
                table_view.selectRow(row)
                break

    # Set sensible column widths
    table_view.resizeColumnsToContents()

    # Sort by date descending by default (most recent first)
    table_view.sortByColumn(0, Qt.DescendingOrder)
    table_view.sortByColumn(1, Qt.DescendingOrder)

    # Hide the ID column
    #table_view.hideColumn(0)

def get_transactions_with_summary(limit=20, filter_params=None):
    """Get transactions from database with summary information"""
    # Build the query dynamically based on filters
    query = """
        SELECT t.id, t.description, t.currency_id, 
               SUM(IFNULL(tl.debit, 0)) as total_debit,
               MIN(tl.date) as earliest_date
        FROM transactions t
        LEFT JOIN transaction_lines tl ON t.id = tl.transaction_id
    """

    where_clauses = []
    params = []

    # Apply filters if provided
    if filter_params:
        if 'date_from' in filter_params:
            where_clauses.append("tl.date >= ?")
            params.append(filter_params['date_from'])

        if 'date_to' in filter_params:
            where_clauses.append("tl.date <= ?")
            params.append(filter_params['date_to'])

        if 'account_id' in filter_params:
            where_clauses.append("tl.account_id = ?")
            params.append(filter_params['account_id'])

        if 'description' in filter_params:
            where_clauses.append("t.description LIKE ?")
            params.append(f"%{filter_params['description']}%")

    # Add WHERE clause if we have conditions
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    # Group by transaction and order by date
    query += " GROUP BY t.id, t.description, t.currency_id ORDER BY earliest_date DESC"

    # Apply limit if specified
    if limit:
        query += f" LIMIT {limit}"

    # Execute the query
    cursor = db.conn.cursor()
    cursor.execute(query, params)
    transactions_data = cursor.fetchall()

    result = []
    for data in transactions_data:
        transaction_id = data[0]
        description = data[1]
        currency_id = data[2]
        total_debit = data[3] or 0
        earliest_date = data[4] or "N/A"

        # Get currency name
        currency_data = db.get_currency_by_id(currency_id)
        currency_name = currency_data[1] if currency_data else "Unknown"

        # Apply amount filters if specified
        if filter_params:
            if 'min_amount' in filter_params and total_debit < filter_params['min_amount']:
                continue

            if 'max_amount' in filter_params and total_debit > filter_params['max_amount']:
                continue

        result.append({
            'id': transaction_id,
            'description': description,
            'amount': total_debit,
            'date': earliest_date,
            'currency': currency_name
        })

    return result

def load_transaction_lines(table_view, transaction_id, is_debit=True):
    """Load transaction lines into the appropriate table view"""
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["ID", "Date", "Account", "Classification", "Amount"])

    # Get transaction lines from database
    lines = db.get_transaction_lines(transaction_id)

    for line in lines:
        line_id = line[0]
        account_id = line[2]
        debit = line[3] if line[3] else 0
        credit = line[4] if line[4] else 0
        date = line[5]
        classification_id = line[7]

        # Skip lines that don't match the requested type (debit/credit)
        if is_debit and not debit:
            continue
        if not is_debit and not credit:
            continue

        # Get account name
        account_data = db.get_account_by_id(account_id)
        account_name = account_data[1] if account_data else "Unknown"

        # Get classification name if available
        #classification_id = line[6] if len(line) > 6 else None
        classification_name = ""
        if classification_id:
            classification_data = db.get_classification_by_id(classification_id)
            #classification_name = classification_data[1] if classification_data else ""
            if classification_data:
                classification_name = classification_data[1]

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

        model.appendRow([id_item, date_item, account_item, classification_item, amount_item])

    # Create proxy model for sorting
    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model)
    proxy_model.setSortRole(Qt.UserRole)

    # Set the proxy model to the table view
    table_view.setModel(proxy_model)

    table_view.resizeColumnsToContents()
    # Hide the ID column
    #table_view.hideColumn(0)

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
    """Add a new transaction with a comprehensive form collecting all data at once"""
    # Get currencies for dropdown
    currencies = [curr[1] for curr in db.get_all_currencies()]

    # Get accounts for dropdown
    accounts = [acc[1] for acc in db.get_all_accounts()]

    # Create a custom dialog for the comprehensive transaction entry
    dialog = QDialog(parent)
    dialog.setWindowTitle("Add Transaction")
    dialog.setMinimumWidth(700)
    dialog.setMinimumHeight(500)

    layout = QVBoxLayout(dialog)

    # Transaction header section
    header_group = QGroupBox("Transaction Details")
    header_layout = QGridLayout(header_group)

    # Add header fields: description, amount, date, currency
    header_layout.addWidget(QLabel("Description:"), 0, 0)
    description_edit = QLineEdit()
    header_layout.addWidget(description_edit, 0, 1, 1, 5)

    header_layout.addWidget(QLabel("Total Amount:"), 1, 0)
    total_amount_edit = QLineEdit()
    total_amount_edit.setValidator(QDoubleValidator())
    header_layout.addWidget(total_amount_edit, 1, 1)

    header_layout.addWidget(QLabel("Date:"), 1, 2)
    date_edit = QDateEdit(QDate.currentDate())
    date_edit.setCalendarPopup(True)
    header_layout.addWidget(date_edit, 1, 3)

    header_layout.addWidget(QLabel("Currency:"), 1, 4)
    currency_combo = QComboBox()
    currency_combo.addItems(currencies)
    # Set default to EGP if available
    default_index = currencies.index("EGP") if "EGP" in currencies else 0
    currency_combo.setCurrentIndex(default_index)
    header_layout.addWidget(currency_combo, 1, 5)

    header_layout.setColumnStretch(0, 1)  # Label column
    header_layout.setColumnStretch(1, 2)  # Amount column
    header_layout.setColumnStretch(2, 1)  # Date label column
    header_layout.setColumnStretch(3, 2)  # Date column
    header_layout.setColumnStretch(4, 1)
    header_layout.setColumnStretch(5, 2)

    layout.addWidget(header_group)

    # Credit lines section
    credit_group = QGroupBox("Credit Lines")
    credit_layout = QVBoxLayout(credit_group)

    credit_lines_widget = QWidget()
    credit_lines_layout = QVBoxLayout(credit_lines_widget)
    credit_lines_layout.setContentsMargins(0, 0, 0, 0)

    # Function to add a credit line row
    credit_line_widgets = []

    def add_credit_line(amount=None):
        line_widget = QWidget()
        line_layout = QHBoxLayout(line_widget)
        line_layout.setContentsMargins(0, 0, 0, 0)

        account_combo = QComboBox()
        account_combo.addItems(accounts)

        classification_combo = QComboBox()
        classification_combo.addItem("(None)")

        amount_edit = QLineEdit()
        amount_edit.setValidator(QDoubleValidator())
        if amount:
            amount_edit.setText(str(amount))

        line_date_edit = QDateEdit(date_edit.date())
        line_date_edit.setCalendarPopup(True)

        remove_btn = QPushButton("Remove")

        line_layout.addWidget(account_combo, 3)
        line_layout.addWidget(classification_combo, 2)
        line_layout.addWidget(amount_edit, 2)
        line_layout.addWidget(line_date_edit, 2)
        line_layout.addWidget(remove_btn, 1)

        credit_lines_layout.addWidget(line_widget)

        # Add to tracking list
        line_data = {
            'widget': line_widget,
            'account': account_combo,
            'classification': classification_combo,
            'amount': amount_edit,
            'date': line_date_edit,
            'remove': remove_btn
        }
        credit_line_widgets.append(line_data)

        # Connect signals
        amount_edit.textChanged.connect(update_remaining_amount)
        remove_btn.clicked.connect(lambda: remove_credit_line(line_data))
        account_combo.currentIndexChanged.connect(
            lambda index: update_classification_combo(classification_combo, accounts[index]))

        return line_data

    def remove_credit_line(line_data):
        credit_line_widgets.remove(line_data)
        line_data['widget'].deleteLater()
        update_remaining_amount()

    credit_layout.addWidget(credit_lines_widget)

    # Add button for credit lines
    add_credit_btn = QPushButton("Add Credit Line")
    add_credit_btn.clicked.connect(lambda: add_credit_line())
    credit_layout.addWidget(add_credit_btn)

    layout.addWidget(credit_group)

    # Debit lines section (similar to credit lines)
    debit_group = QGroupBox("Debit Lines")
    debit_layout = QVBoxLayout(debit_group)

    debit_lines_widget = QWidget()
    debit_lines_layout = QVBoxLayout(debit_lines_widget)
    debit_lines_layout.setContentsMargins(0, 0, 0, 0)

    # Function to add a debit line row
    debit_line_widgets = []

    def add_debit_line(amount=None):
        line_widget = QWidget()
        line_layout = QHBoxLayout(line_widget)
        line_layout.setContentsMargins(0, 0, 0, 0)

        account_combo = QComboBox()
        account_combo.addItems(accounts)

        classification_combo = QComboBox()
        classification_combo.addItem("(None)")

        amount_edit = QLineEdit()
        amount_edit.setValidator(QDoubleValidator())
        if amount:
            amount_edit.setText(str(amount))

        line_date_edit = QDateEdit(date_edit.date())
        line_date_edit.setCalendarPopup(True)

        remove_btn = QPushButton("Remove")

        line_layout.addWidget(account_combo, 3)
        line_layout.addWidget(classification_combo, 2)
        line_layout.addWidget(amount_edit, 2)
        line_layout.addWidget(line_date_edit, 2)
        line_layout.addWidget(remove_btn, 1)

        debit_lines_layout.addWidget(line_widget)

        # Add to tracking list
        line_data = {
            'widget': line_widget,
            'account': account_combo,
            'classification': classification_combo,
            'amount': amount_edit,
            'date': line_date_edit,
            'remove': remove_btn
        }
        debit_line_widgets.append(line_data)

        # Connect signals
        amount_edit.textChanged.connect(update_remaining_amount)
        remove_btn.clicked.connect(lambda: remove_debit_line(line_data))
        account_combo.currentIndexChanged.connect(
            lambda index: update_classification_combo(classification_combo, accounts[index]))

        return line_data

    # Function to update classification combo based on selected account
    def update_classification_combo(combo, account_name):
        combo.clear()
        combo.addItem("(None)")
        account_id = db.get_account_id(account_name)
        classifications = db.get_classifications_for_account(account_id)
        for classification in classifications:
            combo.addItem(classification[1])

    def remove_debit_line(line_data):
        debit_line_widgets.remove(line_data)
        line_data['widget'].deleteLater()
        update_remaining_amount()

    debit_layout.addWidget(debit_lines_widget)

    # Add button for debit lines
    add_debit_btn = QPushButton("Add Debit Line")
    add_debit_btn.clicked.connect(lambda: add_debit_line())
    debit_layout.addWidget(add_debit_btn)

    layout.addWidget(debit_group)

    # Summary section
    summary_widget = QWidget()
    summary_layout = QHBoxLayout(summary_widget)

    credit_total_label = QLabel("Credit Total: 0.00")
    debit_total_label = QLabel("Debit Total: 0.00")
    balance_label = QLabel("Balance: 0.00")

    summary_layout.addWidget(credit_total_label)
    summary_layout.addWidget(debit_total_label)
    summary_layout.addWidget(balance_label)

    layout.addWidget(summary_widget)

    # Function to update remaining amounts
    def update_remaining_amount():
        try:
            total_amount = float(total_amount_edit.text() or 0)

            # Calculate credit total
            credit_total = 0
            for line in credit_line_widgets:
                try:
                    credit_total += float(line['amount'].text() or 0)
                except ValueError:
                    pass

            # Calculate debit total
            debit_total = 0
            for line in debit_line_widgets:
                try:
                    debit_total += float(line['amount'].text() or 0)
                except ValueError:
                    pass

            # Update display
            credit_total_label.setText(f"Credit Total: {credit_total:.2f}")
            debit_total_label.setText(f"Debit Total: {debit_total:.2f}")

            # Calculate balance
            balance = debit_total - credit_total
            balance_label.setText(f"Balance: {balance:.2f}")

            # Color code balance
            if abs(balance) < 0.01:  # Allow for minor floating point differences
                balance_label.setStyleSheet("color: green;")
            else:
                balance_label.setStyleSheet("color: red;")
        except ValueError:
            pass

    # Connect header signals
    total_amount_edit.textChanged.connect(update_remaining_amount)
    date_edit.dateChanged.connect(lambda date: update_line_dates(date))

    def update_line_dates(new_date):
        for line in credit_line_widgets + debit_line_widgets:
            line['date'].setDate(new_date)

    # Buttons
    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)

    # Add first credit line by default
    add_credit_line()

    # Show dialog
    if dialog.exec_() == QDialog.Accepted:
        try:
            # Validate transaction
            if not description_edit.text().strip():
                raise ValueError("Description is required")

            total_amount = float(total_amount_edit.text() or 0)
            if total_amount <= 0:
                raise ValueError("Total amount must be greater than zero")

            # Get currency ID
            currency_id = db.get_currency_id(currency_combo.currentText())

            # Get credit and debit lines
            credit_lines = []
            for line in credit_line_widgets:
                try:
                    amount = float(line['amount'].text() or 0)
                    if amount <= 0:
                        continue  # Skip lines with zero or negative amounts

                    account_id = db.get_account_id(line['account'].currentText())
                    line_date = line['date'].date().toString("yyyy-MM-dd")
                    classification_name = line['classification'].currentText()
                    classification_id = None
                    if classification_name != "(None)":
                        classification = db.get_classification_by_name(classification_name)
                        if classification:
                            classification_id = classification[0]

                    credit_lines.append({
                        'account_id': account_id,
                        'amount': amount,
                        'date': line_date,
                        'classification_id': classification_id
                    })
                except ValueError:
                    pass

            debit_lines = []
            for line in debit_line_widgets:
                try:
                    amount = float(line['amount'].text() or 0)
                    if amount <= 0:
                        continue  # Skip lines with zero or negative amounts

                    account_id = db.get_account_id(line['account'].currentText())
                    line_date = line['date'].date().toString("yyyy-MM-dd")
                    classification_name = line['classification'].currentText()
                    classification_id = None
                    if classification_name != "(None)":
                        classification = db.get_classification_by_name(classification_name)
                        if classification:
                            classification_id = classification[0]

                    debit_lines.append({
                        'account_id': account_id,
                        'amount': amount,
                        'date': line_date,
                        'classification_id': classification_id
                    })
                except ValueError:
                    pass

            # Calculate totals for final check
            credit_total = sum(line['amount'] for line in credit_lines)
            debit_total = sum(line['amount'] for line in debit_lines)

            # Verify balanced transaction
            if abs(credit_total - debit_total) > 0.01:  # Allow for minor floating point differences
                raise ValueError(f"Transaction is not balanced. Credit: {credit_total:.2f}, Debit: {debit_total:.2f}")

            if not credit_lines or not debit_lines:
                raise ValueError("At least one credit and one debit line are required")

            # Save transaction and lines
            new_transaction_id = save_complete_transaction(
                description_edit.text(),
                currency_id,
                credit_lines,
                debit_lines
            )

            # Reload transactions and select the new one
            load_transactions(table_view, select_transaction_id=new_transaction_id)

            # Force transaction selection update
            if hasattr(table_view, '_on_transaction_selected'):
                table_view._on_transaction_selected()

            QMessageBox.information(parent, "Success", "Transaction added successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add transaction: {e}")

def add_transaction_wizard(parent, table_view):
    """Add a new transaction using a wizard format with 3 pages"""

    wizard = QWizard(parent)
    wizard.setMinimumWidth(700)  # Adjust as needed
    wizard.setWindowTitle("Add Transaction Wizard")
    # Set the wizard style to Modern - this should help with white backgrounds
    wizard.setWizardStyle(QWizard.ModernStyle)
    # Create a transparent pixmap for the banner/watermark
    transparent_pixmap = QPixmap()
    #transparent_pixmap.fill(Qt.transparent)
    wizard.setPixmap(QWizard.WatermarkPixmap, transparent_pixmap)
    wizard.setPixmap(QWizard.BannerPixmap, transparent_pixmap)
    wizard.setPixmap(QWizard.LogoPixmap, transparent_pixmap)

    # Page 1: Transaction Basic Information
    page1 = QWizardPage()
    page1.setTitle("Transaction Information")
    page1.setSubTitle("Enter the basic transaction details")

    layout1 = QVBoxLayout(page1)

    layout1.addStretch(1)

    # Description field
    desc_layout = QHBoxLayout()
    desc_layout.addWidget(QLabel("Description:"))
    description_edit = QLineEdit()
    desc_layout.addWidget(description_edit)
    layout1.addLayout(desc_layout)

    # Amount, Date and Currency fields
    details_layout = QHBoxLayout()

    details_layout.addWidget(QLabel("Total Amount:"))
    total_amount_edit = QLineEdit()
    total_amount_edit.setValidator(QDoubleValidator())
    details_layout.addWidget(total_amount_edit)

    details_layout.addWidget(QLabel("Date:"))
    date_edit = QDateEdit(QDate.currentDate())
    date_edit.setCalendarPopup(True)
    details_layout.addWidget(date_edit)

    details_layout.addWidget(QLabel("Currency:"))
    currency_combo = QComboBox()
    currencies = [curr[1] for curr in db.get_all_currencies()]
    currency_combo.addItems(currencies)
    default_index = currencies.index("EGP") if "EGP" in currencies else 0
    currency_combo.setCurrentIndex(default_index)
    details_layout.addWidget(currency_combo)

    layout1.addLayout(details_layout)

    layout1.addStretch(1)  # Add at the end

    # Register fields with the wizard
    page1.registerField("description*", description_edit)
    page1.registerField("total_amount*", total_amount_edit)
    page1.registerField("date", date_edit)
    page1.registerField("currency", currency_combo, "currentText")

    # Page 2: Credit Account Selection
    page2 = QWizardPage()
    page2.setTitle("Credit Accounts")
    page2.setSubTitle("Select accounts to credit (money goes from these accounts)")

    layout2 = QVBoxLayout(page2)

    # Container for credit lines
    credit_lines_container = QWidget()
    credit_lines_layout = QVBoxLayout(credit_lines_container)
    credit_lines_layout.setContentsMargins(0, 0, 0, 0)

    # Scroll area for credit lines
    credit_scroll = QScrollArea()
    credit_scroll.setWidgetResizable(True)
    credit_scroll.setWidget(credit_lines_container)
    #credit_scroll.setMinimumHeight(200)  # Adjust this value as needed
    layout2.addWidget(credit_scroll)

    # Add button and summary for credit lines
    buttons_layout = QHBoxLayout()
    add_credit_btn = QPushButton("Add Credit Line")
    buttons_layout.addWidget(add_credit_btn)

    credit_total_label = QLabel("Credit Total: 0.00")
    buttons_layout.addWidget(credit_total_label)
    layout2.addLayout(buttons_layout)

    # Page 3: Debit Account Selection
    page3 = QWizardPage()
    page3.setTitle("Debit Accounts")
    page3.setSubTitle("Select accounts to debit (money comes to these accounts)")

    layout3 = QVBoxLayout(page3)

    # Container for debit lines
    debit_lines_container = QWidget()
    debit_lines_layout = QVBoxLayout(debit_lines_container)
    debit_lines_layout.setContentsMargins(10, 10, 10, 10)


    # Scroll area for debit lines
    debit_scroll = QScrollArea()
    debit_scroll.setWidgetResizable(True)
    debit_scroll.setWidget(debit_lines_container)
    #debit_scroll.setMinimumHeight(200)  # Adjust this value as needed
    layout3.addWidget(debit_scroll)

    # Add button and summary for debit lines
    debit_buttons_layout = QHBoxLayout()
    add_debit_btn = QPushButton("Add Debit Line")
    debit_buttons_layout.addWidget(add_debit_btn)

    debit_total_label = QLabel("Debit Total: 0.00")
    debit_buttons_layout.addWidget(debit_total_label)
    layout3.addLayout(debit_buttons_layout)

    # Add pages to wizard
    wizard.addPage(page1)
    wizard.addPage(page2)
    wizard.addPage(page3)

    # Add a custom button to the wizard
    add_another_btn = QPushButton("Add Another Transaction")
    wizard.setButton(QWizard.CustomButton1, add_another_btn)
    wizard.setOption(QWizard.HaveCustomButton1, True)
    wizard.setButtonText(QWizard.CustomButton1, "Add Another Transaction")

    # Only show the button on the last page
    def update_custom_button(page_id):
        # Show the custom button only on the last page (index 2)
        wizard.setOption(QWizard.HaveCustomButton1, page_id == 2)

    wizard.currentIdChanged.connect(update_custom_button)

    # Connect the button to start a new transaction wizard
    def start_new_transaction():
        # This will be called when CustomButton1 is clicked
        # We need to accept the current wizard first
        wizard.accept()
        # Then start a new one
        QTimer.singleShot(100, lambda: add_transaction_wizard(parent, table_view))

    wizard.customButtonClicked.connect(start_new_transaction)

    # Lists to track line widgets
    credit_line_widgets = []
    debit_line_widgets = []

    # At the end of your wizard setup:
    def on_current_id_changed(current_id):
        if current_id == 0:  # First page
            description_edit.setFocus()
        elif current_id == 1 and credit_line_widgets:  # Credit page
            credit_line_widgets[0]['account'].setFocus()
        elif current_id == 2 and debit_line_widgets:  # Debit page
            debit_line_widgets[0]['account'].setFocus()

    wizard.currentIdChanged.connect(on_current_id_changed)

    # Set tab order for first page
    wizard.setTabOrder(description_edit, total_amount_edit)
    wizard.setTabOrder(total_amount_edit, date_edit)
    wizard.setTabOrder(date_edit, currency_combo)

    # Custom key event handler for pages
    def handle_key_press(obj, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # If on the last page, handle differently
            if wizard.currentId() == 2:  # Assuming 3 pages (0, 1, 2)
                if event.modifiers() & Qt.ControlModifier:
                    # Ctrl+Enter to finish and add new transaction
                    wizard.button(QWizard.FinishButton).click()
                    add_transaction_wizard(parent, table_view)
                else:
                    # Just finish
                    wizard.button(QWizard.FinishButton).click()
            else:
                # On other pages, proceed to next
                wizard.button(QWizard.NextButton).click()
            return True
        return False

    # Install event filter on all input widgets
    def install_event_filter(widget, filter_func):
        class KeyPressFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.KeyPress:
                    return filter_func(obj, event)
                return False

        filter_obj = KeyPressFilter(widget)
        widget.installEventFilter(filter_obj)
        return filter_obj

    # Apply to all editable widgets
    key_filters = []
    key_filters.append(install_event_filter(description_edit, handle_key_press))
    key_filters.append(install_event_filter(total_amount_edit, handle_key_press))
    key_filters.append(install_event_filter(date_edit, handle_key_press))
    key_filters.append(install_event_filter(currency_combo, handle_key_press))

    # Function to update credit total
    def update_credit_total():
        try:
            total_transaction_amount = float(total_amount_edit.text() or 0)
            credit_total = 0

            for line in credit_line_widgets:
                try:
                    credit_total += float(line['amount'].text() or 0)
                except (ValueError, TypeError):
                    pass

            # Update the label with correct formatting
            credit_total_label.setText(f"Credit Total: {credit_total:.2f}")

            # Calculate remaining amount needed
            remaining = total_transaction_amount - credit_total

            # Highlight if exceeds total amount
            if credit_total > total_transaction_amount:
                credit_total_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
                for line in credit_line_widgets:
                    line['amount'].setStyleSheet("QLineEdit { background-color: #FFE0E0; }")
            else:
                credit_total_label.setStyleSheet("")
                for line in credit_line_widgets:
                    line['amount'].setStyleSheet("")

            # Return the remaining amount for new lines
            return remaining

        except (ValueError, TypeError):
            return 0

    def update_debit_total():
        try:
            total_transaction_amount = float(total_amount_edit.text() or 0)
            debit_total = 0

            for line in debit_line_widgets:
                try:
                    debit_total += float(line['amount'].text() or 0)
                except (ValueError, TypeError):
                    pass

            # Update the label with correct formatting
            debit_total_label.setText(f"Debit Total: {debit_total:.2f}")

            # Calculate remaining amount needed
            remaining = total_transaction_amount - debit_total

            # Highlight if exceeds total amount
            if debit_total > total_transaction_amount:
                debit_total_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
                for line in debit_line_widgets:
                    line['amount'].setStyleSheet("QLineEdit { background-color: #FFE0E0; }")
            else:
                debit_total_label.setStyleSheet("")
                for line in debit_line_widgets:
                    line['amount'].setStyleSheet("")

            # Return the remaining amount for new lines
            return remaining

        except (ValueError, TypeError):
            return 0

    # Function to add a credit line
    def add_credit_line(amount=None):
        line_widget = QWidget()
        line_layout = QVBoxLayout(line_widget)
        line_layout.setContentsMargins(5, 5, 5, 5)

        # Top row with account and classification
        top_row = QHBoxLayout()

        # Account label and selection
        account_label = QLabel("Account:")
        top_row.addWidget(account_label, 1)

        # Account selection
        account_combo = QComboBox()
        accounts = [acc[1] for acc in db.get_all_accounts()]
        account_combo.addItems(accounts)
        top_row.addWidget(account_combo, 3)

        # Classification selection
        class_label = QLabel("Classification:")
        top_row.addWidget(class_label, 1)

        classification_combo = QComboBox()
        classification_combo.addItem("(None)")
        top_row.addWidget(classification_combo, 3)

        line_layout.addLayout(top_row)

        # Bottom row with amount and date
        bottom_row = QHBoxLayout()

        # Amount field
        amount_label = QLabel("Amount:")
        bottom_row.addWidget(amount_label, 1)
        amount_edit = QLineEdit()
        amount_edit.setValidator(QDoubleValidator())
        if amount:
            amount_edit.setText(str(amount))
        bottom_row.addWidget(amount_edit, 3)

        # Date field
        date_label = QLabel("Date:")
        bottom_row.addWidget(date_label, 1)

        line_date_edit = QDateEdit(date_edit.date())
        line_date_edit.setCalendarPopup(True)
        bottom_row.addWidget(line_date_edit, 3)

        # Remove button
        remove_btn = QPushButton("Remove")
        if len(credit_line_widgets) == 0:  # First line has no remove button
            remove_btn.setVisible(False)
        bottom_row.addWidget(remove_btn, 1)

        line_layout.addLayout(bottom_row)

        # Add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        line_layout.addWidget(separator)

        credit_lines_layout.addWidget(line_widget)

        # Track the widget and its components
        line_data = {
            'widget': line_widget,
            'account': account_combo,
            'classification': classification_combo,
            'amount': amount_edit,
            'date': line_date_edit,
            'remove': remove_btn
        }
        credit_line_widgets.append(line_data)

        # Connect signals
        amount_edit.textChanged.connect(update_credit_total)
        remove_btn.clicked.connect(lambda: remove_credit_line(line_data))
        account_combo.currentIndexChanged.connect(
            lambda index: update_classification_combo(classification_combo, accounts[index])
        )

        return line_data

    # Function to remove a credit line
    def remove_credit_line(line_data):
        if line_data in credit_line_widgets:
            credit_line_widgets.remove(line_data)
            line_data['widget'].deleteLater()
            update_credit_total()

    # Function to add a debit line
    def add_debit_line(amount=None):
        line_widget = QWidget()
        line_layout = QVBoxLayout(line_widget)
        line_layout.setContentsMargins(5, 5, 5, 5)

        # Top row with account and classification
        top_row = QHBoxLayout()

        # Account label and selection
        account_label = QLabel("Account:")
        top_row.addWidget(account_label, 1)

        # Account selection
        account_combo = QComboBox()
        accounts = [acc[1] for acc in db.get_all_accounts()]
        account_combo.addItems(accounts)
        top_row.addWidget(account_combo, 3)

        # Classification selection
        class_label = QLabel("Classification:")
        top_row.addWidget(class_label, 1)

        classification_combo = QComboBox()
        classification_combo.addItem("(None)")
        top_row.addWidget(classification_combo, 3)

        line_layout.addLayout(top_row)

        # Bottom row with amount and date
        bottom_row = QHBoxLayout()

        # Amount field
        amount_label = QLabel("Amount:")
        bottom_row.addWidget(amount_label, 1)

        amount_edit = QLineEdit()
        amount_edit.setValidator(QDoubleValidator())
        if amount:
            amount_edit.setText(str(amount))
        bottom_row.addWidget(amount_edit, 3)

        # Date field
        date_label = QLabel("Date:")
        bottom_row.addWidget(date_label, 1)

        line_date_edit = QDateEdit(date_edit.date())
        line_date_edit.setCalendarPopup(True)
        bottom_row.addWidget(line_date_edit, 3)

        # Remove button
        remove_btn = QPushButton("Remove")
        if len(debit_line_widgets) == 0:  # First line has no remove button
            remove_btn.setVisible(False)
        bottom_row.addWidget(remove_btn, 1)

        line_layout.addLayout(bottom_row)

        # Add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        line_layout.addWidget(separator)

        debit_lines_layout.addWidget(line_widget)

        # Track the widget and its components
        line_data = {
            'widget': line_widget,
            'account': account_combo,
            'classification': classification_combo,
            'amount': amount_edit,
            'date': line_date_edit,
            'remove': remove_btn
        }
        debit_line_widgets.append(line_data)

        # Connect signals
        amount_edit.textChanged.connect(update_debit_total)
        remove_btn.clicked.connect(lambda: remove_debit_line(line_data))
        account_combo.currentIndexChanged.connect(
            lambda index: update_classification_combo(classification_combo, accounts[index])
        )

        return line_data

    # Function to remove a debit line
    def remove_debit_line(line_data):
        if line_data in debit_line_widgets:
            debit_line_widgets.remove(line_data)
            line_data['widget'].deleteLater()
            update_debit_total()

    # Function to update classification options based on account
    def update_classification_combo(combo, account_name):
        combo.clear()
        combo.addItem("(None)")
        account_id = db.get_account_id(account_name)
        classifications = db.get_classifications_for_account(account_id)
        for classification in classifications:
            combo.addItem(classification[1])

    # Function to update credit total
    def update_credit_total():
        try:
            total_transaction_amount = float(total_amount_edit.text() or 0)
            credit_total = 0

            for line in credit_line_widgets:
                try:
                    credit_total += float(line['amount'].text() or 0)
                except (ValueError, TypeError):
                    pass

            credit_total_label.setText(f"Credit Total: {credit_total:.2f}")

            # Highlight if exceeds total amount
            if credit_total > total_transaction_amount:
                credit_total_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
                for line in credit_line_widgets:
                    line['amount'].setStyleSheet("QLineEdit { background-color: #FFE0E0; }")
            else:
                credit_total_label.setStyleSheet("")
                for line in credit_line_widgets:
                    line['amount'].setStyleSheet("")
        except (ValueError, TypeError):
            pass

    # Function to update debit total
    def update_debit_total():
        try:
            total_transaction_amount = float(total_amount_edit.text() or 0)
            debit_total = 0

            for line in debit_line_widgets:
                try:
                    debit_total += float(line['amount'].text() or 0)
                except (ValueError, TypeError):
                    pass

            debit_total_label.setText(f"Debit Total: {debit_total:.2f}")

            # Highlight if exceeds total amount
            if debit_total > total_transaction_amount:
                debit_total_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
                for line in debit_line_widgets:
                    line['amount'].setStyleSheet("QLineEdit { background-color: #FFE0E0; }")
            else:
                debit_total_label.setStyleSheet("")
                for line in debit_line_widgets:
                    line['amount'].setStyleSheet("")
        except (ValueError, TypeError):
            pass

    # Connect events for adding lines
    add_credit_btn.clicked.connect(lambda: add_credit_line(update_credit_total()))
    add_debit_btn.clicked.connect(lambda: add_debit_line(update_debit_total()))

    # Update date fields when main date changes
    def update_line_dates():
        new_date = date_edit.date()
        for line in credit_line_widgets:
            line['date'].setDate(new_date)
        for line in debit_line_widgets:
            line['date'].setDate(new_date)

    date_edit.dateChanged.connect(update_line_dates)

    # Add default lines when pages are shown
    def on_current_id_changed(current_id):
        if current_id == 1 and not credit_line_widgets:  # Credit page
            try:
                total_amount = float(total_amount_edit.text() or 0)
                if total_amount > 0:
                    add_credit_line(total_amount)
            except (ValueError, TypeError):
                add_credit_line()
        elif current_id == 2 and not debit_line_widgets:  # Debit page
            try:
                total_amount = float(total_amount_edit.text() or 0)
                if total_amount > 0:
                    add_debit_line(total_amount)
            except (ValueError, TypeError):
                add_debit_line()

    wizard.currentIdChanged.connect(on_current_id_changed)

    # Final validation before accepting
    def validate_before_finish():
        try:
            # Calculate totals
            credit_total = 0
            for line in credit_line_widgets:
                try:
                    credit_total += float(line['amount'].text() or 0)
                except (ValueError, TypeError):
                    pass

            debit_total = 0
            for line in debit_line_widgets:
                try:
                    debit_total += float(line['amount'].text() or 0)
                except (ValueError, TypeError):
                    pass

            # Check if transaction is balanced
            if abs(credit_total - debit_total) > 0.01:
                QMessageBox.warning(wizard, "Unbalanced Transaction",
                                    f"Transaction is not balanced.\nCredit: {credit_total:.2f}\nDebit: {debit_total:.2f}")
                return False

            # Ensure we have at least one credit and one debit line
            if not credit_line_widgets or not debit_line_widgets:
                QMessageBox.warning(wizard, "Incomplete Transaction",
                                    "At least one credit and one debit line are required.")
                return False

            return True
        except Exception as e:
            QMessageBox.critical(wizard, "Error", f"Validation error: {str(e)}")
            return False

    wizard.button(QWizard.FinishButton).clicked.connect(validate_before_finish)

    # Execute the wizard
    if wizard.exec_() == QWizard.Accepted:
        try:
            # Retrieve data from wizard
            description = description_edit.text()
            total_amount = float(total_amount_edit.text() or 0)
            date_value = date_edit.date().toString("yyyy-MM-dd")
            currency_id = db.get_currency_id(currency_combo.currentText())

            # Prepare credit lines data
            credit_lines = []
            for line in credit_line_widgets:
                try:
                    amount = float(line['amount'].text() or 0)
                    if amount <= 0:
                        continue  # Skip lines with zero or negative amounts

                    account_id = db.get_account_id(line['account'].currentText())
                    line_date = line['date'].date().toString("yyyy-MM-dd")
                    classification_name = line['classification'].currentText()
                    classification_id = None

                    if classification_name != "(None)":
                        classification = db.get_classification_by_name(classification_name)
                        if classification:
                            classification_id = classification[0]

                    credit_lines.append({
                        'account_id': account_id,
                        'amount': amount,
                        'date': line_date,
                        'classification_id': classification_id
                    })
                except (ValueError, TypeError):
                    pass

            # Prepare debit lines data
            debit_lines = []
            for line in debit_line_widgets:
                try:
                    amount = float(line['amount'].text() or 0)
                    if amount <= 0:
                        continue  # Skip lines with zero or negative amounts

                    account_id = db.get_account_id(line['account'].currentText())
                    line_date = line['date'].date().toString("yyyy-MM-dd")
                    classification_name = line['classification'].currentText()
                    classification_id = None

                    if classification_name != "(None)":
                        classification = db.get_classification_by_name(classification_name)
                        if classification:
                            classification_id = classification[0]

                    debit_lines.append({
                        'account_id': account_id,
                        'amount': amount,
                        'date': line_date,
                        'classification_id': classification_id
                    })
                except (ValueError, TypeError):
                    pass

            # Final verification
            credit_total = sum(line['amount'] for line in credit_lines)
            debit_total = sum(line['amount'] for line in debit_lines)

            if abs(credit_total - debit_total) > 0.01:
                raise ValueError(f"Transaction is not balanced. Credit: {credit_total:.2f}, Debit: {debit_total:.2f}")

            if not credit_lines or not debit_lines:
                raise ValueError("At least one credit and one debit line are required")

            # Save transaction and lines
            new_transaction_id = save_complete_transaction(
                description,
                currency_id,
                credit_lines,
                debit_lines
            )

            # Reload transactions and select the new one
            load_transactions(table_view, select_transaction_id=new_transaction_id)

            # Force transaction selection update
            if hasattr(table_view, '_on_transaction_selected'):
                table_view._on_transaction_selected()

            QMessageBox.information(parent, "Success", "Transaction added successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add transaction: {str(e)}")

def save_complete_transaction(description, currency_id, credit_lines, debit_lines):
    """Save a complete transaction with all its lines in one operation"""
    try:
        # Start a transaction
        db.begin_transaction()

        # Insert transaction
        transaction_id = db.insert_transaction(description, currency_id)

        # Insert credit lines
        for line in credit_lines:
            db.insert_transaction_line(
                transaction_id,
                line['account_id'],
                debit=None,
                credit=line['amount'],
                date=line['date'],
                classification_id=line['classification_id']
            )

        # Insert debit lines
        for line in debit_lines:
            db.insert_transaction_line(
                transaction_id,
                line['account_id'],
                debit=line['amount'],
                credit=None,
                date=line['date'],
                classification_id=line['classification_id']
            )

        # Commit transaction
        db.commit_transaction()

        return transaction_id
    except Exception as e:
        # Rollback on error
        db.rollback_transaction()
        raise e

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

            # Update transaction
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
            # Delete transaction
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