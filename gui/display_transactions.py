from PyQt5.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QTableView, QAction, QMessageBox,
                             QHeaderView, QWidget, QToolBar, QSplitter, QLabel, QHBoxLayout, QPushButton,
                             QDialog, QGroupBox, QGridLayout, QLineEdit, QDateEdit,QComboBox, QDialogButtonBox,
                             QScrollArea, QFrame, QCompleter)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon, QDoubleValidator, QPixmap
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QDate, QTimer, QObject, QEvent
from gui.dialog_utils import show_entity_dialog
from gui.import_utils import import_csv_wizard
from database import db
import datetime

# Add these new cache functions
# Cache for frequently accessed data
_account_cache = {}
_currency_cache = {}
_classification_cache = {}


def get_cached_account_name(account_id):
    """Get account name from cache or load it from database"""
    if account_id not in _account_cache:
        account_data = db.get_account_by_id(account_id)
        _account_cache[account_id] = account_data[1] if account_data else "Unknown"
    return _account_cache[account_id]


def get_cached_currency_name(currency_id):
    """Get currency name from cache or load it from database"""
    if currency_id not in _currency_cache:
        currency_data = db.get_currency_by_id(currency_id)
        _currency_cache[currency_id] = currency_data[1] if currency_data else "Unknown"
    return _currency_cache[currency_id]


def get_cached_classification_name(classification_id):
    """Get classification name from cache or load it from database"""
    if classification_id is None:
        return ""
    if classification_id not in _classification_cache:
        classification_data = db.get_classification_by_id(classification_id)
        _classification_cache[classification_id] = classification_data[1] if classification_data else ""
    return _classification_cache[classification_id]


def warm_cache():
    """Preload common data into cache"""
    # Preload all accounts
    for account in db.get_all_accounts():
        _account_cache[account[0]] = account[1]

    # Preload all currencies
    for currency in db.get_all_currencies():
        _currency_cache[currency[0]] = currency[1]

    # Preload all classifications
    cursor = db.conn.cursor()
    cursor.execute("SELECT id, name FROM classifications")
    for classification in cursor.fetchall():
        _classification_cache[classification[0]] = classification[1]


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

# Add this class for handling focus events
class FocusEventFilter(QObject):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            self.callback()
        return False

