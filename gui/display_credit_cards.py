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


def display_credit_cards(content_frame, toolbar):
    # Clear existing layout
    #print('Starting to display credit cards')
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
    #print('clearing toolbar')
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
    statement_action = QAction(QIcon('icons/statement.png'), "Statement", toolbar)

    toolbar.insertAction(actions_to_keep[0], add_action)
    toolbar.insertAction(actions_to_keep[0], edit_action)
    toolbar.insertAction(actions_to_keep[0], delete_action)
    toolbar.insertAction(actions_to_keep[0], statement_action)

    # Connect actions
    add_action.triggered.connect(lambda: add_credit_card(content_frame, table_view))
    edit_action.triggered.connect(lambda: edit_credit_card(content_frame, table_view))
    delete_action.triggered.connect(lambda: delete_credit_card(content_frame, table_view))
    statement_action.triggered.connect(lambda: view_credit_card_statement(content_frame, table_view))

    # Load data
    load_credit_cards(table_view)


def load_credit_cards(table_view):
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["ID", "Account Name", "Credit Limit", "Close Day", "Due Day", "Currency"])

    # Get credit cards from database
    credit_cards = db.get_all_credit_cards()
    print(credit_cards)
    for card in credit_cards:
        print(card)
        #cc.id, a.name, cc.credit_limit, cc.close_day, cc.due_day, cu.name as currency
        #card_id, account_id, account_name, credit_limit, close_day, due_day, currency_name = card
        card_id, account_name, credit_limit, close_day, due_day, currency_name = card
        id_item = QStandardItem(str(card_id))
        name_item = QStandardItem(account_name)
        limit_item = QStandardItem(str(credit_limit))
        close_day_item = QStandardItem(str(close_day))
        due_day_item = QStandardItem(str(due_day))
        currency_item = QStandardItem(currency_name)

        # Set alignment for the ID column
        id_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        limit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        close_day_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        due_day_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Set UserRole data for proper sorting
        id_item.setData(int(card_id), Qt.UserRole)  # Sort ID as number
        name_item.setData(account_name.lower(), Qt.UserRole)  # Sort name case-insensitive
        limit_item.setData(int(credit_limit), Qt.UserRole)  # Sort limit as number
        close_day_item.setData(int(close_day), Qt.UserRole)  # Sort close day as number
        due_day_item.setData(int(due_day), Qt.UserRole)  # Sort close day as number
        currency_item.setData(currency_name.lower(), Qt.UserRole)  # Sort currency case-insensitive

        model.appendRow([id_item, name_item, limit_item, close_day_item, due_day_item, currency_item])

    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model)
    proxy_model.setSortRole(Qt.UserRole)  # Use UserRole for all columns

    # Set the proxy model to the table view
    table_view.setModel(proxy_model)
    table_view.setColumnWidth(0, 60)
    table_view.setColumnWidth(1, 200)
    table_view.setColumnWidth(2, 100)
    table_view.setColumnWidth(3, 80)
    table_view.setColumnWidth(4, 80)
    table_view.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)


def add_credit_card(parent, table_view):
    # Get currencies for dropdown
    currencies = [curr[1] for curr in db.get_all_currencies()]

    fields = [
        {'id': 'name', 'label': 'Credit Card Name', 'type': 'text', 'required': True},
        {'id': 'currency', 'label': 'Currency', 'type': 'combobox', 'options': currencies, 'required': True},
        {'id': 'credit_limit', 'label': 'Credit Limit', 'type': 'number', 'required': True},
        {'id': 'close_day', 'label': 'Statement Close Day', 'type': 'integer', 'required': True},
        {'id': 'due_day', 'label': 'Payment Due Day', 'type': 'integer', 'required': True}
    ]

    data = show_entity_dialog(parent, "Add Credit Card", fields)
    if data:
        try:
            # Get liability category ID
            liability_cat_id = db.get_category_id("Liability")
            if not liability_cat_id:
                # Create Liability category if not exists
                liability_cat_id = db.insert_category("Liability")

            # Get currency ID
            currency_id = db.get_currency_id(data['currency'])

            # Insert account
            account_id = db.insert_account(data['name'], liability_cat_id, currency_id)

            # Insert credit card
            credit_limit = float(data['credit_limit'])
            close_day = int(data['close_day'])
            due_day = int(data['due_day'])

            db.insert_credit_card(account_id, credit_limit, close_day, due_day)

            load_credit_cards(table_view)
            QMessageBox.information(parent, "Success", "Credit card added successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add credit card: {e}")


