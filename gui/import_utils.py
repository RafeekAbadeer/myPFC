import os
import json
import csv
import datetime
from PyQt5.QtWidgets import (
    QDialog, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QLineEdit, QComboBox, QPushButton, QCheckBox, QMessageBox, QHeaderView,
    QFileDialog, QGroupBox, QFormLayout, QTextEdit, QTableView, QWidget, QSizePolicy
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPixmap, QColor, QFont
from PyQt5.QtCore import Qt, QDate
from database import db



def import_csv_wizard(parent):
    """
    Creates a wizard to guide the user through importing a CSV file
    Returns the ID of the created orphan transaction batch if successful, None otherwise
    """
    wizard = QWizard(parent)
    wizard.setWindowTitle("Import Transactions")
    wizard.setMinimumSize(800, 600)
    wizard.current_page_id = 0  # Initialize to page 1 (0-indexed)

    # Add state storage for combo box selections
    wizard.saved_mappings = {
        'date': None,
        'description': None,
        'amount': None,
        'debit': None,
        'credit': None,
        'account': None,
        'currency': None,
        'date_format': None,
        'custom_date_format': None
    }

    # Apply modern style to match add_transaction_wizard
    wizard.setWizardStyle(QWizard.ModernStyle)

    # Create a transparent pixmap for the banner/watermark
    transparent_pixmap = QPixmap()
    wizard.setPixmap(QWizard.WatermarkPixmap, transparent_pixmap)
    wizard.setPixmap(QWizard.BannerPixmap, transparent_pixmap)
    wizard.setPixmap(QWizard.LogoPixmap, transparent_pixmap)

    # ==================
    # Page 1: File Selection and Basic Info
    # ==================
    page1 = QWizardPage()
    page1.setTitle("Select CSV File and Import Details")
    page1.setSubTitle("Please select a CSV file and provide basic information")

    layout1 = QVBoxLayout(page1)
    layout1.setSpacing(10)
    layout1.setContentsMargins(20, 20, 20, 20)

    # File selection
    file_group = QGroupBox("CSV File")
    file_layout = QVBoxLayout(file_group)
    file_layout.setSpacing(10)

    file_selector = QHBoxLayout()
    file_path_edit = QLineEdit()
    file_path_edit.setReadOnly(True)
    file_path_edit.setMinimumHeight(30)
    browse_button = QPushButton("Browse...")
    browse_button.setMinimumHeight(30)
    file_selector.addWidget(file_path_edit)
    file_selector.addWidget(browse_button)

    file_layout.addLayout(file_selector)

    # CSV preview
    preview_label = QLabel("File Preview:")
    file_layout.addWidget(preview_label)

    preview_text = QTextEdit()
    preview_text.setReadOnly(True)
    preview_text.setMinimumHeight(150)
    file_layout.addWidget(preview_text)

    layout1.addWidget(file_group)

    # Import details
    details_group = QGroupBox("Import Details")
    details_layout = QFormLayout(details_group)
    details_layout.setSpacing(10)

    reference_edit = QLineEdit()
    reference_edit.setMinimumHeight(30)
    # Generate a default reference with current date
    default_reference = f"Import {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
    reference_edit.setText(default_reference)
    reference_edit.textChanged.emit(default_reference)
    details_layout.addRow("Import Reference:", reference_edit)

    account_combo = QComboBox()
    #account_combo.setMinimumHeight(30)
    account_combo.addItem("Multiple accounts (in CSV)")
    accounts = db.get_all_accounts()
    for account in accounts:
        account_combo.addItem(account[1])
    details_layout.addRow("Source Account:", account_combo)

    # Add currency selection
    currency_combo = QComboBox()
    #currency_combo.setMinimumHeight(30)
    currencies = db.get_all_currencies()
    for currency in currencies:
        currency_combo.addItem(currency[1])

    # Set default currency to EGP if available
    default_index = 0
    for i, currency in enumerate(currencies):
        if currency[1] == "EGP":
            default_index = i
            break
    currency_combo.setCurrentIndex(default_index)

    details_layout.addRow("Currency:", currency_combo)

    has_header_checkbox = QCheckBox("CSV has header row")
    has_header_checkbox.setChecked(True)
    details_layout.addRow("", has_header_checkbox)

    layout1.addWidget(details_group)

    # Register fields
    page1.registerField("filePath*", file_path_edit)
    page1.registerField("reference", reference_edit)
    page1.registerField("account", account_combo, "currentText")
    page1.registerField("currency", currency_combo, "currentText")
    page1.registerField("hasHeader", has_header_checkbox)

    # ==================
    # Page 2: CSV Mapping
    # ==================
    page2 = QWizardPage()
    page2.setTitle("Map CSV Columns")
    page2.setSubTitle("Please map the CSV columns to the appropriate fields")

    layout2 = QVBoxLayout(page2)
    layout2.setSpacing(10)
    layout2.setContentsMargins(20, 20, 20, 20)

    # Create a scroll area for the content
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll_content = QWidget()
    scroll_layout = QVBoxLayout(scroll_content)
    scroll_layout.setSpacing(10)

    # Header preview
    header_group = QGroupBox("CSV Content Preview")
    header_layout = QVBoxLayout(header_group)

    # Add explanatory label
    header_info_label = QLabel(
        "This shows column headers (first row) and a sample row from your CSV file. Colors indicate mapped fields.")
    header_info_label.setWordWrap(True)
    header_layout.addWidget(header_info_label)

    header_preview = QTableView()
    header_preview.setMinimumHeight(100)
    header_preview.setAlternatingRowColors(True)
    header_model = QStandardItemModel()
    header_preview.setModel(header_model)

    # Add better column headers for unmapped columns
    def update_header_labels():
        # Update header row with more descriptive labels if needed
        for col in range(header_model.columnCount()):
            item = header_model.item(0, col)
            if item and "Column" in item.text():
                # Add tooltip for unmapped columns
                item.setToolTip("Select this column in the mapping below to use this data")

    # Improve header preview appearance
    header_preview.horizontalHeader().setVisible(False)
    header_preview.verticalHeader().setVisible(False)
    header_preview.setSelectionMode(QTableView.SingleSelection)
    header_preview.setSelectionBehavior(QTableView.SelectColumns)

    header_layout.addWidget(header_preview)

    scroll_layout.addWidget(header_group)

    # Mapping fields
    mapping_group = QGroupBox("Field Mapping")
    # Remove height constraints to let it size naturally
    mapping_layout = QFormLayout(mapping_group)
    mapping_layout.setSpacing(10)
    mapping_layout.setContentsMargins(10, 20, 10, 20)
    mapping_layout.setSpacing(10)  # Reduced from 15
    mapping_layout.setContentsMargins(10, 15, 10, 15)  # Reduced margins

    date_combo = QComboBox()
    description_combo = QComboBox()
    amount_combo = QComboBox()
    debit_combo = QComboBox()
    credit_combo = QComboBox()

    # Set uniform sizing for all combo boxes
    combo_height = 40  # Increased from 35
    for combo in [date_combo, description_combo, amount_combo, debit_combo, credit_combo]:
        combo.setMinimumHeight(combo_height)
        combo.setMaximumHeight(combo_height)  # Ensure consistent height
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    # Add "Not mapped" option to all combos
    for combo in [date_combo, description_combo, amount_combo, debit_combo, credit_combo]:
        combo.addItem("Not mapped")

    mapping_layout.addRow("Date:", date_combo)
    mapping_layout.addRow("Description:", description_combo)
    mapping_layout.addRow("Amount:", amount_combo)
    mapping_layout.addRow("Debit:", debit_combo)
    mapping_layout.addRow("Credit:", credit_combo)

    # Account mapping section (only visible if "Multiple accounts" selected on page 1)
    account_mapping_section = QWidget()
    account_mapping_layout = QVBoxLayout(account_mapping_section)
    account_mapping_layout.setContentsMargins(0, 0, 0, 15)  # Add bottom margin

    account_form = QFormLayout()
    account_col_combo = QComboBox()
    account_col_combo.addItem("Not mapped")
    account_form.addRow("Account Column:", account_col_combo)

    account_mapping_layout.addLayout(account_form)

    account_mapping_info = QLabel("The account column should contain account names that match your system")
    account_mapping_info.setWordWrap(True)
    account_mapping_info.setIndent(20)  # Indent the text
    account_mapping_layout.addWidget(account_mapping_info)

    mapping_layout.addRow(account_mapping_section)

    # Add currency mapping section
    currency_mapping_section = QWidget()
    currency_mapping_layout = QVBoxLayout(currency_mapping_section)
    currency_mapping_layout.setContentsMargins(0, 0, 0, 15)  # Add bottom margin

    currency_form = QFormLayout()
    currency_col_combo = QComboBox()
    currency_col_combo.addItem("Not mapped")
    currency_form.addRow("Currency Column:", currency_col_combo)

    currency_mapping_layout.addLayout(currency_form)

    currency_mapping_info = QLabel(
        "If your CSV contains currency information, map it here. Otherwise, the selected currency will be used for all transactions.")
    currency_mapping_info.setWordWrap(True)
    currency_mapping_info.setIndent(20)  # Indent the text
    currency_mapping_layout.addWidget(currency_mapping_info)

    mapping_layout.addRow(currency_mapping_section)

    scroll_layout.addWidget(mapping_group)

    # Date format section
    date_format_group = QGroupBox("Date Format")
    date_format_group.setMaximumHeight(150)  # Add this line to limit height
    date_format_layout = QFormLayout(date_format_group)
    date_format_layout.setSpacing(10)  # Reduce spacing if needed

    date_format_combo = QComboBox()
    #date_format_combo.setMinimumHeight(30)
    date_format_combo.addItems([
        "Auto-detect",
        "YYYY-MM-DD",
        "MM/DD/YYYY",
        "DD/MM/YYYY",
        "Custom..."
    ])
    date_format_layout.addRow("Format:", date_format_combo)

    # Add tooltips to help explain the UI
    date_combo.setToolTip("Select the column containing transaction dates")
    description_combo.setToolTip("Select the column containing transaction descriptions")
    amount_combo.setToolTip("Select the column containing transaction amounts (for single amount column)")
    debit_combo.setToolTip("Select the column containing debit amounts (money out)")
    credit_combo.setToolTip("Select the column containing credit amounts (money in)")
    account_col_combo.setToolTip("Select the column containing account names")
    currency_col_combo.setToolTip("Select the column containing currency information")


    custom_date_format = QLineEdit()
    #custom_date_format.setMinimumHeight(30)
    custom_date_format.setPlaceholderText("e.g., %Y-%m-%d or %d/%m/%Y")
    custom_date_format.setEnabled(False)
    date_format_layout.addRow("Custom Format:", custom_date_format)

    scroll_layout.addWidget(date_format_group)

    # Set the scroll area content and add to main layout
    scroll_area.setWidget(scroll_content)
    layout2.addWidget(scroll_area)

    # Register fields
    page2.registerField("dateColumn", date_combo, "currentText")
    page2.registerField("descriptionColumn", description_combo, "currentText")
    page2.registerField("amountColumn", amount_combo, "currentText")
    page2.registerField("debitColumn", debit_combo, "currentText")
    page2.registerField("creditColumn", credit_combo, "currentText")
    page2.registerField("accountColumn", account_col_combo, "currentText")
    page2.registerField("currencyColumn", currency_col_combo, "currentText")
    page2.registerField("dateFormat", date_format_combo, "currentText")
    page2.registerField("customDateFormat", custom_date_format)


    # ==================
    # Page 3: Preview & Import
    # ==================
    page3 = QWizardPage()
    page3.setTitle("Preview and Import")
    page3.setSubTitle("Review the data and click Finish to import")

    layout3 = QVBoxLayout(page3)
    layout3.setSpacing(10)
    layout3.setContentsMargins(20, 20, 20, 20)

    # Data preview
    preview_group = QGroupBox("Data Preview")
    preview_layout = QVBoxLayout(preview_group)

    data_preview = QTableView()
    data_preview.setMinimumHeight(300)
    data_preview.setAlternatingRowColors(True)
    data_model = QStandardItemModel()
    data_preview.setModel(data_model)

    # Enhance table appearance
    data_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    data_preview.horizontalHeader().setStretchLastSection(True)

    preview_layout.addWidget(data_preview)

    layout3.addWidget(preview_group)

    # Summary
    summary_group = QGroupBox("Import Summary")
    summary_layout = QFormLayout(summary_group)

    total_rows_label = QLabel("0")
    summary_layout.addRow("Total Rows:", total_rows_label)

    valid_rows_label = QLabel("0")
    summary_layout.addRow("Valid Rows:", valid_rows_label)

    invalid_rows_label = QLabel("0")
    summary_layout.addRow("Invalid Rows:", invalid_rows_label)

    layout3.addWidget(summary_group)

    # Notes/warnings
    notes_group = QGroupBox("Notes")
    notes_layout = QVBoxLayout(notes_group)

    notes_text = QTextEdit()
    notes_text.setReadOnly(True)
    notes_text.setMinimumHeight(100)
    notes_layout.addWidget(notes_text)

    layout3.addWidget(notes_group)

    # Add pages to wizard
    wizard.addPage(page1)
    wizard.addPage(page2)
    wizard.addPage(page3)

    # ==================
    # Helper Functions
    # ==================

    def save_page2_state():
        """Save the current state of all mapping fields"""
        wizard.saved_mappings['date'] = date_combo.currentText()
        wizard.saved_mappings['description'] = description_combo.currentText()
        wizard.saved_mappings['amount'] = amount_combo.currentText()
        wizard.saved_mappings['debit'] = debit_combo.currentText()
        wizard.saved_mappings['credit'] = credit_combo.currentText()
        wizard.saved_mappings['account'] = account_col_combo.currentText()
        wizard.saved_mappings['currency'] = currency_col_combo.currentText()
        wizard.saved_mappings['date_format'] = date_format_combo.currentText()
        wizard.saved_mappings['custom_date_format'] = custom_date_format.text()

        # Debug output
        print("SAVING STATE:")
        print(f"Saved mappings: {wizard.saved_mappings}")

    def restore_page2_state():
        """Restore previously saved mapping fields"""
        print("RESTORING STATE:")
        print(f"Current saved mappings: {wizard.saved_mappings}")

        # Helper function to safely set combo box value
        def set_combo_value(combo, value):
            if value and value != "Not mapped":
                index = combo.findText(value)
                if index >= 0:
                    combo.setCurrentIndex(index)
                    print(f"Set {combo.objectName() if combo.objectName() else 'combo'} to {value} at index {index}")
                else:
                    print(f"Could not find '{value}' in combo box")

        set_combo_value(date_combo, wizard.saved_mappings.get('date'))
        set_combo_value(description_combo, wizard.saved_mappings.get('description'))
        set_combo_value(amount_combo, wizard.saved_mappings.get('amount'))
        set_combo_value(debit_combo, wizard.saved_mappings.get('debit'))
        set_combo_value(credit_combo, wizard.saved_mappings.get('credit'))
        set_combo_value(account_col_combo, wizard.saved_mappings.get('account'))
        set_combo_value(currency_col_combo, wizard.saved_mappings.get('currency'))
        set_combo_value(date_format_combo, wizard.saved_mappings.get('date_format'))

        if wizard.saved_mappings.get('custom_date_format'):
            custom_date_format.setText(wizard.saved_mappings['custom_date_format'])

    # Modify browse_file to use this approach
    def browse_file():
        # Load config for initial directory
        config = load_config()
        initial_dir = config.get('last_import_path', '')

        # Fallback to desktop or home if path doesn't exist
        if not initial_dir or not os.path.exists(initial_dir):
            initial_dir = os.path.expanduser("~/Desktop")
        if not os.path.exists(initial_dir):
            initial_dir = os.path.expanduser("~")

        # Open dialog with initial directory
        file_path, _ = QFileDialog.getOpenFileName(parent, "Open CSV File", initial_dir, "CSV Files (*.csv)")

        if file_path:
            # Set path in UI
            file_path_edit.setText(file_path)
            update_preview(file_path)

            # Save directory only - not connected to wizard events
            directory = os.path.dirname(file_path)
            update_import_path(directory)

    def update_preview(file_path, max_lines=10):
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                preview_lines = []
                for i, line in enumerate(csvfile):
                    if i >= max_lines:
                        break
                    preview_lines.append(line.strip())

                preview_text.setPlainText('\n'.join(preview_lines))
        except Exception as e:
            preview_text.setPlainText(f"Error reading file: {str(e)}")

    def update_header_mapping(file_path):
        if not file_path or not os.path.exists(file_path):
            return

        try:
            # Clear current headers
            header_model.clear()

            # Detect CSV dialect
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                sample = csvfile.read(1024)
                csvfile.seek(0)

                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(sample)
                    has_header = sniffer.has_header(sample) if has_header_checkbox.isChecked() else False
                except:
                    # If sniffing fails, use defaults
                    dialect = csv.excel
                    has_header = has_header_checkbox.isChecked()

                reader = csv.reader(csvfile, dialect)

                # Get headers
                headers = next(reader) if has_header else []
                if not has_header:
                    # Create column numbers as headers
                    row = next(reader)
                    headers = [f"Column {i + 1}" for i in range(len(row))]

                # Display headers in the first row
                for i, header in enumerate(headers):
                    header_model.setItem(0, i, QStandardItem(header))

                # Get a real data row for the sample (not the header)
                csvfile.seek(0)
                reader = csv.reader(csvfile, dialect)

                # Skip the header if present
                if has_header:
                    next(reader)

                # Get the first data row
                sample_row = next(reader, None)
                if sample_row:
                    for i, cell in enumerate(sample_row):
                        if i < len(sample_row) and i < len(headers):
                            header_model.setItem(1, i, QStandardItem(cell))
                else:
                    # If no data row available, create empty cells
                    for i in range(len(headers)):
                        header_model.setItem(1, i, QStandardItem(""))
                if sample_row:
                    for i, cell in enumerate(sample_row):
                        if i < len(sample_row) and i < len(headers):
                            header_model.setItem(1, i, QStandardItem(cell))
                else:
                    # If no sample row, create empty cells for the second row
                    for i in range(len(headers)):
                        header_model.setItem(1, i, QStandardItem(""))

                # Update column combo boxes
                for combo in [date_combo, description_combo, amount_combo, debit_combo, credit_combo,
                              account_col_combo, currency_col_combo]:
                    combo.clear()
                    combo.addItem("Not mapped")
                    combo.addItems(headers)

                # Auto-map columns with improved detection
                best_matches = {
                    'date': {'score': 0, 'index': -1},
                    'description': {'score': 0, 'index': -1},
                    'amount': {'score': 0, 'index': -1},
                    'debit': {'score': 0, 'index': -1},
                    'credit': {'score': 0, 'index': -1},
                    'account': {'score': 0, 'index': -1},
                    'currency': {'score': 0, 'index': -1}
                }

                date_keywords = ['date', 'day', 'time', 'when']
                desc_keywords = ['desc', 'narr', 'detail', 'note', 'memo', 'part', 'ref', 'subject']
                amount_keywords = ['amount', 'sum', 'value', 'total', 'number']
                debit_keywords = ['debit', 'withdrawal', 'out', 'payment', 'dr', 'withdraw', 'spent']
                credit_keywords = ['credit', 'deposit', 'in', 'received', 'cr', 'income', 'incoming']
                account_keywords = ['account', 'acct', 'acc', 'category', 'cat', 'type', 'source']
                currency_keywords = ['currency', 'curr', 'ccy', 'fx', 'cur', 'money']

                for i, header in enumerate(headers):
                    header_lower = header.lower()

                    # Date mapping
                    for keyword in date_keywords:
                        if keyword in header_lower:
                            best_matches['date']['score'] += 10
                            best_matches['date']['index'] = i
                            # Exact match gets higher score
                            if header_lower == keyword:
                                best_matches['date']['score'] += 20

                    # Description mapping
                    for keyword in desc_keywords:
                        if keyword in header_lower:
                            best_matches['description']['score'] += 10
                            best_matches['description']['index'] = i
                            if header_lower == keyword or header_lower == 'description':
                                best_matches['description']['score'] += 20

                    # Amount mapping
                    for keyword in amount_keywords:
                        if keyword in header_lower:
                            best_matches['amount']['score'] += 10
                            best_matches['amount']['index'] = i
                            if header_lower == keyword:
                                best_matches['amount']['score'] += 20

                    # Debit mapping
                    for keyword in debit_keywords:
                        if keyword in header_lower:
                            best_matches['debit']['score'] += 10
                            best_matches['debit']['index'] = i
                            if header_lower == keyword:
                                best_matches['debit']['score'] += 20

                    # Credit mapping
                    for keyword in credit_keywords:
                        if keyword in header_lower:
                            best_matches['credit']['score'] += 10
                            best_matches['credit']['index'] = i
                            if header_lower == keyword:
                                best_matches['credit']['score'] += 20

                    # Account mapping
                    for keyword in account_keywords:
                        if keyword in header_lower:
                            best_matches['account']['score'] += 10
                            best_matches['account']['index'] = i
                            if header_lower == keyword:
                                best_matches['account']['score'] += 20

                    # Currency mapping
                    for keyword in currency_keywords:
                        if keyword in header_lower:
                            best_matches['currency']['score'] += 10
                            best_matches['currency']['index'] = i
                            if header_lower == keyword:
                                best_matches['currency']['score'] += 20

                # Apply best matches if score exceeds threshold
                if best_matches['date']['score'] > 0:
                    date_combo.setCurrentIndex(best_matches['date']['index'] + 1)  # +1 for "Not mapped"

                if best_matches['description']['score'] > 0:
                    description_combo.setCurrentIndex(best_matches['description']['index'] + 1)

                if best_matches['amount']['score'] > 0:
                    amount_combo.setCurrentIndex(best_matches['amount']['index'] + 1)
                elif best_matches['debit']['score'] == 0 and best_matches['credit']['score'] == 0:
                    # If no debit/credit but amount exists, use amount
                    for i, header in enumerate(headers):
                        if "amount" in header.lower():
                            amount_combo.setCurrentIndex(i + 1)
                            break

                if best_matches['debit']['score'] > 0:
                    debit_combo.setCurrentIndex(best_matches['debit']['index'] + 1)

                if best_matches['credit']['score'] > 0:
                    credit_combo.setCurrentIndex(best_matches['credit']['index'] + 1)

                if best_matches['account']['score'] > 0:
                    account_col_combo.setCurrentIndex(best_matches['account']['index'] + 1)

                if best_matches['currency']['score'] > 0:
                    currency_col_combo.setCurrentIndex(best_matches['currency']['index'] + 1)

                # Highlight mapped columns
                for i in range(header_model.columnCount()):
                    for col in range(header_model.columnCount()):
                        item = header_model.item(0, col)
                        if item:
                            # Reset background initially
                            item.setBackground(QColor(60, 60, 60))
                            item.setForeground(QColor(180, 180, 180))

                # Update the column highlighting to show mapping
                update_column_highlighting()

                # Try to auto-detect date format from sample data
                try:
                    if date_combo.currentText() != "Not mapped":
                        date_col_index = headers.index(date_combo.currentText())
                        # Get a few sample dates
                        sample_dates = []
                        csvfile.seek(0)
                        reader = csv.reader(csvfile, dialect)
                        if has_header:
                            next(reader)  # Skip header

                        for i, row in enumerate(reader):
                            if i >= 5:  # Get up to 5 samples
                                break
                            if len(row) > date_col_index:
                                sample_dates.append(row[date_col_index])

                        # Try to determine format from samples
                        if sample_dates:
                            # Common formats to try
                            formats = [
                                ("%Y-%m-%d", "YYYY-MM-DD"),
                                ("%m/%d/%Y", "MM/DD/YYYY"),
                                ("%d/%m/%Y", "DD/MM/YYYY"),
                                ("%Y/%m/%d", "YYYY/MM/DD")
                            ]

                            for fmt, display_fmt in formats:
                                try:
                                    # Try to parse the first date
                                    datetime.datetime.strptime(sample_dates[0], fmt)
                                    # If successful, select this format
                                    date_format_combo.setCurrentText(display_fmt)
                                    break
                                except:
                                    continue
                except:
                    # If auto-detection fails, leave as Auto-detect
                    pass

        except Exception as e:
            QMessageBox.warning(parent, "Error", f"Failed to parse CSV file: {str(e)}")

    def update_column_highlighting():
        """Highlight columns in the header preview based on current mapping"""
        # Get the current mapped columns
        mappings = {
            'date': date_combo.currentText(),
            'description': description_combo.currentText(),
            'amount': amount_combo.currentText(),
            'debit': debit_combo.currentText(),
            'credit': credit_combo.currentText(),
            'account': account_col_combo.currentText(),
            'currency': currency_col_combo.currentText()
        }

        # Remove "Not mapped" entries
        mappings = {k: v for k, v in mappings.items() if v != "Not mapped"}

        # Define colors for different field types
        colors = {
            'date': QColor(70, 130, 180),  # Steel blue
            'description': QColor(60, 179, 113),  # Medium sea green
            'amount': QColor(255, 165, 0),  # Orange
            'debit': QColor(178, 34, 34),  # Firebrick
            'credit': QColor(34, 139, 34),  # Forest green
            'account': QColor(138, 43, 226),  # Blue violet
            'currency': QColor(210, 105, 30)  # Chocolate
        }

        # Apply highlighting
        for i in range(header_model.columnCount()):
            item = header_model.item(0, i)
            if item:
                header_text = item.text()
                # Reset styling
                item.setBackground(QColor(60, 60, 60))
                item.setForeground(QColor(255, 255, 255))

                # Strip any existing field labels
                if " (" in header_text:
                    header_text = header_text.split(" (")[0]

                # Check if this column is mapped
                mapped_field = None
                for field, mapped_column in mappings.items():
                    if mapped_column == header_text:
                        mapped_field = field
                        break

                if mapped_field:
                    # For "Column X" headers, completely replace with field name
                    if header_text.startswith("Column "):
                        new_text = mapped_field.capitalize()  # e.g., "Date" instead of "Column 1 (date)"
                    else:
                        # For meaningful headers, keep original name with field type
                        new_text = f"{header_text} ({mapped_field})"

                    # Apply styling
                    item.setText(new_text)
                    item.setBackground(colors.get(mapped_field, QColor(100, 100, 100)))
                    item.setFont(QFont("Arial", 10, QFont.Bold))

                    # Apply lighter color to sample data
                    sample_item = header_model.item(1, i)
                    if sample_item:
                        lighter_color = QColor(colors.get(mapped_field, QColor(100, 100, 100)))
                        lighter_color.setAlpha(100)  # Make it semi-transparent
                        sample_item.setBackground(lighter_color)
                else:
                    # Set the original text for unmapped columns
                    item.setText(header_text)

    def update_account_mapping_visibility():
        account_mapping_section.setVisible(account_combo.currentText() == "Multiple accounts (in CSV)")

    def update_date_format_visibility():
        custom_date_format.setEnabled(date_format_combo.currentText() == "Custom...")

    def update_data_preview():
        if not wizard.field("filePath"):
            return

        try:
            file_path = wizard.field("filePath")
            has_header = wizard.field("hasHeader")

            # Get column mappings
            mappings = {
                'date': wizard.field("dateColumn"),
                'description': wizard.field("descriptionColumn"),
                'amount': wizard.field("amountColumn"),
                'debit': wizard.field("debitColumn"),
                'credit': wizard.field("creditColumn"),
                'account': wizard.field("accountColumn"),
                'currency': wizard.field("currencyColumn")
            }

            # Remove unmapped columns
            mappings = {k: v for k, v in mappings.items() if v != "Not mapped"}

            # Get date format
            date_format = wizard.field("dateFormat")
            if date_format == "Custom...":
                date_format = wizard.field("customDateFormat")
            elif date_format == "YYYY-MM-DD":
                date_format = "%Y-%m-%d"
            elif date_format == "MM/DD/YYYY":
                date_format = "%m/%d/%Y"
            elif date_format == "DD/MM/YYYY":
                date_format = "%d/%m/%Y"

            # Clear current preview
            data_model.clear()

            # Set up header
            headers = ["Date", "Description", "Debit", "Credit", "Account", "Currency", "Status"]
            data_model.setHorizontalHeaderLabels(headers)

            # Get default currency
            default_currency = wizard.field("currency")

            # Parse and display preview
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)

                # Get the actual CSV headers first
                csv_headers = []
                if has_header:
                    csv_headers = next(reader)

                # Create column index mapping directly from CSV headers
                col_indices = {}
                for field, mapped_column in mappings.items():
                    if mapped_column != "Not mapped":
                        try:
                            if has_header:
                                # Direct match with CSV headers
                                col_indices[field] = csv_headers.index(mapped_column)
                            else:
                                # For files without headers, extract column number
                                col_indices[field] = int(mapped_column.split()[-1]) - 1
                        except (ValueError, IndexError) as e:
                            print(f"Could not map {field} to {mapped_column}: {e}")
                            continue

                # Debug output
                print("=" * 50)
                print(f"CSV Headers from file: {csv_headers}")
                print(f"Mappings from wizard: {mappings}")
                print(f"Column Indices calculated: {col_indices}")
                print("=" * 50)

                total_rows = 0
                valid_rows = 0
                invalid_rows = 0

                for row_index, row in enumerate(reader):
                    if row_index >= 20:  # Limit preview to 20 rows
                        break

                    total_rows += 1

                    # Create a dict from the row using the pre-calculated indices
                    row_dict = {}
                    for field, col_index in col_indices.items():
                        if 0 <= col_index < len(row):
                            row_dict[field] = row[col_index]
                        else:
                            print(f"Column index {col_index} out of range for field {field}")

                    # Process the row
                    try:
                        preview_row = []

                        # Date
                        date_str = row_dict.get('date', '')
                        if date_str:
                            if date_format != "Auto-detect":
                                try:
                                    # Parse with specified format
                                    date_obj = datetime.datetime.strptime(date_str, date_format)
                                    date_str = date_obj.strftime("%Y-%m-%d")
                                except:
                                    date_str = f"{date_str} (format error)"
                            preview_row.append(QStandardItem(date_str))
                        else:
                            preview_row.append(QStandardItem(""))

                        # Description
                        description = row_dict.get('description', '')
                        preview_row.append(QStandardItem(description))

                        # Debit
                        debit = None
                        if 'debit' in row_dict:
                            try:
                                debit_str = row_dict['debit'].replace(',', '')
                                debit = float(debit_str) if debit_str else None
                                preview_row.append(QStandardItem(f"{debit:.2f}" if debit else ""))
                            except ValueError:
                                preview_row.append(QStandardItem("INVALID"))
                        elif 'amount' in row_dict:
                            try:
                                amount_str = row_dict['amount'].replace(',', '')
                                amount = float(amount_str) if amount_str else None
                                if amount and amount > 0:
                                    debit = amount
                                    preview_row.append(QStandardItem(f"{debit:.2f}"))
                                else:
                                    preview_row.append(QStandardItem(""))
                            except ValueError:
                                preview_row.append(QStandardItem("INVALID"))
                        else:
                            preview_row.append(QStandardItem(""))

                        # Credit
                        credit = None
                        if 'credit' in row_dict:
                            try:
                                credit_str = row_dict['credit'].replace(',', '')
                                credit = float(credit_str) if credit_str else None
                                preview_row.append(QStandardItem(f"{credit:.2f}" if credit else ""))
                            except ValueError:
                                preview_row.append(QStandardItem("INVALID"))
                        elif 'amount' in row_dict:
                            try:
                                amount_str = row_dict['amount'].replace(',', '')
                                amount = float(amount_str) if amount_str else None
                                if amount and amount < 0:
                                    credit = abs(amount)
                                    preview_row.append(QStandardItem(f"{credit:.2f}"))
                                else:
                                    preview_row.append(QStandardItem(""))
                            except ValueError:
                                preview_row.append(QStandardItem("INVALID"))
                        else:
                            preview_row.append(QStandardItem(""))

                        # Account
                        if wizard.field("account") == "Multiple accounts (in CSV)":
                            account = row_dict.get('account', '')
                            preview_row.append(QStandardItem(account))
                        else:
                            preview_row.append(QStandardItem(wizard.field("account")))

                        # Currency
                        if 'currency' in row_dict and row_dict['currency']:
                            currency = row_dict['currency']
                            preview_row.append(QStandardItem(currency))
                        else:
                            # Use default currency
                            preview_row.append(QStandardItem(default_currency))

                        # Status
                        is_valid = (
                            (debit is not None or credit is not None) and
                            description and
                            date_str
                        )

                        if is_valid:
                            valid_rows += 1
                            status_item = QStandardItem("Valid")
                            # Set green background for valid rows
                            for item in preview_row:
                                item.setBackground(QColor(0, 100, 0, 40))  # Light green
                        else:
                            invalid_rows += 1
                            status_item = QStandardItem("Missing data")
                            # Set red background for invalid rows
                            for item in preview_row:
                                item.setBackground(QColor(100, 0, 0, 40))  # Light red

                        preview_row.append(status_item)
                        data_model.appendRow(preview_row)

                    except Exception as e:
                        invalid_rows += 1
                        error_row = [
                            QStandardItem("ERROR"),
                            QStandardItem(str(e)),
                            QStandardItem(""),
                            QStandardItem(""),
                            QStandardItem(""),
                            QStandardItem(default_currency),
                            QStandardItem("Invalid")
                        ]
                        # Set red background for error rows
                        for item in error_row:
                            item.setBackground(QColor(120, 0, 0, 60))  # Darker red

                        data_model.appendRow(error_row)

                # Update summary labels

                total_rows_label.setText(str(total_rows))
                valid_rows_label.setText(str(valid_rows))
                invalid_rows_label.setText(str(invalid_rows))

                # Update notes
                notes = []
                if invalid_rows > 0:
                    notes.append(f"⚠️ {invalid_rows} rows have validation issues.")

                if not mappings.get('date'):
                    notes.append("❌ No date column mapped. Dates are required.")

                if not mappings.get('description'):
                    notes.append("⚠️ No description column mapped. Descriptions are recommended.")

                if not (mappings.get('amount') or (mappings.get('debit') and mappings.get('credit'))):
                    notes.append(
                        "❌ No amount columns mapped. Either 'Amount' or both 'Debit' and 'Credit' are required.")

                if wizard.field("account") == "Multiple accounts (in CSV)" and not mappings.get('account'):
                    notes.append("❌ You selected 'Multiple accounts' but no account column is mapped.")

                # Apply color-coding to notes
                styled_notes = []
                for note in notes:
                    if "❌" in note:
                        styled_notes.append(f"<span style='color:#ff5555;'>{note}</span>")
                    else:
                        styled_notes.append(f"<span style='color:#ffaa00;'>{note}</span>")

                notes_text.setHtml("<br>".join(styled_notes))

                # Update status of the finish button based on errors
                has_critical_errors = any("❌" in note for note in notes)
                wizard.button(QWizard.FinishButton).setEnabled(not has_critical_errors and valid_rows > 0)

        except Exception as e:
            QMessageBox.warning(parent, "Error", f"Failed to preview data: {str(e)}")


    def process_csv():
        try:
            file_path = wizard.field("filePath")
            reference = wizard.field("reference")
            has_header = wizard.field("hasHeader")

            # Get column mappings
            mappings = {
                'date': wizard.field("dateColumn"),
                'description': wizard.field("descriptionColumn"),
                'amount': wizard.field("amountColumn"),
                'debit': wizard.field("debitColumn"),
                'credit': wizard.field("creditColumn"),
                'account': wizard.field("accountColumn"),
                'currency': wizard.field("currencyColumn")
            }

            # Remove unmapped columns
            mappings = {k: v for k, v in mappings.items() if v != "Not mapped"}

            # Get date format
            date_format = wizard.field("dateFormat")
            if date_format == "Custom...":
                date_format = wizard.field("customDateFormat")
            elif date_format == "YYYY-MM-DD":
                date_format = "%Y-%m-%d"
            elif date_format == "MM/DD/YYYY":
                date_format = "%m/%d/%Y"
            elif date_format == "DD/MM/YYYY":
                date_format = "%d/%m/%Y"

            # Get default account if not using multiple accounts
            default_account_id = None
            if wizard.field("account") != "Multiple accounts (in CSV)":
                account_name = wizard.field("account")
                default_account_id = db.get_account_id(account_name)

            # Get default currency
            default_currency_id = None
            currency_name = wizard.field("currency")
            default_currency_id = db.get_currency_id(currency_name)

            # Process CSV
            lines_data = []

            # Read the entire CSV into memory once
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                all_rows = list(csv.reader(csvfile))

            # Split headers and data rows
            if has_header and all_rows:
                csv_headers = all_rows[0]
                data_rows = all_rows[1:]
            else:
                csv_headers = []
                data_rows = all_rows

            # Create column index mapping based on actual CSV headers
            col_indices = {}
            for field, mapped_column in mappings.items():
                if mapped_column != "Not mapped":
                    try:
                        # Find index in actual CSV headers
                        if has_header and mapped_column in csv_headers:
                            col_indices[field] = csv_headers.index(mapped_column)
                        else:
                            # For files without headers, extract column number
                            col_num = int(mapped_column.split()[-1]) - 1
                            col_indices[field] = col_num
                    except (ValueError, IndexError):
                        print(f"Could not map {field} to {mapped_column}")
                        continue

            # Debug: Print mapping information
            print("=" * 50)
            print(f"CSV Headers: {csv_headers}")
            print(f"Mappings: {mappings}")
            print(f"Column Indices: {col_indices}")
            print("=" * 50)

            # Process rows
            for row_index, row in enumerate(data_rows):
                    try:
                        # Get fields from the row
                        date_str = row[col_indices.get('date', -1)] if 'date' in col_indices and col_indices[
                            'date'] < len(row) else ''
                        description = row[col_indices.get('description', -1)] if 'description' in col_indices and \
                                                                                 col_indices['description'] < len(
                            row) else ''

                        # Handle amount, debit and credit
                        debit = None
                        credit = None

                        if 'debit' in col_indices and col_indices['debit'] < len(row):
                            debit_str = row[col_indices['debit']].replace(',', '').strip()
                            if debit_str:
                                try:
                                    debit = float(debit_str)
                                except ValueError:
                                    debit = None

                        if 'credit' in col_indices and col_indices['credit'] < len(row):
                            credit_str = row[col_indices['credit']].replace(',', '').strip()
                            if credit_str:
                                try:
                                    credit = float(credit_str)
                                except ValueError:
                                    credit = None

                        if debit is None and credit is None and 'amount' in col_indices and col_indices['amount'] < len(
                                row):
                            amount_str = row[col_indices['amount']].replace(',', '').strip()
                            if amount_str:
                                try:
                                    amount = float(amount_str)
                                    if amount > 0:
                                        debit = amount
                                    else:
                                        credit = abs(amount)
                                except ValueError:
                                    pass

                        # Get account if using multiple accounts
                        account_id = default_account_id
                        account_valid = True
                        account_name = None

                        if wizard.field("account") == "Multiple accounts (in CSV)" and 'account' in col_indices and \
                                col_indices['account'] < len(row):
                            account_name = row[col_indices['account']]
                            try:
                                account_id = db.get_account_id(account_name)
                            except:
                                # Instead of skipping, mark as invalid but keep the row
                                account_valid = False
                                account_id = None

                        # Get currency if specified
                        currency_id = default_currency_id
                        currency_valid = True

                        if 'currency' in col_indices and col_indices['currency'] < len(row):
                            currency_code = row[col_indices['currency']].strip()
                            if currency_code:
                                try:
                                    # Try to get currency by name
                                    currency_id = db.get_currency_id(currency_code)
                                except:
                                    # If not found by name, the default will be used
                                    currency_valid = False

                        # Format date
                        if date_str:
                            try:
                                if date_format != "Auto-detect":
                                    try:
                                        date_obj = datetime.datetime.strptime(date_str, date_format)
                                        date_str = date_obj.strftime("%Y-%m-%d")
                                    except ValueError:
                                        # Try common formats if specified format fails
                                        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                                            try:
                                                date_obj = datetime.datetime.strptime(date_str, fmt)
                                                date_str = date_obj.strftime("%Y-%m-%d")
                                                break
                                            except ValueError:
                                                continue
                            except:
                                # If date parsing fails, use current date
                                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                        else:
                            # Use current date if none provided
                            date_str = datetime.datetime.now().strftime("%Y-%m-%d")

                        # Only skip rows with no amount information at all
                        if debit is None and credit is None:
                            continue

                        # Create line data with validity information and currency
                        line = {
                            'description': description,
                            'account_id': account_id,
                            'account_name': account_name,  # Store the original name for reference
                            'debit': debit,
                            'credit': credit,
                            'date': date_str,
                            'currency_id': currency_id,
                            'valid': account_valid and currency_valid and (debit is not None or credit is not None)
                        }

                        # Debug output
                        print(f"Line {row_index}: {line}")
                        print(f"  account_valid: {account_valid}, currency_valid: {currency_valid}")
                        print(f"  debit: {debit}, credit: {credit}")
                        print(f"  valid: {line['valid']}")

                        lines_data.append(line)

                    except Exception as e:
                        print(f"Error processing row {row_index}: {str(e)}")
                        # Still add the row with error info
                        lines_data.append({
                            'description': f"Error in row {row_index + 1}: {str(e)}",
                            'account_id': None,
                            'account_name': None,
                            'debit': None,
                            'credit': None,
                            'date': datetime.datetime.now().strftime("%Y-%m-%d"),
                            'currency_id': default_currency_id,
                            'valid': False,
                        })
                        continue

            # Insert orphan transaction if we have any lines
            if lines_data:
                orphan_id = db.insert_orphan_transaction(reference, lines_data)
                return orphan_id
            else:
                QMessageBox.warning(parent, "Import Error", "No transaction lines found in the CSV file.")
                return None

        except Exception as e:
            QMessageBox.critical(parent, "Import Error", f"Failed to import CSV: {str(e)}")
            return None

    # ==================
    # Connect Signals
    # ==================


    browse_button.clicked.connect(browse_file)
    account_combo.currentIndexChanged.connect(update_account_mapping_visibility)
    date_format_combo.currentIndexChanged.connect(update_date_format_visibility)

    # Connect field mapping changes to update column highlighting
    for combo in [date_combo, description_combo, amount_combo, debit_combo, credit_combo,
                  account_col_combo, currency_col_combo]:
        combo.currentIndexChanged.connect(update_column_highlighting)


    # Connect wizard signals
    def on_current_id_changed(page_id):
        print(f"Page changed from {getattr(wizard, 'current_page_id', 'unknown')} to {page_id}")

        # Save state when leaving page 2 (index 1)
        if hasattr(wizard, 'current_page_id') and wizard.current_page_id == 1 and page_id != 1:
            save_page2_state()

        # Store current page ID for next time
        wizard.current_page_id = page_id

        # Handle page changes
        if page_id == 1:  # Second page (0-indexed)
            update_header_mapping(wizard.field("filePath"))
            update_account_mapping_visibility()
            update_date_format_visibility()

            # Use QTimer to restore state after the UI has been fully updated
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, restore_page2_state)

        elif page_id == 2:  # Third page
            # Save state before moving to page 3
            if wizard.current_page_id == 1:
                save_page2_state()
            update_data_preview()


    wizard.currentIdChanged.connect(on_current_id_changed)


    # Before completing, validate and process
    def on_finished():
        if wizard.result() == QWizard.Accepted:
            orphan_id = process_csv()
            if orphan_id:
                QMessageBox.information(
                    parent,
                    "Import Successful",
                    f"CSV imported successfully as orphan transaction batch #{orphan_id}.\n\n"
                    f"You can now process these transactions in the Orphan Transactions view."
                )

                # Return the orphan ID for further processing
                wizard.orphan_id = orphan_id

    wizard.finished.connect(on_finished)

    # Execute the wizard
    result = wizard.exec_()

    # Return the created orphan transaction ID if successful
    return getattr(wizard, 'orphan_id', None) if result == QWizard.Accepted else None