def get_recent_descriptions(limit=100):
    """Get the most recent unique transaction descriptions, limited to prevent performance issues"""
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT DISTINCT description FROM transactions 
        ORDER BY id DESC 
        LIMIT ?
    """, (limit,))
    return [row[0] for row in cursor.fetchall()]


def make_combo_editable(combo, items):
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.NoInsert)

    # Create a completer
    completer = QCompleter(items, combo)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    combo.setCompleter(completer)

    # Set empty text initially instead of showing first item
    combo.setCurrentText("")

    # Show dropdown and handle focus behavior
    class ComboFocusEventFilter(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.FocusIn:
                # Show all dropdown options when focused
                QTimer.singleShot(10, combo.showPopup)
                # Clear the text to ensure user can see all options
                combo.lineEdit().clear()
            return False

    # Install the event filter
    focus_filter = ComboFocusEventFilter()
    combo.lineEdit().installEventFilter(focus_filter)

    # Store the filter as a property to prevent garbage collection
    combo.setProperty("focus_filter", focus_filter)

    return combo


def update_summary_counts(transactions_table, debit_table, credit_table,
                          transactions_count_label, credit_lines_count_label, debit_lines_count_label,
                          total_count=None, page_size=None, current_page=None):
    """Update the summary counts for transactions and lines"""
    # Count displayed transactions
    if transactions_table.model():
        displayed_count = transactions_table.model().rowCount()

        # If we have pagination information, show comprehensive count
        if total_count is not None:
            # Format is consistent regardless of page size
            if page_size is None:
                transactions_count_label.setText(f"Total Transactions: {displayed_count} of {total_count}")
            else:
                start_item = (current_page - 1) * page_size + 1 if displayed_count > 0 else 0
                end_item = start_item + displayed_count - 1 if displayed_count > 0 else 0
                transactions_count_label.setText(
                    f"Total Transactions: {displayed_count} ({start_item}-{end_item} of {total_count})")
        else:
            transactions_count_label.setText(f"Total Transactions: {displayed_count}")
    else:
        transactions_count_label.setText("Total Transactions: 0")

    # Count credit lines
    if credit_table.model():
        credit_lines_count = credit_table.model().rowCount()
        credit_lines_count_label.setText(f"Total Credit Lines: {credit_lines_count}")
    else:
        credit_lines_count_label.setText("Total Credit Lines: 0")

    # Count debit lines
    if debit_table.model():
        debit_lines_count = debit_table.model().rowCount()
        debit_lines_count_label.setText(f"Total Debit Lines: {debit_lines_count}")
    else:
        debit_lines_count_label.setText("Total Debit Lines: 0")

def display_transactions(content_frame, toolbar):
    # Warm up the cache with frequently used data
    warm_cache()

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

    # Add label above transactions table
    transactions_header = QLabel("<h3>Transactions</h3>")
    transactions_layout.addWidget(transactions_header)

    # Create table view for transactions
    transactions_table = QTableView()
    transactions_layout.addWidget(transactions_table)
    transactions_table.setAlternatingRowColors(True)

    splitter.addWidget(transactions_widget)

    # Make transactions table non-editable
    transactions_table.setEditTriggers(QTableView.NoEditTriggers)

    # Select entire rows
    transactions_table.setSelectionBehavior(QTableView.SelectRows)



    # Create bottom widget for transaction lines
    lines_widget = QWidget()
    lines_layout = QVBoxLayout(lines_widget)
    lines_widget.setLayout(lines_layout)
    splitter.addWidget(lines_widget)

    # Add after the transactions table but before the lines widget
    pagination_widget = QWidget()
    pagination_layout = QHBoxLayout(pagination_widget)
    pagination_widget.setLayout(pagination_layout)

    # Add pagination controls
    prev_page_btn = QPushButton("Previous")
    page_label = QLabel("Page 1")
    next_page_btn = QPushButton("Next")
    page_size_combo = QComboBox()
    page_size_combo.addItems(["20", "50", "100", "All"])
    page_size_combo.setMinimumWidth(70)  # Add this line

    pagination_layout.addWidget(prev_page_btn)
    pagination_layout.addWidget(page_label)
    pagination_layout.addWidget(next_page_btn)
    pagination_layout.addWidget(QLabel("Items per page:"))
    pagination_layout.addWidget(page_size_combo)
    pagination_layout.addStretch()

    # Add to main layout
    transactions_layout.addWidget(pagination_widget)

    # Connect pagination controls
    def go_to_prev_page():
        current_page = getattr(transactions_table, 'current_page', 1)
        if current_page > 1:
            load_transactions(transactions_table, page=current_page - 1,
                              page_size=transactions_table.page_size,
                              filter_params=getattr(transactions_table, 'filter_params', None))
            transactions_table.current_page = current_page - 1

            # Update pagination info explicitly after loading transactions
            update_pagination_info()

    def go_to_next_page():
        current_page = getattr(transactions_table, 'current_page', 1)
        load_transactions(transactions_table, page=current_page + 1,
                          page_size=transactions_table.page_size,
                          filter_params=getattr(transactions_table, 'filter_params', None))
        transactions_table.current_page = current_page + 1

        # Update pagination info explicitly
        update_pagination_info()

    def change_page_size():
        selected_page_size = page_size_combo.currentText()
        if selected_page_size == "All":
            page_size = None
        else:
            page_size = int(selected_page_size)

        # Store the current filter parameters
        filter_params = getattr(transactions_table, 'filter_params', None)

        # Store new pagination values - Do this BEFORE loading transactions
        transactions_table.current_page = 1
        transactions_table.page_size = page_size

        # Load transactions with the new page size
        load_transactions(transactions_table, page=1, page_size=page_size, filter_params=filter_params)

        # Get the total count for the summary
        total_count = db.get_transaction_count(filter_params)
        displayed_count = transactions_table.model().rowCount() if transactions_table.model() else 0

        # Force selection to update (this should trigger on_transaction_selected)
        if transactions_table.model() and transactions_table.model().rowCount() > 0:
            transactions_table.selectRow(0)

        # Explicitly update the summary with the correct counts
        update_summary_counts(transactions_table, debit_table, credit_table,
                              transactions_count_label, credit_lines_count_label, debit_lines_count_label,
                              total_count, page_size, 1)  # 1 for page number since we reset to page 1

        # Update the pagination control text
        if page_size is None:
            page_text = "Page: All"
            total_pages = 1
        else:
            total_pages = max(1, (total_count + page_size - 1) // page_size)
            page_text = f"Page 1 of {total_pages}"

        page_label.setText(page_text)

        # Enable/disable navigation buttons
        prev_page_btn.setEnabled(False)  # First page, so disable previous
        next_page_btn.setEnabled(page_size is not None and total_pages > 1)

    prev_page_btn.clicked.connect(go_to_prev_page)
    next_page_btn.clicked.connect(go_to_next_page)
    page_size_combo.currentIndexChanged.connect(change_page_size)

    # Create sections for debit and credit lines

    credit_label = QLabel("<h3>Credit Lines</h3>")
    lines_layout.addWidget(credit_label)

    # Create credit lines table
    credit_table = QTableView()
    lines_layout.addWidget(credit_table)
    credit_table.setAlternatingRowColors(True)

    # Make credit lines table non-editable
    credit_table.setEditTriggers(QTableView.NoEditTriggers)

    # Select entire rows
    credit_table.setSelectionBehavior(QTableView.SelectRows)

    debit_label = QLabel("<h3>Debit Lines</h3>")
    lines_layout.addWidget(debit_label)

    # Create debit lines table
    debit_table = QTableView()
    lines_layout.addWidget(debit_table)
    debit_table.setAlternatingRowColors(True)

    # Make debit lines table non-editable
    debit_table.setEditTriggers(QTableView.NoEditTriggers)

    # Select entire rows
    debit_table.setSelectionBehavior(QTableView.SelectRows)

    # Add summary bar below all tables
    summary_widget = QWidget()
    summary_layout = QHBoxLayout(summary_widget)
    summary_widget.setLayout(summary_layout)

    # Set a maximum height for the summary bar
    summary_widget.setMaximumHeight(50)

    # Create labels for the summary information
    transactions_count_label = QLabel("Total Transactions: 0")
    credit_lines_count_label = QLabel("Total Credit Lines: 0")
    debit_lines_count_label = QLabel("Total Debit Lines: 0")

    # Add labels to the summary layout with some spacing
    summary_layout.addWidget(transactions_count_label)
    summary_layout.addSpacing(20)
    summary_layout.addWidget(credit_lines_count_label)
    summary_layout.addSpacing(20)
    summary_layout.addWidget(debit_lines_count_label)
    summary_layout.addStretch(1)  # Push everything to the left

    # Add the summary widget to the main layout
    layout.addWidget(summary_widget)

    # Hide lines widget initially (will show when transaction is selected)
    lines_widget.setVisible(False)

    # Enable sorting for all tables
    transactions_table.setSortingEnabled(True)
    debit_table.setSortingEnabled(True)
    credit_table.setSortingEnabled(True)

    #toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)

    # Add toolbar buttons for main transactions
    add_action = QAction(QIcon('icons/add.png'), "Add", toolbar)
    import_csv_action = QAction(QIcon('icons/import.png'), "Import CSV", toolbar)
    edit_action = QAction(QIcon('icons/edit.png'), "Edit", toolbar)
    delete_action = QAction(QIcon('icons/delete.png'), "Delete", toolbar)
    filter_action = QAction(QIcon('icons/filter.png'), "Filter", toolbar)
    reset_filter_action = QAction(QIcon('icons/clear.png'), "Reset Filter", toolbar)
    export_action = QAction(QIcon('icons/export.png'), "Export", toolbar)


    toolbar.insertAction(actions_to_keep[0], add_action)
    toolbar.insertAction(actions_to_keep[0], import_csv_action)
    toolbar.insertAction(actions_to_keep[0], edit_action)
    toolbar.insertAction(actions_to_keep[0], delete_action)
    toolbar.insertAction(actions_to_keep[0], filter_action)
    toolbar.insertAction(actions_to_keep[0], reset_filter_action)
    toolbar.insertAction(actions_to_keep[0], export_action)

    # Connect actions for main transactions
    add_action.triggered.connect(lambda: add_transaction_wizard(content_frame, transactions_table))
    import_csv_action.triggered.connect(lambda: on_import_csv(content_frame, transactions_table))
    edit_action.triggered.connect(lambda: edit_transaction_wizard(content_frame, transactions_table))
    delete_action.triggered.connect(lambda: delete_transaction(content_frame, transactions_table))
    filter_action.triggered.connect(lambda: filter_transactions(content_frame, transactions_table))
    reset_filter_action.triggered.connect(lambda: reset_transaction_filters(content_frame, transactions_table))
    export_action.triggered.connect(lambda: export_transactions_data(content_frame, transactions_table))


    def update_pagination_info():
        current_page = getattr(transactions_table, 'current_page', 1)
        page_size = getattr(transactions_table, 'page_size', None)  # Default to None instead of 20
        filter_params = getattr(transactions_table, 'filter_params', None)

        # Get total count
        total_count = db.get_transaction_count(filter_params)

        # Calculate total pages - handle page_size = None (All records)
        if page_size is None:
            total_pages = 1
            page_text = "Page: All"
        else:
            total_pages = max(1, (total_count + page_size - 1) // page_size)
            page_text = f"Page {current_page} of {total_pages}"

        # Update label
        page_label.setText(page_text)

        # Enable/disable buttons
        prev_page_btn.setEnabled(current_page > 1)
        next_page_btn.setEnabled(page_size is not None and current_page < total_pages)

        # Update the summary count with complete information
        update_summary_counts(transactions_table, debit_table, credit_table,
                              transactions_count_label, credit_lines_count_label, debit_lines_count_label,
                              total_count, page_size, current_page)

    # Store the update_pagination_info function on the table_view
    transactions_table.update_pagination_info = update_pagination_info

    # Create function to handle selection changes in the transactions table
    def on_transaction_selected():
        row_data = get_selected_row_data(transactions_table)
        if row_data:
            transaction_id = int(row_data["ID"])

            # Show loading indicator
            lines_widget.setVisible(True)

            # Use QTimer to allow UI to update before loading
            QTimer.singleShot(10, lambda: load_transaction_details(transaction_id))

    def load_transaction_details(transaction_id):
        # Load detailed transaction data
        load_transaction_lines(debit_table, transaction_id, is_debit=True)
        load_transaction_lines(credit_table, transaction_id, is_debit=False)

        # Get pagination info for summary update
        current_page = getattr(transactions_table, 'current_page', 1)
        page_size = getattr(transactions_table, 'page_size', None)
        filter_params = getattr(transactions_table, 'filter_params', None)
        total_count = db.get_transaction_count(filter_params)

        # Update summary counts with complete info
        update_summary_counts(transactions_table, debit_table, credit_table,
                              transactions_count_label, credit_lines_count_label, debit_lines_count_label,
                              total_count, page_size, current_page)

    # Store the function on the table_view for later reconnection
    transactions_table._on_transaction_selected = on_transaction_selected

    # Connect selection change signal - Modified to handle None selectionModel
    if transactions_table.selectionModel():
        transactions_table.selectionModel().selectionChanged.connect(on_transaction_selected)
    else:
        # If selection model doesn't exist yet, use a short timer to try again
        QTimer.singleShot(50,
                          lambda: transactions_table.selectionModel().selectionChanged.connect(on_transaction_selected)
                          if transactions_table.selectionModel() else None)

    # Set sensible initial sizes for the splitter
    splitter.setSizes([500, 300])

    # Load initial transaction data
    page_size = page_size_combo.currentText()
    if page_size == "All":
        initial_page_size = None
    else:
        initial_page_size = int(page_size)

    load_transactions(transactions_table, page=1, page_size=initial_page_size)

    # Explicitly update pagination info after initial load to ensure summary shows complete information
    update_pagination_info()


def filter_categories(parent, table_view):
    # Placeholder for filter functionality
    # Will be implemented in a later step
    QMessageBox.information(parent, "Filter", "Filter functionality will be implemented soon.")


def export_transactions_data(parent, transactions_table):
    """
    Export all filtered transactions data with summarized credit and debit information,
    regardless of pagination. Includes unique account:classification pairs.
    """
    from gui.export_utils import export_table_data

    # Get current filter parameters from the table
    filter_params = getattr(transactions_table, 'filter_params', None)

    # Create a temporary table view for export with enhanced columns
    temp_table = QTableView()
    temp_model = QStandardItemModel()

    # Set headers including credit and debit summaries
    temp_model.setHorizontalHeaderLabels([
        "ID", "Date", "Description", "Amount", "Currency",
        "Credit Accounts", "Debit Accounts"
    ])

    # Get ALL transactions that match the current filter (ignoring pagination)
    transactions = get_transactions_with_summary(limit=None, offset=0, filter_params=filter_params)

    if not transactions:
        QMessageBox.information(parent, "Export Info", "No data to export.")
        return

    # Process all transactions
    for transaction in transactions:
        transaction_id = transaction['id']
        date = transaction['date']
        description = transaction['description']
        amount = transaction['amount']
        currency = transaction['currency']

        # Create row items
        id_item = QStandardItem(str(transaction_id))
        date_item = QStandardItem(date)
        description_item = QStandardItem(description)
        amount_item = QStandardItem(f"{amount:.2f}")
        currency_item = QStandardItem(currency)

        # Set alignment for ID and amount
        id_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Get transaction lines for credit and debit summaries
        lines = db.get_transaction_lines(transaction_id)

        # Use sets to track unique account:classification pairs
        credit_accounts = set()
        debit_accounts = set()

        for line in lines:
            account_id = line[2]
            debit = line[3] if line[3] else 0
            credit = line[4] if line[4] else 0
            classification_id = line[7]

            # Get account name
            account_name = get_cached_account_name(account_id)

            # Get classification name if available
            classification_name = get_cached_classification_name(classification_id)

            # Create account + classification text
            account_text = account_name
            if classification_name:
                account_text += f": {classification_name}"

            if credit > 0:
                credit_accounts.add(account_text)
            elif debit > 0:
                debit_accounts.add(account_text)

        # Create items for credit and debit summaries
        # Join with line breaks which will work better for wrapping in PDF
        credit_summary = QStandardItem("\n".join(sorted(credit_accounts)))
        debit_summary = QStandardItem("\n".join(sorted(debit_accounts)))

        # Add all items to the row
        temp_model.appendRow([
            id_item, date_item, description_item, amount_item, currency_item,
            credit_summary, debit_summary
        ])

    # Set the model to the temporary table
    temp_table.setModel(temp_model)

    # Export the data (using our existing PDF export with word wrap support)
    export_table_data(parent, temp_table, "transactions_export", "Transactions Journal")


def load_transactions(table_view, page=1, page_size=None, filter_params=None, select_transaction_id=None):
    # Calculate offset
    offset = (page - 1) * page_size if page_size else 0

    # Store the current page and page size on the table_view for reference
    table_view.current_page = page
    table_view.page_size = page_size
    table_view.filter_params = filter_params

    """Load transactions into the table view"""
    # Store the on_transaction_selected function for reconnection
    on_transaction_selected = None
    if hasattr(table_view, '_on_transaction_selected'):
        on_transaction_selected = table_view._on_transaction_selected


    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["ID", "Date", "Description", "Amount", "Currency"])

    # Get transactions from database with appropriate limit
    actual_limit = page_size  # Use the page_size as the limit
    transactions = get_transactions_with_summary(actual_limit, offset, filter_params)

    # Rest of your existing code

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

    # Reconnect the selection change signal - Modified to handle None selectionModel
    if on_transaction_selected:
        table_view._on_transaction_selected = on_transaction_selected
        # Only connect if the selection model exists
        if table_view.selectionModel():
            table_view.selectionModel().selectionChanged.connect(on_transaction_selected)
        else:
            # If selection model doesn't exist yet, use a short timer to try again
            QTimer.singleShot(50, lambda: table_view.selectionModel().selectionChanged.connect(on_transaction_selected)
            if table_view.selectionModel() else None)

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

    # At the end of load_transactions function, add:
    if hasattr(table_view, 'update_pagination_info'):
        table_view.update_pagination_info()

def get_transactions_with_summary(limit=20, offset=0, filter_params=None):
    """Get transactions from database with summary information"""
    # Build the query dynamically based on filters
    base_query = """
        SELECT tl.transaction_id, tl.date, tl.debit, tl.account_id
        FROM transaction_lines tl
    """

    join_clause = ""
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
            join_clause = " JOIN transactions t ON tl.transaction_id = t.id"
            where_clauses.append("t.description LIKE ?")
            params.append(f"%{filter_params['description']}%")

    # Build the filtered lines query
    filtered_query = base_query + join_clause

    # Add WHERE clause if we have conditions
    if where_clauses:
        filtered_query += " WHERE " + " AND ".join(where_clauses)

    # Main query using the filtered results
    query = f"""
        WITH filtered_lines AS ({filtered_query})
        SELECT t.id, t.description, t.currency_id, 
               SUM(IFNULL(fl.debit, 0)) as total_debit,
               MIN(fl.date) as earliest_date,
               COUNT(fl.transaction_id) as line_count
        FROM transactions t
        JOIN filtered_lines fl ON t.id = fl.transaction_id
        GROUP BY t.id, t.description, t.currency_id 
        ORDER BY earliest_date DESC
    """

    # Apply limit and offset
    if limit is not None:
        query += f" LIMIT {limit} OFFSET {offset}"
    elif offset > 0:  # If no limit but we have offset
        query += f" LIMIT -1 OFFSET {offset}"  # -1 means all records in SQLite

    # Execute the query
    cursor = db.conn.cursor()
    cursor.execute(query, params)
    transactions_data = cursor.fetchall()

    # Process results as before
    result = []
    for data in transactions_data:
        transaction_id = data[0]
        description = data[1]
        currency_id = data[2]
        total_debit = data[3] or 0
        earliest_date = data[4] or "N/A"

        # Get currency name from cache
        currency_name = get_cached_currency_name(currency_id)

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

        # Get account name from cache
        account_name = get_cached_account_name(account_id)

        # Get classification name if available
        classification_name = get_cached_classification_name(classification_id)

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


def get_all_descriptions():
    cursor = db.conn.cursor()
    cursor.execute("SELECT DISTINCT description FROM transactions")
    return [row[0] for row in cursor.fetchall()]

def add_transaction_wizard(parent, table_view, edit_mode=False, transaction_id=None,
                          transaction_data=None, credit_lines_data=None, debit_lines_data=None):
    """Add or edit a transaction using a wizard format with 3 pages"""

    wizard = QWizard(parent)
    wizard.setMinimumWidth(700)
    wizard.setWindowTitle("Add Transaction Wizard" if not edit_mode else "Edit Transaction Wizard")
    wizard.setWizardStyle(QWizard.ModernStyle)

    # Create a transparent pixmap for the banner/watermark
    transparent_pixmap = QPixmap()
    #transparent_pixmap.fill(Qt.transparent)
    wizard.setPixmap(QWizard.WatermarkPixmap, transparent_pixmap)
    wizard.setPixmap(QWizard.BannerPixmap, transparent_pixmap)
    wizard.setPixmap(QWizard.LogoPixmap, transparent_pixmap)

    # Store edit mode information
    wizard.edit_mode = edit_mode
    wizard.transaction_id = transaction_id
    # Add properties to store line data
    wizard.stored_credit_lines = credit_lines_data
    wizard.stored_debit_lines = debit_lines_data

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
    description_completer = QCompleter(get_recent_descriptions())
    description_completer.setCaseSensitivity(Qt.CaseInsensitive)
    description_completer.setFilterMode(Qt.MatchContains)
    description_edit.setCompleter(description_completer)
    desc_layout.addWidget(description_edit)
    layout1.addLayout(desc_layout)

    # If editing, pre-fill description
    if edit_mode and transaction_data:
        description_edit.setText(transaction_data['description'])

    # Amount, Date and Currency fields
    details_layout = QGridLayout()

    details_layout.addWidget(QLabel("Total Amount:"), 0, 0)
    total_amount_edit = QLineEdit()
    total_amount_edit.setValidator(QDoubleValidator())
    total_amount_edit.setMaximumWidth(150)
    details_layout.addWidget(total_amount_edit, 0, 1)

    details_layout.addWidget(QLabel("Date:"), 0, 2)
    date_edit = QDateEdit(QDate.currentDate())
    date_edit.setCalendarPopup(True)
    details_layout.addWidget(date_edit, 0, 3)

    details_layout.addWidget(QLabel("Currency:"), 0, 4)
    currency_combo = QComboBox()
    currencies = [curr[1] for curr in db.get_all_currencies()]
    currency_combo.addItems(currencies)

    # If editing, pre-fill currency and calculate total
    if edit_mode and transaction_data:
        # Set currency
        currency_index = currencies.index(transaction_data['currency_name']) if transaction_data[
                                                                                    'currency_name'] in currencies else 0
        currency_combo.setCurrentIndex(currency_index)

        # Calculate total amount from transaction lines
        total_amount = 0
        if debit_lines_data:
            for line in debit_lines_data:
                total_amount += line['amount']

        # Set the total amount
        total_amount_edit.setText(f"{total_amount:.2f}")

        # Create a proper validation function
        def validate_wizard_fields():
            # Check if both mandatory fields have content
            has_description = bool(description_edit.text().strip())
            has_amount = False
            try:
                amount = float(total_amount_edit.text() or 0)
                has_amount = amount > 0
            except (ValueError, TypeError):
                has_amount = False

            # Only enable the Next button if both fields are valid
            wizard.button(QWizard.NextButton).setEnabled(has_description and has_amount)

        # Store the original buttons
        def fix_back_button_navigation():
            # When navigating back to page 1, ensure Next button is properly enabled
            current_id = wizard.currentId()
            if current_id == 0 and edit_mode:  # We're on page 1 (index 0)
                # Re-run our validation to fix the Next button
                validate_wizard_fields()

        def on_page_changed(page_id):
            if page_id == 1 and edit_mode:  # Credit page
                # Only do this in edit mode
                QTimer.singleShot(100, populate_credit_lines)
            elif page_id == 2 and edit_mode:  # Debit page
                # Only do this in edit mode
                QTimer.singleShot(100, populate_debit_lines)

        wizard.currentIdChanged.connect(on_page_changed)

        # Now add these functions inside add_transaction_wizard:
        def populate_credit_lines():
            # Clear any existing credit lines first
            for widget in credit_line_widgets:
                widget['widget'].deleteLater()
            credit_line_widgets.clear()

            # Add stored credit lines
            if wizard.stored_credit_lines:
                for line in wizard.stored_credit_lines:
                    line_data = add_credit_line(amount=line['amount'])

                    # Directly set values without triggering signals
                    line_data['account'].blockSignals(True)
                    line_data['account'].setCurrentText(line['account_name'])
                    line_data['account'].blockSignals(False)

                    # Now manually set up classifications
                    account_id = line['account_id']
                    classifications = db.get_classifications_for_account(account_id)

                    line_data['classification'].blockSignals(True)
                    line_data['classification'].clear()

                    if classifications:
                        for classification in classifications:
                            line_data['classification'].addItem(classification[1])

                        line_data['classification'].setEditable(True)

                        if line.get('classification_name'):
                            line_data['classification'].setCurrentText(line['classification_name'])
                    else:
                        line_data['classification'].addItem("(None)")

                    line_data['classification'].blockSignals(False)

                # Update totals
                update_credit_total()

        def populate_debit_lines():
            # Clear any existing debit lines first
            for widget in debit_line_widgets:
                widget['widget'].deleteLater()
            debit_line_widgets.clear()

            # Add stored debit lines
            if wizard.stored_debit_lines:
                for line in wizard.stored_debit_lines:
                    line_data = add_debit_line(amount=line['amount'])

                    # Directly set values without triggering signals
                    line_data['account'].blockSignals(True)
                    line_data['account'].setCurrentText(line['account_name'])
                    line_data['account'].blockSignals(False)

                    # Now manually set up classifications
                    account_id = line['account_id']
                    classifications = db.get_classifications_for_account(account_id)

                    line_data['classification'].blockSignals(True)
                    line_data['classification'].clear()

                    if classifications:
                        for classification in classifications:
                            line_data['classification'].addItem(classification[1])

                        line_data['classification'].setEditable(True)

                        if line.get('classification_name'):
                            line_data['classification'].setCurrentText(line['classification_name'])
                    else:
                        line_data['classification'].addItem("(None)")

                    line_data['classification'].blockSignals(False)

                # Update totals
                update_debit_total()

        # Connect to page changed signal
        wizard.currentIdChanged.connect(fix_back_button_navigation)

        # Connect validation to text changes to maintain field validation
        description_edit.textChanged.connect(validate_wizard_fields)
        total_amount_edit.textChanged.connect(validate_wizard_fields)

        # Call validation after a delay to ensure all initial values are set
        QTimer.singleShot(200, validate_wizard_fields)

        # Find the earliest date in the transaction lines
        earliest_date = None
        all_lines = []
        if credit_lines_data:
            all_lines.extend(credit_lines_data)
        if debit_lines_data:
            all_lines.extend(debit_lines_data)

        for line in all_lines:
            line_date = line['date']
            date_obj = datetime.datetime.strptime(line_date, "%Y-%m-%d").date()
            if not earliest_date or date_obj < earliest_date:
                earliest_date = date_obj

        if earliest_date:
            date_edit.setDate(QDate(earliest_date.year, earliest_date.month, earliest_date.day))
    else:
        # Default to EGP for new transactions
        default_index = currencies.index("EGP") if "EGP" in currencies else 0
        currency_combo.setCurrentIndex(default_index)

    details_layout.addWidget(currency_combo, 0, 5)
    layout1.addLayout(details_layout)
    layout1.addStretch(1)

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
    layout2.addWidget(credit_scroll)

    # Add button and summary for credit lines
    buttons_layout = QHBoxLayout()
    add_credit_btn = QPushButton("Add Credit Line")
    buttons_layout.addWidget(add_credit_btn)

    credit_total_label = QLabel("Credit Total: 0.00")
    buttons_layout.addWidget(credit_total_label)
    transaction_total_credit_label = QLabel("Transaction Total: 0.00")
    buttons_layout.addWidget(transaction_total_credit_label)
    layout2.addLayout(buttons_layout)

    # Page 3: Debit Account Selection
    page3 = QWizardPage()
    page3.setTitle("Debit Accounts")
    page3.setSubTitle("Select accounts to debit (money comes to these accounts)")

    layout3 = QVBoxLayout(page3)

    # Container for debit lines
    debit_lines_container = QWidget()
    debit_lines_layout = QVBoxLayout(debit_lines_container)
    debit_lines_layout.setContentsMargins(0, 0, 0, 0)

    # Scroll area for debit lines
    debit_scroll = QScrollArea()
    debit_scroll.setWidgetResizable(True)
    debit_scroll.setWidget(debit_lines_container)
    layout3.addWidget(debit_scroll)

    # Add button and summary for debit lines
    debit_buttons_layout = QHBoxLayout()
    add_debit_btn = QPushButton("Add Debit Line")
    debit_buttons_layout.addWidget(add_debit_btn)

    debit_total_label = QLabel("Debit Total: 0.00")
    debit_buttons_layout.addWidget(debit_total_label)
    transaction_total_debit_label = QLabel("Transaction Total: 0.00")
    debit_buttons_layout.addWidget(transaction_total_debit_label)
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

    # Show the custom button only on the last page
    def update_custom_button(page_id):
        # Only show Add Another button when creating new transactions, not when editing
        show_add_another = page_id == 2 and not edit_mode
        wizard.setOption(QWizard.HaveCustomButton1, show_add_another)

    wizard.currentIdChanged.connect(update_custom_button)

    # Connect the button to start a new transaction wizard
    def start_new_transaction():
        wizard.is_adding_another = True
        wizard.accept()

        # Show success message
        QMessageBox.information(parent, "Success", "Transaction added successfully.")

        # Then start a new one
        QTimer.singleShot(100, lambda: add_transaction_wizard(parent, table_view))

    wizard.customButtonClicked.connect(start_new_transaction)

    # Lists to track line widgets
    credit_line_widgets = []
    debit_line_widgets = []

    # Function to update transaction total labels when main amount changes
    def update_transaction_totals():
        try:
            total_amount = float(total_amount_edit.text() or 0)
            transaction_total_credit_label.setText(f"Transaction Total: {total_amount:.2f}")
            transaction_total_debit_label.setText(f"Transaction Total: {total_amount:.2f}")
        except (ValueError, TypeError):
            transaction_total_credit_label.setText("Transaction Total: 0.00")
            transaction_total_debit_label.setText("Transaction Total: 0.00")

    # At the end of your wizard setup:
    def on_current_id_changed(current_id):
        if current_id == 1:  # Credit page
            # Only add a line if no credit lines exist yet
            if len(credit_line_widgets) == 0:
                try:
                    total_amount = float(total_amount_edit.text() or 0)
                    if total_amount > 0:
                        line_data = add_credit_line(total_amount)
                        # Make the account combo box have immediate focus
                        line_data['account'].setFocus()
                        line_data['amount'].textChanged.emit(line_data['amount'].text())  # Trigger update
                    else:
                        line_data = add_credit_line()
                        line_data['account'].setFocus()
                except (ValueError, TypeError):
                    line_data = add_credit_line()
                    line_data['account'].setFocus()
        elif current_id == 2:  # Debit page
            # Only add a line if no debit lines exist yet
            if len(debit_line_widgets) == 0:
                try:
                    total_amount = float(total_amount_edit.text() or 0)
                    if total_amount > 0:
                        line_data = add_debit_line(total_amount)
                        line_data['account'].setFocus()
                        line_data['amount'].textChanged.emit(line_data['amount'].text())  # Trigger update
                    else:
                        line_data = add_debit_line()
                        line_data['account'].setFocus()
                except (ValueError, TypeError):
                    line_data = add_debit_line()
                    line_data['account'].setFocus()

    # Connect the page change handler to create default lines
    wizard.currentIdChanged.connect(on_current_id_changed)

    # Connect to total amount changes
    total_amount_edit.textChanged.connect(update_transaction_totals)

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
            transaction_total_credit_label.setText(f"Transaction Total: {total_transaction_amount:.2f}")

            # Calculate remaining amount needed
            remaining = total_transaction_amount - credit_total

            # Highlight if exceeds total amount
            if credit_total > total_transaction_amount:
                credit_total_label.setStyleSheet("QLabel { color: #b43232; font-weight: bold; }")
                for line in credit_line_widgets:
                    line['amount'].setStyleSheet("QLineEdit { background-color: #FF9999; border: 2px solid #b43232; }")
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
            transaction_total_debit_label.setText(f"Transaction Total: {total_transaction_amount:.2f}")

            # Calculate remaining amount needed
            remaining = total_transaction_amount - debit_total

            # Highlight if exceeds total amount
            if debit_total > total_transaction_amount:
                debit_total_label.setStyleSheet("QLabel { color: #b43232; font-weight: bold; }")
                for line in debit_line_widgets:
                    line['amount'].setStyleSheet("QLineEdit { background-color: #FF9999; border: 2px solid #b43232; }")
            else:
                debit_total_label.setStyleSheet("")
                for line in debit_line_widgets:
                    line['amount'].setStyleSheet("")

            # Return the remaining amount for new lines
            return remaining

        except (ValueError, TypeError):
            return 0

    def can_add_new_line(total_amount, current_total, parent_widget):
        """Check if a new line can be added based on the remaining amount"""
        try:
            total_amount = float(total_amount or 0)
            remaining = total_amount - current_total

            # If there's no more remaining amount, show a message
            if remaining <= 0:
                QMessageBox.warning(
                    parent_widget,
                    "Cannot Add Line",
                    "The total amount has been allocated already. You cannot add more lines."
                )
                return False, 0

            return True, remaining
        except (ValueError, TypeError):
            # If there's an error parsing amounts, still allow adding a line
            return True, 0

    # Function to add a credit line
    def add_credit_line(amount=None, line_data=None):
        """Wrapper function that calls add_transaction_line with is_debit=False"""
        return add_transaction_line(is_debit=False, amount=amount)

    # Function to add a debit line
    def add_debit_line(amount=None, line_data=None):
        """Wrapper function that calls add_transaction_line with is_debit=True"""
        return add_transaction_line(is_debit=True, amount=amount)

    # Add this new combined function
    def add_transaction_line(is_debit=True, amount=None, line_data=None):
        """Add a credit or debit line to the transaction wizard"""
        line_widget = QWidget()
        line_layout = QVBoxLayout(line_widget)
        line_layout.setContentsMargins(5, 5, 5, 5)

        # Top row with account and classification
        top_row = QHBoxLayout()

        # Account label and selection
        account_label = QLabel("Account:")
        top_row.addWidget(account_label, 1)

        # Account selection filtered by nature
        account_combo = QComboBox()

        # Get appropriate accounts based on line type (debit/credit)
        nature_filter = 'debit' if is_debit else 'credit'
        accounts_data = db.get_accounts_by_nature(nature_filter)

        accounts = [acc[1] for acc in accounts_data]
        account_combo.addItems(accounts)
        make_combo_editable(account_combo, accounts)
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
        bottom_row.addWidget(remove_btn, 1)

        line_layout.addLayout(bottom_row)

        # Determine which container and line widgets list to use
        lines_container = debit_lines_container if is_debit else credit_lines_container
        lines_layout = debit_lines_layout if is_debit else credit_lines_layout
        line_widgets_list = debit_line_widgets if is_debit else credit_line_widgets

        # Hide remove button if this is the first line
        if len(line_widgets_list) == 0:
            remove_btn.setVisible(False)

        # Only add separator if this isn't the first line
        if len(line_widgets_list) > 0:
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            lines_layout.addWidget(separator)

        lines_layout.addWidget(line_widget)

        # Track the widget and its components
        line_data_dict = {
            'widget': line_widget,
            'account': account_combo,
            'classification': classification_combo,
            'amount': amount_edit,
            'date': line_date_edit,
            'remove': remove_btn
        }

        # If this is an existing line from edit mode, store the original ID
        if line_data and 'id' in line_data:
            line_data_dict['original_line_id'] = line_data['id']

        line_widgets_list.append(line_data_dict)

        # Connect signals
        update_total_func = update_debit_total if is_debit else update_credit_total
        amount_edit.textChanged.connect(update_total_func)

        # Connect remove button to appropriate function
        if is_debit:
            remove_btn.clicked.connect(lambda: remove_debit_line(line_data_dict))
        else:
            remove_btn.clicked.connect(lambda: remove_credit_line(line_data_dict))

        # Update classification and move focus when account is selected
        def on_account_selected(index):
            if index >= 0 and index < len(accounts):  # Validate index
                # Remember current classification
                current_classification = classification_combo.currentText()

                # Update the classification combo
                update_classification_combo(classification_combo, accounts[index])

                # Try to restore previous classification if possible
                if current_classification and current_classification != "(None)":
                    for i in range(classification_combo.count()):
                        if classification_combo.itemText(i) == current_classification:
                            classification_combo.setCurrentIndex(i)
                            break
                classification_combo.setFocus()

        account_combo.currentIndexChanged.connect(on_account_selected)

        # Handle Enter key press in account combobox
        class AccountKeyPressFilter(QObject):
            def __init__(self, combo, accounts, classification_combo):
                super().__init__()
                self.combo = combo
                self.accounts = accounts
                self.classification_combo = classification_combo

            def eventFilter(self, obj, event):
                if event.type() == QEvent.KeyPress:
                    if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                        current_text = self.combo.currentText()

                        # Validate account exists
                        if current_text in self.accounts:
                            update_classification_combo(self.classification_combo, current_text)
                            self.classification_combo.setFocus()
                            return True
                return False

        account_filter = AccountKeyPressFilter(account_combo, accounts, classification_combo)
        if account_combo.lineEdit():
            account_combo.lineEdit().installEventFilter(account_filter)

        # Store the filter to prevent garbage collection
        line_data_dict['account_filter'] = account_filter

        # Set tab order appropriately
        add_btn = add_debit_btn if is_debit else add_credit_btn
        wizard.setTabOrder(line_date_edit, remove_btn)
        wizard.setTabOrder(remove_btn, add_btn)

        # Pre-fill the line if we are editing and have line data
        if line_data:
            # Set account directly
            if 'account_name' in line_data and line_data['account_name']:
                # Block signals during setup
                account_combo.blockSignals(True)
                account_combo.setCurrentText(line_data['account_name'])
                account_combo.blockSignals(False)

                # Check if the account is valid for this line type
                current_account_name = line_data['account_name']
                if current_account_name not in accounts:
                    # If we're editing an existing line whose account is no longer valid for this type,
                    # we should still show it in the dropdown
                    account_combo.addItem(current_account_name)
                    account_combo.setCurrentText(current_account_name)

                # Set classifications options for this account
                account_id = line_data['account_id']
                classifications = db.get_classifications_for_account(account_id)

                # Setup classification combo
                classification_combo.blockSignals(True)
                classification_combo.clear()

                if classifications:
                    # Add all classifications
                    for classification in classifications:
                        classification_combo.addItem(classification[1])

                    # Make editable if needed
                    classification_combo.setEditable(True)
                    classification_combo.setInsertPolicy(QComboBox.NoInsert)

                    # Set current classification
                    if 'classification_name' in line_data and line_data['classification_name']:
                        classification_combo.setCurrentText(line_data['classification_name'])
                else:
                    # No classifications available
                    classification_combo.addItem("(None)")
                    classification_combo.setEditable(False)

                classification_combo.blockSignals(False)

            # Set amount
            if 'amount' in line_data:
                amount_edit.setText(str(line_data['amount']))

            # Set date
            if 'date' in line_data:
                try:
                    date_obj = datetime.datetime.strptime(line_data['date'], "%Y-%m-%d").date()
                    line_date_edit.setDate(QDate(date_obj.year, date_obj.month, date_obj.day))
                except:
                    pass

        return line_data_dict

    # Function to remove a credit line
    def remove_credit_line(line_data):
        if line_data in credit_line_widgets:
            credit_line_widgets.remove(line_data)
            line_data['widget'].deleteLater()
            update_credit_total()
            # Move focus to the add button after removal
            add_credit_btn.setFocus()

    # Function to remove a debit line
    def remove_debit_line(line_data):
        if line_data in debit_line_widgets:
            debit_line_widgets.remove(line_data)
            line_data['widget'].deleteLater()
            update_debit_total()
            # Move focus to the add button after removal
            add_debit_btn.setFocus()

    def update_classification_combo(combo, account_name):
        combo.clear()
        account_id = db.get_account_id(account_name)
        classifications = db.get_classifications_for_account(account_id)

        # Reset to non-editable first
        combo.setEditable(False)

        # Only show "(None)" when there are NO classifications available
        if not classifications:
            combo.addItem("(None)")
        else:
            # Otherwise just show the actual classifications
            for classification in classifications:
                combo.addItem(classification[1])

        # Make the combo editable with autocompletion if there are classifications
        if classifications:
            items = [c[1] for c in classifications]

            # Simple editable setup without styling
            combo.setEditable(True)
            combo.setInsertPolicy(QComboBox.NoInsert)

            # Create a completer
            completer = QCompleter(items, combo)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            combo.setCompleter(completer)

            # Set empty text initially instead of showing first item
            combo.setCurrentText("")

            # Force style update
            combo.setStyleSheet(
                "QComboBox QAbstractItemView { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; }")
            combo.setStyleSheet("")

            # Set focus behavior
            if combo.lineEdit():
                def on_focus():
                    combo.lineEdit().clear()

                combo.lineEdit().installEventFilter(FocusEventFilter(on_focus))

            # Remember current text if possible
            current_text = combo.currentText()

            # After populating the combo items, try to restore selection
            if current_text and current_text != "(None)":
                for i in range(combo.count()):
                    if combo.itemText(i) == current_text:
                        combo.setCurrentIndex(i)
                        break

    def add_credit_line_with_check():
        current_total = sum(float(line['amount'].text() or 0) for line in credit_line_widgets)
        can_add, remaining = can_add_new_line(total_amount_edit.text(), current_total, wizard)
        if can_add:
            line_data = add_credit_line(remaining)
            line_data['account'].setFocus()

    def add_debit_line_with_check():
        current_total = sum(float(line['amount'].text() or 0) for line in debit_line_widgets)
        can_add, remaining = can_add_new_line(total_amount_edit.text(), current_total, wizard)
        if can_add:
            line_data = add_debit_line(remaining)
            line_data['account'].setFocus()

    # Update date fields when main date changes
    def update_line_dates():
        new_date = date_edit.date()
        for line in credit_line_widgets:
            line['date'].setDate(new_date)
        for line in debit_line_widgets:
            line['date'].setDate(new_date)

    add_credit_btn.clicked.connect(add_credit_line_with_check)
    add_debit_btn.clicked.connect(add_debit_line_with_check)
    date_edit.dateChanged.connect(update_line_dates)

    # Save Logic
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

                    # Store original line ID if this is an edit and we have the line data
                    original_line_id = None
                    if 'original_line_id' in line:
                        original_line_id = line['original_line_id']

                    credit_lines.append({
                        'id': original_line_id,  # None for new lines
                        'account_id': account_id,
                        'amount': amount,
                        'date': line_date,
                        'classification_id': classification_id
                    })
                except (ValueError, TypeError):
                    pass

            # Prepare debit lines data (similar to credit lines)
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

                    # Store original line ID if this is an edit and we have the line data
                    original_line_id = None
                    if hasattr(line, 'original_line_id'):
                        original_line_id = line.original_line_id

                    debit_lines.append({
                        'id': original_line_id,  # None for new lines
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
            if wizard.edit_mode and wizard.transaction_id:
                # Update existing transaction
                update_complete_transaction(
                    wizard.transaction_id,
                    description,
                    currency_id,
                    credit_lines,
                    debit_lines,
                    credit_lines_data,  # Pass original data for comparison
                    debit_lines_data
                )
                success_message = "Transaction updated successfully."
            else:
                # Save as new transaction
                new_transaction_id = save_complete_transaction(
                    description,
                    currency_id,
                    credit_lines,
                    debit_lines
                )
                wizard.transaction_id = new_transaction_id
                success_message = "Transaction added successfully."

            # Reload transactions and select the transaction
            load_transactions(table_view, select_transaction_id=wizard.transaction_id)

            # Force transaction selection update
            if hasattr(table_view, '_on_transaction_selected'):
                table_view._on_transaction_selected()

            if hasattr(wizard, 'is_adding_another') and wizard.is_adding_another:
                # Skip showing success message - it will be shown before the next wizard opens
                pass
            else:
                QMessageBox.information(parent, "Success", success_message)
        except Exception as e:
            QMessageBox.critical(parent, "Error",
                                 f"Failed to {'update' if wizard.edit_mode else 'add'} transaction: {str(e)}")


def on_import_csv(parent, table_view):
    """Import a new CSV file"""
    # Use the existing import_csv_wizard function
    orphan_id = import_csv_wizard(parent)

    if orphan_id:
        # Refresh the table view
        load_orphan_transactions(table_view)

        # Select the newly imported batch
        model = table_view.model()
        for row in range(model.rowCount()):
            if model.item(row, 0).text() == str(orphan_id):
                table_view.selectRow(row)
                break

def fill_classifications_for_edit(combo, account_id, target_classification):
    """Fill classification combo and set value during edit operations"""
    # Clear the combo first
    combo.clear()

    # Get classification options for this account
    classifications = db.get_classifications_for_account(account_id)

    # Add items to combo
    if not classifications:
        combo.addItem("(None)")
    else:
        for classification in classifications:
            combo.addItem(classification[1])

    # Make editable if needed
    if classifications:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)

        # Create a completer
        items = [c[1] for c in classifications]
        completer = QCompleter(items, combo)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        combo.setCompleter(completer)

    # Set the target classification if provided
    if target_classification:
        # First try to find it in the list
        found = False
        for i in range(combo.count()):
            if combo.itemText(i) == target_classification:
                combo.setCurrentIndex(i)
                found = True
                break

        # If not in list but combo is editable, set as text
        if not found and combo.isEditable():
            combo.setCurrentText(target_classification)

def set_classification_after_account(combo, account_id, target_classification):
    """Set classification after account is selected"""
    # First clear the combo
    combo.clear()

    # Get classifications for this account
    classifications = db.get_classifications_for_account(account_id)

    # Only show "(None)" when there are NO classifications available
    if not classifications:
        combo.addItem("(None)")
    else:
        # Add all classifications
        for classification in classifications:
            combo.addItem(classification[1])

    # Make editable if needed
    if classifications:
        items = [c[1] for c in classifications]
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)

        # Create a completer
        completer = QCompleter(items, combo)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        combo.setCompleter(completer)

    # Set the target classification if provided
    if target_classification:
        found = False
        for i in range(combo.count()):
            if combo.itemText(i) == target_classification:
                combo.setCurrentIndex(i)
                found = True
                break

        # If not found in the list but combo is editable, set as text
        if not found and combo.isEditable():
            combo.setCurrentText(target_classification)

def edit_transaction_wizard(parent, table_view):
    """Edit an existing transaction using the same wizard as for adding"""
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a transaction to edit.")
        return

    transaction_id = int(row_data["ID"])

    # Get transaction details
    transaction_details = db.get_transaction_by_id(transaction_id)
    if not transaction_details:
        QMessageBox.warning(parent, "Error", "Could not retrieve transaction details.")
        return

    # Get transaction lines with fully populated data
    credit_lines = []
    debit_lines = []

    # Get raw transaction lines
    lines = db.get_transaction_lines(transaction_id)

    for line in lines:
        line_id = line[0]
        account_id = line[2]
        debit = line[3] if line[3] else 0
        credit = line[4] if line[4] else 0
        date = line[5]
        classification_id = line[7]

        # Get account name
        account_name = get_cached_account_name(account_id)

        # Get classification name
        classification_name = get_cached_classification_name(classification_id)

        # Create line data dictionary
        line_data = {
            'id': line_id,
            'account_id': account_id,
            'account_name': account_name,
            'amount': debit if debit else credit,
            'date': date,
            'classification_id': classification_id,
            'classification_name': classification_name
        }

        # Add to appropriate list
        if debit > 0:
            debit_lines.append(line_data)
        else:
            credit_lines.append(line_data)

    # Now call the modified add_transaction_wizard with edit mode
    add_transaction_wizard(parent, table_view, edit_mode=True,
                           transaction_id=transaction_id,
                           transaction_data=transaction_details,
                           credit_lines_data=credit_lines,
                           debit_lines_data=debit_lines)

# Define the function
def reset_transaction_filters(parent, table_view):
    # Reset filters
    table_view.filter_params = None

    # Reset to first page with default page size
    load_transactions(table_view, page=1, page_size=None)

    # Update pagination display if the function is available
    if hasattr(table_view, 'update_pagination_info'):
        table_view.update_pagination_info()

        # Inform the user
        QMessageBox.information(parent, "Filters Reset", "All transaction filters have been reset.")



# After this function in display_transactions.py
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

# Add the update_complete_transaction function right here
def update_complete_transaction(transaction_id, description, currency_id,
                               credit_lines, debit_lines,
                               original_credit_lines=None, original_debit_lines=None):
    """Update a complete transaction with all its lines"""
    try:
        # Start a transaction
        db.begin_transaction()

        # Update transaction record
        db.update_transaction(transaction_id, description, currency_id)

        # Track which original lines have been processed
        processed_credit_line_ids = set()
        processed_debit_line_ids = set()

        # Create sets of original line IDs for quick lookup
        original_credit_ids = {line['id'] for line in original_credit_lines} if original_credit_lines else set()
        original_debit_ids = {line['id'] for line in original_debit_lines} if original_debit_lines else set()

        # Process credit lines
        for line in credit_lines:
            if line.get('id') and line['id'] in original_credit_ids:
                # Update existing line
                db.update_transaction_line(
                    line['id'],
                    line['account_id'],
                    debit=None,
                    credit=line['amount'],
                    date=line['date'],
                    classification_id=line['classification_id']
                )
                processed_credit_line_ids.add(line['id'])
            else:
                # Insert new line
                db.insert_transaction_line(
                    transaction_id,
                    line['account_id'],
                    debit=None,
                    credit=line['amount'],
                    date=line['date'],
                    classification_id=line['classification_id']
                )

        # Process debit lines
        for line in debit_lines:
            if line.get('id') and line['id'] in original_debit_ids:
                # Update existing line
                db.update_transaction_line(
                    line['id'],
                    line['account_id'],
                    debit=line['amount'],
                    credit=None,
                    date=line['date'],
                    classification_id=line['classification_id']
                )
                processed_debit_line_ids.add(line['id'])
            else:
                # Insert new line
                db.insert_transaction_line(
                    transaction_id,
                    line['account_id'],
                    debit=line['amount'],
                    credit=None,
                    date=line['date'],
                    classification_id=line['classification_id']
                )

        # Delete any original lines that weren't updated (they were removed)
        if original_credit_lines:
            for line in original_credit_lines:
                if line['id'] not in processed_credit_line_ids:
                    db.delete_transaction_line(line['id'])

        if original_debit_lines:
            for line in original_debit_lines:
                if line['id'] not in processed_debit_line_ids:
                    db.delete_transaction_line(line['id'])

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
        # At the end of load_transactions function, add:
        if hasattr(table_view, 'update_pagination_info'):
            table_view.update_pagination_info()