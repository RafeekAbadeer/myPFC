from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTableView, QAction, QMessageBox,
    QHeaderView, QWidget, QToolBar, QLabel, QPushButton, QDialog,
    QSplitter, QFormLayout, QComboBox, QDateEdit, QFrame, QLineEdit, QGroupBox
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtCore import Qt, QDate
from gui.import_utils import import_csv_wizard
from database import db, get_counterpart_suggestions
import datetime


def display_orphan_transactions(content_frame, toolbar):
    """Display orphan transactions awaiting processing"""

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

    # Add toolbar actions
    import_action = QAction(QIcon('icons/import.png'), "Import CSV", toolbar)
    process_action = QAction(QIcon('icons/process.png'), "Process Selected", toolbar)
    ignore_action = QAction(QIcon('icons/ignore.png'), "Ignore Selected", toolbar)

    # Add actions to toolbar
    toolbar.insertAction(actions_to_keep[0], import_action)
    toolbar.insertAction(actions_to_keep[0], process_action)
    toolbar.insertAction(actions_to_keep[0], ignore_action)

    # Create a splitter to divide the main transactions and details panels
    splitter = QSplitter(Qt.Vertical)
    layout.addWidget(splitter)

    # Top widget for orphan transaction batches
    top_widget = QWidget()
    top_layout = QVBoxLayout(top_widget)

    # Label for top section
    top_label = QLabel("<h3>Orphan Transaction Batches</h3>")
    top_layout.addWidget(top_label)

    # Create table for orphan transactions
    orphan_table = QTableView()
    orphan_table.setSelectionBehavior(QTableView.SelectRows)
    orphan_table.setAlternatingRowColors(True)
    top_layout.addWidget(orphan_table)

    # Bottom widget for orphan lines
    bottom_widget = QWidget()
    bottom_layout = QVBoxLayout(bottom_widget)

    # Label for bottom section
    bottom_label = QLabel("<h3>Orphan Transaction Lines</h3>")
    bottom_layout.addWidget(bottom_label)

    # Create table for orphan lines
    lines_table = QTableView()
    lines_table.setSelectionBehavior(QTableView.SelectRows)
    lines_table.setAlternatingRowColors(True)
    bottom_layout.addWidget(lines_table)

    # Add widgets to splitter
    splitter.addWidget(top_widget)
    splitter.addWidget(bottom_widget)

    # Set initial sizes
    splitter.setSizes([300, 400])

    # Load orphan transaction batches
    load_orphan_transactions(orphan_table)

    # Connect actions
    import_action.triggered.connect(lambda: on_import_csv(content_frame, orphan_table))
    process_action.triggered.connect(lambda: on_process_selected(orphan_table, lines_table, content_frame))
    ignore_action.triggered.connect(lambda: on_ignore_selected(orphan_table, lines_table))

    # Connect selection signal
    orphan_table.selectionModel().selectionChanged.connect(
        lambda: on_orphan_transaction_selected(orphan_table, lines_table))

    # Add processing buttons to lines view
    lines_buttons_layout = QHBoxLayout()

    process_line_btn = QPushButton("Process Selected Line")
    process_line_btn.clicked.connect(lambda: on_process_line(lines_table, content_frame))

    ignore_line_btn = QPushButton("Ignore Selected Line")
    ignore_line_btn.clicked.connect(lambda: on_ignore_line(lines_table))

    bulk_process_btn = QPushButton("Bulk Process Similar...")
    bulk_process_btn.clicked.connect(lambda: on_bulk_process(lines_table, content_frame))

    lines_buttons_layout.addWidget(process_line_btn)
    lines_buttons_layout.addWidget(ignore_line_btn)
    lines_buttons_layout.addWidget(bulk_process_btn)
    lines_buttons_layout.addStretch()

    bottom_layout.addLayout(lines_buttons_layout)


# Helper functions below would include:
def load_orphan_transactions(table_view):
    """Load orphan transaction batches into the table view"""
    # Implementation here


def load_orphan_lines(table_view, orphan_transaction_id):
    """Load orphan transaction lines for a specific batch"""
    # Implementation here