# Define function to load and save config
def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def update_import_path(directory):
    """Safely updates only the import path in config without disturbing other settings"""
    try:
        # Read current config
        config = load_config()

        # Update just the import path
        config['last_import_path'] = directory

        # Write back to file
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error updating import path: {e}")

def save_config(config):
    try:
        with open('config.json', 'w') as f:
            json.dump(config, indent=4, sort_keys=True)
    except:
        pass



def parse_csv_data(file_path, mapping):
    """Parse CSV data with column mapping"""
    lines_data = []

    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Process each row according to mapping
            line = {}

            # Map basic fields
            line['description'] = row.get(mapping['description'], '')
            line['date'] = row.get(mapping['date'], '')
            line['account_id'] = mapping['account_id']  # From wizard selection

            # Handle amount - this needs to determine debit vs. credit
            if 'amount' in mapping and mapping['amount'] in row:
                # Single amount column - determine debit/credit by sign or indicator
                amount_str = row[mapping['amount']].replace(',', '')

                # Check if there's a separate type/indicator column
                if 'type' in mapping and mapping['type'] in row:
                    type_indicator = row[mapping['type']].lower()
                    # Logic to determine if debit or credit based on indicator
                    is_credit = any(word in type_indicator for word in ['cr', 'credit', 'deposit', '+'])
                    is_debit = any(word in type_indicator for word in ['dr', 'debit', 'withdrawal', '-'])

                    if is_credit:
                        line['credit'] = abs(float(amount_str))
                        line['debit'] = None
                    elif is_debit:
                        line['debit'] = abs(float(amount_str))
                        line['credit'] = None
                else:
                    # No indicator - determine by sign
                    amount = float(amount_str)
                    if amount < 0:
                        line['credit'] = abs(amount)
                        line['debit'] = None
                    else:
                        line['debit'] = amount
                        line['credit'] = None
            else:
                # Separate debit and credit columns
                debit_str = row.get(mapping.get('debit', ''), '0')
                credit_str = row.get(mapping.get('credit', ''), '0')

                debit = float(debit_str.replace(',', '') or '0')
                credit = float(credit_str.replace(',', '') or '0')

                line['debit'] = debit if debit > 0 else None
                line['credit'] = credit if credit > 0 else None

            # Only add lines with valid amounts
            if line['debit'] or line['credit']:
                lines_data.append(line)

    return lines_data