import os
import csv
import datetime
from PyQt5.QtWidgets import (
    QDialog, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QCheckBox, QMessageBox,
    QFileDialog, QGroupBox, QFormLayout, QTextEdit, QTableView, QWidget
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
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

    # ==================
    # Page 1: File Selection and Basic Info
    # ==================
    page1 = QWizardPage()
    page1.setTitle("Select CSV File and Import Details")
    page1.setSubTitle("Please select a CSV file and provide basic information")

    layout1 = QVBoxLayout(page1)

    # File selection
    file_group = QGroupBox("CSV File")
    file_layout = QVBoxLayout(file_group)

    file_selector = QHBoxLayout()
    file_path_edit = QLineEdit()
    file_path_edit.setReadOnly(True)
    browse_button = QPushButton("Browse...")
    file_selector.addWidget(file_path_edit)
    file_selector.addWidget(browse_button)

    file_layout.addLayout(file_selector)

    # CSV preview
    preview_label = QLabel("File Preview:")
    file_layout.addWidget(preview_label)

    preview_text = QTextEdit()
    preview_text.setReadOnly(True)
    preview_text.setMaximumHeight(150)
    file_layout.addWidget(preview_text)

    layout1.addWidget(file_group)

    # Import details
    details_group = QGroupBox("Import Details")
    details_layout = QFormLayout(details_group)

    reference_edit = QLineEdit()
    details_layout.addRow("Import Reference:", reference_edit)

    account_combo = QComboBox()
    account_combo.addItem("Multiple accounts (in CSV)")
    accounts = db.get_all_accounts()
    for account in accounts:
        account_combo.addItem(account[1])
    details_layout.addRow("Source Account:", account_combo)

    has_header_checkbox = QCheckBox("CSV has header row")
    has_header_checkbox.setChecked(True)
    details_layout.addRow("", has_header_checkbox)

    layout1.addWidget(details_group)

    # Register fields
    page1.registerField("filePath*", file_path_edit)
    page1.registerField("reference*", reference_edit)
    page1.registerField("account", account_combo, "currentText")
    page1.registerField("hasHeader", has_header_checkbox)

    # ==================
    # Page 2: CSV Mapping
    # ==================
    page2 = QWizardPage()
    page2.setTitle("Map CSV Columns")
    page2.setSubTitle("Please map the CSV columns to the appropriate fields")

    layout2 = QVBoxLayout(page2)

    # Header preview
    header_group = QGroupBox("CSV Headers")
    header_layout = QVBoxLayout(header_group)

    header_preview = QTableView()
    header_model = QStandardItemModel()
    header_preview.setModel(header_model)
    header_layout.addWidget(header_preview)

    layout2.addWidget(header_group)

    # Mapping fields
    mapping_group = QGroupBox("Field Mapping")
    mapping_layout = QFormLayout(mapping_group)

    date_combo = QComboBox()
    description_combo = QComboBox()
    amount_combo = QComboBox()
    debit_combo = QComboBox()
    credit_combo = QComboBox()

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
    account_mapping_layout = QFormLayout(account_mapping_section)

    account_col_combo = QComboBox()
    account_col_combo.addItem("Not mapped")
    account_mapping_layout.addRow("Account Column:", account_col_combo)

    account_mapping_info = QLabel("The account column should contain account names that match your system")
    account_mapping_info.setWordWrap(True)
    account_mapping_layout.addRow("", account_mapping_info)

    mapping_layout.addRow(account_mapping_section)

    layout2.addWidget(mapping_group)

    # Date format section
    date_format_group = QGroupBox("Date Format")
    date_format_layout = QFormLayout(date_format_group)

    date_format_combo = QComboBox()
    date_format_combo.addItems([
        "Auto-detect",
        "YYYY-MM-DD",
        "MM/DD/YYYY",
        "DD/MM/YYYY",
        "Custom..."
    ])
    date_format_layout.addRow("Format:", date_format_combo)

    custom_date_format = QLineEdit()
    custom_date_format.setPlaceholderText("e.g., %Y-%m-%d or %d/%m/%Y")
    custom_date_format.setEnabled(False)
    date_format_layout.addRow("Custom Format:", custom_date_format)

    layout2.addWidget(date_format_group)

    # Register fields
    page2.registerField("dateColumn", date_combo, "currentText")
    page2.registerField("descriptionColumn", description_combo, "currentText")
    page2.registerField("amountColumn", amount_combo, "currentText")
    page2.registerField("debitColumn", debit_combo, "currentText")
    page2.registerField("creditColumn", credit_combo, "currentText")
    page2.registerField("accountColumn", account_col_combo, "currentText")
    page2.registerField("dateFormat", date_format_combo, "currentText")
    page2.registerField("customDateFormat", custom_date_format)

    # ==================
    # Page 3: Preview & Import
    # ==================
    page3 = QWizardPage()
    page3.setTitle("Preview and Import")
    page3.setSubTitle("Review the data and click Finish to import")

    layout3 = QVBoxLayout(page3)

    # Data preview
    preview_group = QGroupBox("Data Preview")
    preview_layout = QVBoxLayout(preview_group)

    data_preview = QTableView()
    data_model = QStandardItemModel()
    data_preview.setModel(data_model)
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
    notes_layout.addWidget(notes_text)

    layout3.addWidget(notes_group)

    # Add pages to wizard
    wizard.addPage(page1)
    wizard.addPage(page2)
    wizard.addPage(page3)

    # ==================
    # Helper Functions
    # ==================

    def browse_file():
        file_path, _ = QFileDialog.getOpenFileName(parent, "Open CSV File", "", "CSV Files (*.csv)")
        if file_path:
            file_path_edit.setText(file_path)
            update_preview(file_path)

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
                dialect = sniffer.sniff(sample)
                has_header = sniffer.has_header(sample) if has_header_checkbox.isChecked() else False

                reader = csv.reader(csvfile, dialect)

                # Get headers
                headers = next(reader) if has_header else []
                if not has_header:
                    # Create column numbers as headers
                    row = next(reader)
                    headers = [f"Column {i + 1}" for i in range(len(row))]

                # Display headers
                for i, header in enumerate(headers):
                    header_model.setItem(0, i, QStandardItem(header))

                # Add sample data row
                if has_header:
                    row = next(reader, None)
                    if row:
                        for i, cell in enumerate(row):
                            header_model.setItem(1, i, QStandardItem(cell))

                # Update column combo boxes
                for combo in [date_combo, description_combo, amount_combo, debit_combo, credit_combo,
                              account_col_combo]:
                    combo.clear()
                    combo.addItem("Not mapped")
                    combo.addItems(headers)

                # Auto-map columns based on common names
                for i, header in enumerate(headers):
                    header_lower = header.lower()

                    # Date mapping
                    if any(word in header_lower for word in ['date', 'day', 'time']):
                        date_combo.setCurrentIndex(i + 1)  # +1 for "Not mapped"

                    # Description mapping
                    if any(word in header_lower for word in ['desc', 'narr', 'detail', 'note', 'memo']):
                        description_combo.setCurrentIndex(i + 1)

                    # Amount mapping
                    if header_lower == 'amount' or header_lower == 'sum' or header_lower == 'value':
                        amount_combo.setCurrentIndex(i + 1)

                    # Debit mapping
                    if any(word in header_lower for word in ['debit', 'withdrawal', 'out', 'payment']):
                        debit_combo.setCurrentIndex(i + 1)

                    # Credit mapping
                    if any(word in header_lower for word in ['credit', 'deposit', 'in', 'received']):
                        credit_combo.setCurrentIndex(i + 1)

                    # Account mapping
                    if any(word in header_lower for word in ['account', 'acct', 'acc']):
                        account_col_combo.setCurrentIndex(i + 1)

        except Exception as e:
            QMessageBox.warning(parent, "Error", f"Failed to parse CSV file: {str(e)}")

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
                'account': wizard.field("accountColumn")
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
            headers = ["Date", "Description", "Debit", "Credit", "Account", "Status"]
            data_model.setHorizontalHeaderLabels(headers)

            # Parse and display preview
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)

                # Skip header if needed
                if has_header:
                    next(reader)

                total_rows = 0
                valid_rows = 0
                invalid_rows = 0

                for row_index, row in enumerate(reader):
                    if row_index >= 20:  # Limit preview to 20 rows
                        break

                    total_rows += 1

                    # Create a dict from the row
                    row_dict = {}
                    for col_name, header_name in mappings.items():
                        col_index = header_model.horizontalHeaderItem(0).text().index(header_name)
                        if col_index < len(row):
                            row_dict[col_name] = row[col_index]

                    # Process the row
                    try:
                        preview_row = []

                        # Date
                        date_str = row_dict.get('date', '')
                        if date_str:
                            if date_format != "Auto-detect":
                                # Parse with specified format
                                date_obj = datetime.datetime.strptime(date_str, date_format)
                                date_str = date_obj.strftime("%Y-%m-%d")
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

                        # Status
                        is_valid = (
                                (debit is not None or credit is not None) and
                                description and
                                date_str
                        )

                        if is_valid:
                            valid_rows += 1
                            preview_row.append(QStandardItem("Valid"))
                        else:
                            invalid_rows += 1
                            preview_row.append(QStandardItem("Missing data"))

                        data_model.appendRow(preview_row)

                    except Exception as e:
                        invalid_rows += 1
                        error_row = [
                            QStandardItem("ERROR"),
                            QStandardItem(str(e)),
                            QStandardItem(""),
                            QStandardItem(""),
                            QStandardItem(""),
                            QStandardItem("Invalid")
                        ]
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

                notes_text.setHtml("<br>".join(notes))

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
                'account': wizard.field("accountColumn")
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

            # Process CSV
            lines_data = []

            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)

                # Skip header if needed
                if has_header:
                    headers = next(reader)

                # Create column index mapping
                col_indices = {}
                for field, header in mappings.items():
                    if header != "Not mapped":
                        try:
                            col_indices[field] = headers.index(header) if has_header else int(header.split()[-1]) - 1
                        except (ValueError, IndexError):
                            continue

                # Process rows
                for row_index, row in enumerate(reader):
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
                        if wizard.field("account") == "Multiple accounts (in CSV)" and 'account' in col_indices and \
                                col_indices['account'] < len(row):
                            account_name = row[col_indices['account']]
                            try:
                                account_id = db.get_account_id(account_name)
                            except:
                                # Skip rows with invalid accounts
                                continue

                        # Format date
                        if date_str:
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
                        else:
                            # Use current date if none provided
                            date_str = datetime.datetime.now().strftime("%Y-%m-%d")

                        # Skip rows with no amount
                        if debit is None and credit is None:
                            continue

                        # Create line data
                        line = {
                            'description': description,
                            'account_id': account_id,
                            'debit': debit,
                            'credit': credit,
                            'date': date_str
                        }

                        lines_data.append(line)

                    except Exception as e:
                        print(f"Error processing row {row_index}: {str(e)}")
                        continue

            # Insert orphan transaction if we have valid lines
            if lines_data:
                orphan_id = db.insert_orphan_transaction(reference, lines_data)
                return orphan_id
            else:
                QMessageBox.warning(parent, "Import Error", "No valid transaction lines found in the CSV file.")
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

    # Connect wizard signals
    def on_current_id_changed(page_id):
        if page_id == 1:  # Second page (0-indexed)
            update_header_mapping(wizard.field("filePath"))
            update_account_mapping_visibility()
        elif page_id == 2:  # Third page
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