def on_orphan_transaction_selected(orphan_table, lines_table):
    """Handle selection of an orphan transaction batch"""
    # Implementation here


def on_import_csv(parent, table_view):
    """Import a new CSV file"""
    # Implementation here


def on_process_selected(orphan_table, lines_table, parent):
    """Process selected orphan transaction batch"""
    # Implementation here


def on_ignore_selected(orphan_table, lines_table):
    """Ignore selected orphan transaction batch"""
    # Implementation here


def on_process_line(lines_table, parent):
    """Process a single orphan transaction line"""
    # Implementation here


def on_ignore_line(lines_table):
    """Ignore a single orphan transaction line"""
    # Implementation here


def on_bulk_process(lines_table, parent):
    """Bulk process similar transaction lines"""
    # Implementation here


def process_orphan_lines(orphan_id, parent):
    """Process orphan transaction lines into balanced transactions"""

    # Create dialog
    dialog = QDialog(parent)
    dialog.setWindowTitle("Process Imported Transactions")
    dialog.resize(800, 600)

    # Get orphan lines
    lines = db.get_orphan_lines(orphan_id, 'new')
    if not lines:
        QMessageBox.information(parent, "No Lines", "No unprocessed lines found for this import.")
        return

    # Set up layout
    layout = QVBoxLayout(dialog)

    # Create current line display
    current_line_frame = QFrame()
    current_line_layout = QFormLayout(current_line_frame)

    # Description field
    description_edit = QLineEdit()
    current_line_layout.addRow("Description:", description_edit)

    # Create two columns - one for imported data, one for counterpart
    columns_layout = QHBoxLayout()
    # Left column - Imported data (read-only)
    imported_group = QGroupBox("Imported Transaction")
    imported_layout = QFormLayout(imported_group)

    imported_desc_label = QLabel()
    imported_layout.addRow("Description:", imported_desc_label)

    imported_date_label = QLabel()
    imported_layout.addRow("Date:", imported_date_label)

    imported_amount_label = QLabel()
    imported_layout.addRow("Amount:", imported_amount_label)

    imported_account_label = QLabel()
    imported_layout.addRow("Account:", imported_account_label)

    # Left column - Imported data (read-only)
    imported_group = QGroupBox("Imported Transaction")
    imported_layout = QFormLayout(imported_group)

    imported_desc_label = QLabel()
    imported_layout.addRow("Description:", imported_desc_label)

    imported_date_label = QLabel()
    imported_layout.addRow("Date:", imported_date_label)

    imported_amount_label = QLabel()
    imported_layout.addRow("Amount:", imported_amount_label)

    imported_account_label = QLabel()
    imported_layout.addRow("Account:", imported_account_label)

    # Smart account selection with suggestions
    counterpart_account_combo = QComboBox()
    counterpart_layout.addRow("Account:", counterpart_account_combo)

    # Add suggestion display area
    suggestions_group = QGroupBox("Suggested Accounts")
    suggestions_layout = QVBoxLayout(suggestions_group)

    # Add both columns to main layout
    columns_layout.addWidget(imported_group)
    columns_layout.addWidget(counterpart_group)

    layout.addLayout(columns_layout)
    layout.addWidget(suggestions_group)

    # Function to update display with suggestions
    def update_display_with_suggestions():
        # [Basic display update as before]

        # Get suggestions for counterpart account
        suggestions = get_counterpart_suggestions(
            line['description'],
            line['credit'] if line['credit'] else line['debit'],
            line['credit'] is not None
        )

        # Update suggestions display
        clear_layout(suggestions_layout)

        for i, suggestion in enumerate(suggestions[:5]):  # Show top 5
            suggestion_btn = QPushButton(f"{suggestion['account_name']} ({suggestion['confidence']}%)")
            suggestion_btn.setToolTip(suggestion['reason'])

            # Connect button to select this account
            suggestion_btn.clicked.connect(lambda _, idx=i: select_suggested_account(idx))

            suggestions_layout.addWidget(suggestion_btn)

        # Also update the combo box with all accounts
        counterpart_account_combo.clear()
        for account in db.get_all_accounts():
            counterpart_account_combo.addItem(account[1])

        # Pre-select top suggestion if available
        if suggestions:
            index = counterpart_account_combo.findText(suggestions[0]['account_name'])
            if index >= 0:
                counterpart_account_combo.setCurrentIndex(index)

    # Function to select a suggested account
    def select_suggested_account(index):
        suggestions = get_counterpart_suggestions(
            lines[current_index]['description'],
            lines[current_index]['credit'] if lines[current_index]['credit'] else lines[current_index]['debit'],
            lines[current_index]['credit'] is not None
        )

        # Find and select the account in the combo box
        if index < len(suggestions):
            account_name = suggestions[index]['account_name']
            combo_index = counterpart_account_combo.findText(account_name)
            if combo_index >= 0:
                counterpart_account_combo.setCurrentIndex(combo_index)


    # Date field
    date_edit = QDateEdit(QDate.currentDate())
    date_edit.setCalendarPopup(True)
    current_line_layout.addRow("Date:", date_edit)

    # Amount field
    amount_label = QLabel()
    current_line_layout.addRow("Amount:", amount_label)

    # Account field
    account_label = QLabel()
    current_line_layout.addRow("Account:", account_label)

    # Counterpart account selection
    counterpart_combo = QComboBox()
    counterpart_combo.addItems([acc[1] for acc in db.get_accounts_by_nature()])
    current_line_layout.addRow("Counterpart Account:", counterpart_combo)

    # Classification selection
    classification_combo = QComboBox()
    classification_combo.addItem("(None)")
    current_line_layout.addRow("Classification:", classification_combo)

    layout.addWidget(current_line_frame)

    # Add navigation buttons
    nav_layout = QHBoxLayout()
    prev_button = QPushButton("Previous")
    next_button = QPushButton("Next")
    skip_button = QPushButton("Skip")
    create_button = QPushButton("Create Transaction")

    nav_layout.addWidget(prev_button)
    nav_layout.addWidget(skip_button)
    nav_layout.addWidget(create_button)
    nav_layout.addWidget(next_button)

    layout.addLayout(nav_layout)

    # Add progress indicator
    progress_layout = QHBoxLayout()
    progress_label = QLabel("Processing item 1 of X")
    progress_layout.addWidget(progress_label)
    layout.addLayout(progress_layout)

    # Current line index
    current_index = 0

    # Function to update display for current line
    def update_display():
        if current_index >= len(lines):
            dialog.close()
            return

        line = lines[current_index]
        description_edit.setText(line['description'])

        # Set date if available
        try:
            date = datetime.datetime.strptime(line.get('date', ''), '%Y-%m-%d').date()
            date_edit.setDate(QDate(date.year, date.month, date.day))
        except:
            date_edit.setDate(QDate.currentDate())

        # Display amount and determine if credit or debit
        if line['debit']:
            amount_label.setText(f"${line['debit']} (Debit)")
            is_credit = False
        else:
            amount_label.setText(f"${line['credit']} (Credit)")
            is_credit = True

        # Set account
        account_label.setText(line['account_name'])

        # Update classification options based on counterpart account
        update_classification_options()

        # Update progress indicator
        progress_label.setText(f"Processing item {current_index + 1} of {len(lines)}")

        # Update navigation buttons
        prev_button.setEnabled(current_index > 0)
        next_button.setEnabled(current_index < len(lines) - 1)

    # Connect signals for navigation
    prev_button.clicked.connect(lambda: navigate(-1))
    next_button.clicked.connect(lambda: navigate(1))
    skip_button.clicked.connect(lambda: navigate(1, skip=True))
    create_button.clicked.connect(create_transaction)

    # Navigation function
    def navigate(direction, skip=False):
        nonlocal current_index
        if skip:
            # Skip this line (don't process)
            lines[current_index]['skipped'] = True

        # Move to next/previous line
        current_index += direction
        update_display()

    # Transaction creation function
    def create_transaction():
        line = lines[current_index]

        # Get selected counterpart account
        counterpart_account_name = counterpart_combo.currentText()
        counterpart_account_id = db.get_account_id(counterpart_account_name)

        # Get classification if selected
        classification_id = None
        if classification_combo.currentText() != "(None)":
            classification_data = db.get_classification_by_name(classification_combo.currentText())
            if classification_data:
                classification_id = classification_data[0]

        try:
            # Start transaction creation
            db.begin_transaction()

            # Create new transaction
            description = description_edit.text()
            currency_id = 1  # Default currency - might need to be determined differently
            transaction_id = db.insert_transaction(description, currency_id)

            # Create the original line
            date_str = date_edit.date().toString("yyyy-MM-dd")
            if line['debit']:
                # This is a debit line
                db.insert_transaction_line(
                    transaction_id,
                    line['account_id'],
                    debit=line['debit'],
                    credit=None,
                    date=date_str,
                    classification_id=classification_id
                )

                # Create balancing credit line
                db.insert_transaction_line(
                    transaction_id,
                    counterpart_account_id,
                    debit=None,
                    credit=line['debit'],
                    date=date_str,
                    classification_id=None
                )
            else:
                # This is a credit line
                db.insert_transaction_line(
                    transaction_id,
                    line['account_id'],
                    debit=None,
                    credit=line['credit'],
                    date=date_str,
                    classification_id=classification_id
                )

                # Create balancing debit line
                db.insert_transaction_line(
                    transaction_id,
                    counterpart_account_id,
                    debit=line['credit'],
                    credit=None,
                    date=date_str,
                    classification_id=None
                )

            # Mark orphan line as consumed
            db.consume_orphan_line(line['id'], transaction_id)

            # Commit transaction
            db.commit_transaction()

            # Move to next item
            navigate(1)

        except Exception as e:
            db.rollback_transaction()
            QMessageBox.critical(dialog, "Error", f"Failed to create transaction: {str(e)}")

    # Function to update classification options
    def update_classification_options():
        # Get selected account
        account_name = counterpart_combo.currentText()
        account_id = db.get_account_id(account_name)

        # Get classifications for this account
        classifications = db.get_classifications_for_account(account_id)

        # Update combo box
        classification_combo.clear()
        classification_combo.addItem("(None)")
        for classification in classifications:
            classification_combo.addItem(classification[1])

    # Connect account selection to classification update
    counterpart_combo.currentIndexChanged.connect(update_classification_options)

    # Initialize display
    update_display()

    # Show dialog
    dialog.exec_()


