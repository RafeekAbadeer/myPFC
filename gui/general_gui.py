import json
import os
from PyQt5.QtWidgets import (
    QMainWindow, QTreeView, QVBoxLayout, QToolBar, QWidget, QAction, QMessageBox,
    QSplitter, QFrame, QCheckBox, QSizePolicy, QLabel, QAbstractItemView, QLineEdit, QComboBox, QPushButton
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtCore import Qt, QSize, QByteArray, QSettings, QModelIndex
from database import Database
from gui.display_categories import display_categories
from gui.display_accounts import display_accounts
from gui.display_credit_cards import display_credit_cards
from gui.display_transactions import display_transactions
from gui.display_currencies import display_currencies
from gui.display_classifications import display_classifications

class Application(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_file = 'config.json'
        self.setWindowTitle("Personal Finance Manager")
        # Load configuration
        self.config = self.load_config()
        # Apply settings from config
        self.resize(
            self.config.get('window_width', 800),
            self.config.get('window_height', 600)
        )
        # Apply window state if available
        window_state = self.config.get('window_state', 0)  # 0 = normal state
        if window_state == 2: # Qt.WindowMaximized is 2
            self.setWindowState(Qt.WindowMaximized)
        # Set initial splitter position if available
        self.splitter_pos = self.config.get('splitter_position', [200, 600])
        self.database = Database("finance.db")
        self.color_mode = self.config.get('color_mode', 'dark')
        self.dark_mode_enabled = self.color_mode == 'dark'
        self.apply_color_mode(self.color_mode)
        self.create_menu()
        self.create_widgets()

    # Add a method to save window size
    def resizeEvent(self, event):
        # Update config with new window size
        if not (self.windowState() & Qt.WindowMaximized):
            config = self.load_config()
            config['window_width'] = self.width()
            config['window_height'] = self.height()
            self.save_config(config)
        super().resizeEvent(event)

    # Add a method to save window state
    def changeEvent(self, event):
        if event.type() == event.WindowStateChange:
            # Save the new window state when it changes
            config = self.load_config()
            # Store if maximized (2) or normal (0)
            if self.windowState() & Qt.WindowMaximized:
                config['window_state'] = 2
            else:
                config['window_state'] = 0  # Normal state
            self.save_config(config)
        super().changeEvent(event)

    def save_color_mode(self, mode):
        config = self.load_config()
        config['color_mode'] = mode
        self.save_config(config)

    def load_color_mode(self):
        config = self.load_config()
        return config.get('color_mode', 'dark')

    def save_tree_state(self):
        """Save the expansion state of the tree view"""
        expanded_items = []
        model = self.tree.model()

        def process_item(parent_index, parent_path=""):
            rows = model.rowCount(parent_index)
            for row in range(rows):
                current_index = model.index(row, 0, parent_index)
                current_item = model.itemFromIndex(current_index)
                current_path = f"{parent_path}/{current_item.text()}" if parent_path else current_item.text()

                if self.tree.isExpanded(current_index):
                    expanded_items.append(current_path)

                # Process children
                process_item(current_index, current_path)

        # Start processing from root
        process_item(QModelIndex())

        # Save the expanded items
        config = self.load_config()
        config['expanded_items'] = expanded_items
        self.save_config(config)

    def restore_tree_state(self):
        """Restore the expansion state of the tree view"""
        config = self.load_config()
        expanded_items = config.get('expanded_items', [])

        if not expanded_items:
            return

        model = self.tree.model()

        def find_index_by_path(path):
            path_parts = path.split('/')
            current_index = QModelIndex()

            for part in path_parts:
                found = False
                rows = model.rowCount(current_index)

                for row in range(rows):
                    index = model.index(row, 0, current_index)
                    item = model.itemFromIndex(index)

                    if item.text() == part:
                        current_index = index
                        found = True
                        break

                if not found:
                    return None

            return current_index

        # Expand all the saved items
        for path in expanded_items:
            index = find_index_by_path(path)
            if index:
                self.tree.setExpanded(index, True)

    def save_config(self, config):
        """Save configuration to file"""
        with open(self.config_file, 'w') as config_f:
            json.dump(config, config_f, indent=4)

    def load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as config_f:
                return json.load(config_f)
        except FileNotFoundError:
            return {'color_mode': 'dark', 'expanded_items': []}

    def create_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        add_menu = menu_bar.addMenu("Add")
        add_menu.addAction("Category", self.add_category)
        add_menu.addAction("Currency", self.add_currency)
        add_menu.addAction("Account", self.add_account)
        add_menu.addAction("Credit Card", self.add_credit_card)
        add_menu.addAction("Transaction", self.add_transaction)
        add_menu.addAction("Classification", self.add_classification)

        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction("About", self.show_about)

    def create_widgets(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.splitterMoved.connect(self.on_splitter_moved)
        self.left_section = QWidget()
        self.left_layout = QVBoxLayout(self.left_section)
        self.left_layout.setContentsMargins(10, 10, 0, 10)
        splitter.addWidget(self.left_section)

        self.tree = QTreeView()
        self.tree.setHeaderHidden(True)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Disable editing
        self.left_layout.addWidget(self.tree)
        self.right_section = QWidget()
        self.right_layout = QVBoxLayout(self.right_section)
        self.right_layout.setContentsMargins(0, 10, 0, 0)
        self.right_layout.setSpacing(0)

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(20,20))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolbar.setMovable(False)
        self.right_layout.addWidget(self.toolbar)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        self.dark_mode_switch = QCheckBox("")
        self.dark_mode_switch.setChecked(self.dark_mode_enabled)
        self.dark_mode_switch.stateChanged.connect(self.toggle_dark_mode)
        self.toolbar.addWidget(self.dark_mode_switch)
        self.dark_mode_switch.setStyleSheet(open("dark_mode.qss").read())

        self.content_frame = QFrame()
        self.right_layout.addWidget(self.content_frame)
        splitter.addWidget(self.right_section)
        self.splitter = splitter
        if hasattr(self, 'splitter_pos') and len(self.splitter_pos) == 2:
            splitter.setSizes(self.splitter_pos)
        splitter.setStretchFactor(1, 3)
        self.setCentralWidget(splitter)
        self.setup_treeview()
        self.tree.selectionModel().selectionChanged.connect(self.tree_selection_event)
        self.restore_tree_state()

    def on_splitter_moved(self, pos, index):
        # Save the splitter position
        config = self.load_config()
        config['splitter_position'] = [pos, self.splitter.width() - pos]
        self.save_config(config)

    def closeEvent(self, event):
        # Save tree state before closing
        self.save_tree_state()
        # Save any other settings here
        config = self.load_config()
        if self.windowState() & Qt.WindowMaximized:
            config['window_state'] = 2
        else:
            config['window_state'] = 0
            # Only save size if not maximized
            config['window_width'] = self.width()
            config['window_height'] = self.height()

        self.save_config(config)
        event.accept()

    def toggle_dark_mode(self, state):
        try:
            print("Toggling Dark Mode...")  # Debug statement
            if state == Qt.Checked:
                self.apply_color_mode('dark')
                self.dark_mode_switch.setText("")
                self.save_color_mode('dark')
            else:
                self.apply_color_mode('light')
                self.dark_mode_switch.setText("")
                self.save_color_mode('light')
        except Exception as e:
            print(f"Error in toggle_dark_mode: {e}")

    def apply_color_mode(self, mode):
        print(f'Applying {1} mode', mode)
        stylesheet = mode + "_mode.qss"
        if not os.path.exists(stylesheet):
            QMessageBox.critical(self, "Error", f"Stylesheet {stylesheet} not found.")
            return
        try:
            with open(stylesheet, "r") as f:
                self.setStyleSheet(f.read())
            self.dark_mode_enabled = mode == 'dark'
            print(f'{mode} Mode Applied.')
        except Exception as e:
            print(f"Error in apply_dark_mode: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred while applying {mode} mode: {e}")

    def setup_treeview(self):
        model = QStandardItemModel()
        root_node = model.invisibleRootItem()
        dashboard_item = QStandardItem("Dashboard")
        transactions_item = QStandardItem("Transactions")
        statements_item = QStandardItem("Financial Statements")
        statements_item.appendRow(QStandardItem("Journal"))
        statements_item.appendRow(QStandardItem("Income Statement"))
        statements_item.appendRow(QStandardItem("Balance Sheet"))
        statements_item.appendRow(QStandardItem("Cash flow"))
        reports_item = QStandardItem("Reports")
        tools_item = QStandardItem("Tools")
        settings_item = QStandardItem("Settings")
        root_node.appendRow(dashboard_item)
        root_node.appendRow(transactions_item)
        root_node.appendRows([statements_item, reports_item, tools_item])
        root_node.appendRow(settings_item)
        settings_item.appendRow(QStandardItem("Categories"))
        settings_item.appendRow(QStandardItem("Accounts"))
        settings_item.appendRow(QStandardItem("Credit Cards"))
        settings_item.appendRow(QStandardItem("Currencies"))
        settings_item.appendRow(QStandardItem("Classifications"))
        #self.tree.setAlternatingRowColors(True)
        self.tree.setModel(model)
        #self.tree.expandAll()
        self.tree.expanded.connect(self.on_tree_expanded)
        self.tree.collapsed.connect(self.on_tree_collapsed)

    def on_tree_expanded(self, index):
        # Save tree state whenever an item is expanded
        self.save_tree_state()

    def on_tree_collapsed(self, index):
        # Save tree state whenever an item is collapsed
        self.save_tree_state()

    def tree_selection_event(self, selected, deselected):
        try:
            selected_index = self.tree.selectionModel().currentIndex()
            selected_item = selected_index.model().itemFromIndex(selected_index).text()
            print(f"Selected item: {selected_item}")

            layout = self.content_frame.layout()
            if layout is not None:
                self.clear_layout(layout)
            else:
                layout = QVBoxLayout()
                self.content_frame.setLayout(layout)

            display_functions = {
                "Dashboard": self.display_dashboard,
                "Categories": self.display_categories,
                "Accounts": self.display_accounts,
                "Credit Cards": self.display_credit_cards,
                "Transactions": self.display_transactions,
                "Currencies": self.display_currencies,
                "Classifications": self.display_classifications
            }

            #remove all the items on the toolbar except the mode toggle
            actions_to_remove = self.toolbar.actions()[:-2]
            for action in actions_to_remove:
                self.toolbar.removeAction(action)
            display_func = display_functions.get(selected_item)
            if display_func:
                display_func(self.content_frame)

        except Exception as e:
            print(f"Error in tree_selection_event: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def display_dashboard(self, content_frame):
        label = QLabel("Welcome to your Dashboard!")
        content_frame.layout().addWidget(label)

    def display_categories(self, content_frame):
        display_categories(content_frame, self.toolbar)

    def display_accounts(self, content_frame):
        display_accounts(content_frame, self.toolbar)

    def display_credit_cards(self, content_frame):
        display_credit_cards(content_frame, self.toolbar)

    def display_transactions(self, content_frame):
        display_transactions(content_frame, self.toolbar)

    def display_currencies(self, content_frame):
        display_currencies(content_frame, self.toolbar)

    def display_classifications(self, content_frame):
        display_classifications(content_frame, self.toolbar)

    def add_category(self):
        self.open_input_dialog("Add Category", [("Category Name", "name")], self.database.insert_category)

    def add_currency(self):
        self.open_input_dialog("Add Currency", [("Currency Name", "name"), ("Exchange Rate", "rate", float)],
                               self.database.insert_currency)

    def add_account(self):
        self.open_input_dialog("Add Account",
                               [("Account Name", "name"), ("Category", "category", self.database.get_categories),
                                ("Default Currency", "currency", self.database.get_currencies)],
                               self.database.insert_account)

    def add_credit_card(self):
        def save_credit_card(data):
            credit_card_name = data['name']
            close_day = data['close_day']
            due_day = data['due_day']
            credit_limit = data['credit_limit']

            # Get the Liability category ID
            liability_cat_id = self.database.get_category_id("Liability")
            if liability_cat_id is None:
                QMessageBox.critical(self, "Error", "Liability category not found.")
                return

            # Create a new account record
            self.database.insert_account(credit_card_name, liability_cat_id)

            # Get the account ID
            account_id = self.database.get_account_id(credit_card_name)

            # Create a new credit card record
            self.database.insert_credit_card(account_id, credit_limit, close_day, due_day)

        self.open_input_dialog("Add Credit Card", [
            ("Credit Card Name", "name"),
            ("Close Day", "close_day", int),
            ("Due Day", "due_day", int),
            ("Credit Limit", "credit_limit", float)
        ], save_credit_card)

    def add_transaction(self):
        self.open_input_dialog("Add Transaction", [
            ("Description", "description"),
            ("Currency", "currency", self.database.get_currencies)
        ], self.save_transaction)

    def add_classification(self):
        self.open_input_dialog("Add Classification", [("Classification Name", "name")],
                               self.database.insert_classification)

    def save_transaction(self, data):
        description = data['description']
        currency_id = self.database.get_currency_id(data['currency'])
        transaction_id = self.database.insert_transaction(description, currency_id)
        self.add_transaction_lines(transaction_id)

    def add_transaction_lines(self, transaction_id):
        self.open_input_dialog("Add Transaction Line", [
            ("Account", "account", self.database.get_accounts),
            ("Debit", "debit", float, False),
            ("Credit", "credit", float, False),
            ("Date", "date")
        ], lambda data: self.save_transaction_line(transaction_id, data))

    def save_transaction_line(self, transaction_id, data):
        account_id = self.database.get_account_id(data['account'])
        debit = data['debit'] if 'debit' in data else None
        credit = data['credit'] if 'credit' in data else None
        date = data['date']
        self.database.insert_transaction_line(transaction_id, account_id, debit, credit, date)

    def show_about(self):
        QMessageBox.about(self, "About", "Personal Finance Manager\nVersion 1.0\nCopyright 2025")

    def open_input_dialog(self, title, fields, save_command):
        dialog = QWidget()
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)

        entries = {}
        for label, name, *options in fields:
            layout.addWidget(QLabel(label))
            if options:
                var_type = options[0]
                if var_type in [self.database.get_categories, self.database.get_currencies]:
                    combo = QComboBox(dialog)
                    combo.addItems(var_type())
                    layout.addWidget(combo)
                    entries[name] = combo
                else:
                    line_edit = QLineEdit(dialog)
                    line_edit.setValidator(var_type())
                    layout.addWidget(line_edit)
                    entries[name] = line_edit
            else:
                line_edit = QLineEdit(dialog)
                layout.addWidget(line_edit)
                entries[name] = line_edit

        save_button = QPushButton("Save", dialog)
        layout.addWidget(save_button)

        def save_and_close():
            try:
                data = {name: var.currentText() if isinstance(var, QComboBox) else var.text() for name, var in
                        entries.items()}
                save_command(data)
                dialog.close()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

        save_button.clicked.connect(save_and_close)
        dialog.show()