def edit_credit_card(parent, table_view):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a credit card to edit.")
        return

    card_id = int(row_data["ID"])

    # Get credit card details including account_id
    card_details = db.get_credit_card_by_id(card_id)
    if not card_details:
        QMessageBox.critical(parent, "Error", "Failed to retrieve credit card details.")
        return

    account_id = card_details['account_id']
    account_details = db.get_account_details(account_id)

    # Get currencies for dropdown
    currencies = [curr[1] for curr in db.get_all_currencies()]

    fields = [
        {'id': 'name', 'label': 'Credit Card Name', 'type': 'text', 'required': True},
        {'id': 'currency', 'label': 'Currency', 'type': 'combobox', 'options': currencies, 'required': True},
        {'id': 'credit_limit', 'label': 'Credit Limit', 'type': 'number', 'required': True},
        {'id': 'close_day', 'label': 'Statement Close Day', 'type': 'integer', 'required': True},
        {'id': 'due_day', 'label': 'Payment Due Day', 'type': 'integer', 'required': True}
    ]

    initial_data = {
        'name': row_data["Account Name"],
        'currency': account_details['currency_name'],
        'credit_limit': float(row_data["Credit Limit"]),
        'close_day': int(row_data["Close Day"]),
        'due_day': int(row_data["Due Day"])
    }

    data = show_entity_dialog(parent, "Edit Credit Card", fields, initial_data)

    if data:
        try:
            # Get currency ID
            currency_id = db.get_currency_id(data['currency'])

            # Update account
            db.update_account(account_id, data['name'], account_details['category_id'], currency_id)

            # Update credit card
            credit_limit = float(data['credit_limit'])
            close_day = int(data['close_day'])
            due_day = int(data['due_day'])

            db.update_credit_card(account_id, credit_limit, close_day, due_day)

            load_credit_cards(table_view)
            QMessageBox.information(parent, "Success", "Credit card updated successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to update credit card: {e}")


def delete_credit_card(parent, table_view):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a credit card to delete.")
        return

    card_id = int(row_data["ID"])
    card_name = row_data["Account Name"]

    # Get the account ID for this credit card
    card_details = db.get_credit_card_by_id(card_id)
    if not card_details:
        QMessageBox.critical(parent, "Error", "Failed to retrieve credit card details.")
        return

    account_id = card_details['account_id']

    # Check if credit card has transactions
    has_transactions = db.account_has_transactions(account_id)

    message = f"Are you sure you want to delete the credit card '{card_name}'?"
    if has_transactions:
        message += "\n\nWARNING: This credit card has transactions. Deleting it will also delete all associated transactions."

    reply = QMessageBox.question(
        parent,
        "Confirm Deletion",
        message,
        QMessageBox.Yes | QMessageBox.No
    )

    if reply == QMessageBox.Yes:
        try:
            # Delete credit card record
            db.delete_credit_card(account_id)

            # Delete the account
            db.delete_account(account_id)

            load_credit_cards(table_view)
            QMessageBox.information(parent, "Success", "Credit card deleted successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to delete credit card: {e}")


def view_credit_card_statement(parent, table_view):
    row_data = get_selected_row_data(table_view)
    if not row_data:
        QMessageBox.warning(parent, "Warning", "Please select a credit card to view statement.")
        return

    card_id = int(row_data["ID"])
    card_name = row_data["Account Name"]

    # Get account ID for this credit card
    card_details = db.get_credit_card_by_id(card_id)
    if not card_details:
        QMessageBox.critical(parent, "Error", "Failed to retrieve credit card details.")
        return

    account_id = card_details['account_id']

    # Select statement period (month/year)
    fields = [
        {'id': 'month', 'label': 'Month', 'type': 'combobox',
         'options': ["January", "February", "March", "April", "May", "June",
                     "July", "August", "September", "October", "November", "December"],
         'required': True},
        {'id': 'year', 'label': 'Year', 'type': 'combobox',
         'options': [str(year) for year in range(2020, 2026)], 'required': True}
    ]

    period_data = show_entity_dialog(parent, f"Select Statement Period for {card_name}", fields)

    if period_data:
        try:
            month_names = ["January", "February", "March", "April", "May", "June",
                           "July", "August", "September", "October", "November", "December"]
            month_num = month_names.index(period_data['month']) + 1
            year = int(period_data['year'])

            # Get statement data
            statement = db.get_credit_card_statement(account_id, month_num, year)

            if not statement or len(statement) == 0:
                QMessageBox.information(
                    parent,
                    "No Data",
                    f"No transactions found for {period_data['month']} {period_data['year']}."
                )
                return

            # Display statement
            display_statement(parent, card_name, statement, month_num, year)

        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to retrieve statement: {e}")


def display_statement(parent, card_name, statement_data, month, year):
    """
    Create a new dialog to display credit card statement.
    This is a placeholder - you would typically create a more detailed statement view.
    """
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    month_name = month_names[month - 1]

    message = f"Credit Card Statement for {card_name}\n"
    message += f"Period: {month_name} {year}\n\n"

    total_spent = 0
    for trans in statement_data:
        date = trans['date']
        description = trans['description']
        amount = trans['amount']
        total_spent += amount
        message += f"{date}: {description} - {amount:.2f}\n"

    message += f"\nTotal: {total_spent:.2f}"

    QMessageBox.information(parent, "Credit Card Statement", message)