def process_similar_orphans(reference_line_id, parent):
    """Process multiple similar orphan lines at once"""
    # Get the reference line
    reference_line = db.get_orphan_line_by_id(reference_line_id)
    if not reference_line:
        return

    # Find similar lines based on description pattern
    description_pattern = reference_line['description']

    # Extract key part of description (e.g., merchant name)
    # This is a simplified approach - could be more sophisticated
    words = description_pattern.split()
    if len(words) > 2:
        # Use first 2 words if available
        key_part = ' '.join(words[:2])
    else:
        key_part = description_pattern

    # Find similar lines
    similar_lines = db.execute_query("""
        SELECT id, description, debit, credit, account_id
        FROM orphan_transaction_lines
        WHERE status = 'new' 
        AND description LIKE ?
        AND id != ?
    """, (f'%{key_part}%', reference_line_id))

    if not similar_lines:
        QMessageBox.information(parent, "No Similar Items",
                                "No similar items found for bulk processing.")
        return

    # Create dialog
    dialog = QDialog(parent)
    dialog.setWindowTitle("Bulk Process Similar Transactions")
    dialog.resize(700, 500)

    layout = QVBoxLayout(dialog)

    # Show reference transaction
    ref_group = QGroupBox("Reference Transaction")
    ref_layout = QFormLayout(ref_group)

    ref_desc_label = QLabel(reference_line['description'])
    ref_layout.addRow("Description:", ref_desc_label)

    amount = reference_line['debit'] if reference_line['debit'] else reference_line['credit']
    type_text = "Debit" if reference_line['debit'] else "Credit"
    ref_amount_label = QLabel(f"${amount} ({type_text})")
    ref_layout.addRow("Amount:", ref_amount_label)

    layout.addWidget(ref_group)

    # Show counterpart account selection
    counterpart_group = QGroupBox("Counterpart Account")
    counterpart_layout = QFormLayout(counterpart_group)

    account_combo = QComboBox()
    for account in db.get_all_accounts():
        account_combo.addItem(account[1])
    counterpart_layout.addRow("Account:", account_combo)

    layout.addWidget(counterpart_group)

    # Show table of similar transactions
    table = QTableView()
    model = QStandardItemModel()

    model.setHorizontalHeaderLabels(["ID", "Description", "Amount", "Include"])

    for line in similar_lines:
        line_id = line[0]
        description = line[1]
        amount = line[2] if line[2] else line[3]

        id_item = QStandardItem(str(line_id))
        desc_item = QStandardItem(description)
        amount_item = QStandardItem(f"${amount}")

        # Checkbox for selection
        include_item = QStandardItem()
        include_item.setCheckable(True)
        include_item.setCheckState(Qt.Checked)  # Default to checked

        model.appendRow([id_item, desc_item, amount_item, include_item])

    table.setModel(model)
    table.setSelectionBehavior(QTableView.SelectRows)
    table.resizeColumnsToContents()

    layout.addWidget(table)

    # Add buttons
    buttons_layout = QHBoxLayout()
    process_btn = QPushButton("Process All Selected")
    cancel_btn = QPushButton("Cancel")

    buttons_layout.addWidget(process_btn)
    buttons_layout.addWidget(cancel_btn)

    layout.addLayout(buttons_layout)

    # Connect signals
    cancel_btn.clicked.connect(dialog.reject)
    process_btn.clicked.connect(lambda: bulk_process())

    def bulk_process():
        # Get selected account
        counterpart_account_name = account_combo.currentText()
        counterpart_account_id = db.get_account_id(counterpart_account_name)

        # Get selected lines
        selected_line_ids = []
        for row in range(model.rowCount()):
            include_item = model.item(row, 3)
            if include_item.checkState() == Qt.Checked:
                line_id = int(model.item(row, 0).text())
                selected_line_ids.append(line_id)

        if not selected_line_ids:
            QMessageBox.warning(dialog, "No Selection",
                                "Please select at least one transaction to process.")
            return

        # Process each line
        try:
            processed_count = 0

            for line_id in selected_line_ids:
                # Get line data
                line_data = db.get_orphan_line_by_id(line_id)

                # Create transaction
                db.begin_transaction()

                # Format date
                date_str = QDate.currentDate().toString("yyyy-MM-dd")

                # Create transaction record
                transaction_id = db.insert_transaction(
                    line_data['description'],
                    1  # Default currency ID - could be dynamic
                )

                # Add original line
                if line_data['debit']:
                    # This is a debit line
                    db.insert_transaction_line(
                        transaction_id,
                        line_data['account_id'],
                        debit=line_data['debit'],
                        credit=None,
                        date=date_str
                    )

                    # Add balancing credit
                    db.insert_transaction_line(
                        transaction_id,
                        counterpart_account_id,
                        debit=None,
                        credit=line_data['debit'],
                        date=date_str
                    )
                else:
                    # This is a credit line
                    db.insert_transaction_line(
                        transaction_id,
                        line_data['account_id'],
                        debit=None,
                        credit=line_data['credit'],
                        date=date_str
                    )

                    # Add balancing debit
                    db.insert_transaction_line(
                        transaction_id,
                        counterpart_account_id,
                        debit=line_data['credit'],
                        credit=None,
                        date=date_str
                    )

                # Mark as consumed
                db.consume_orphan_line(line_id, transaction_id)

                db.commit_transaction()
                processed_count += 1

            QMessageBox.information(dialog, "Success",
                                    f"Successfully processed {processed_count} transactions.")
            dialog.accept()

        except Exception as e:
            db.rollback_transaction()
            QMessageBox.critical(dialog, "Error", f"Failed to process transactions: {str(e)}")

    # Show dialog
    dialog.exec_()