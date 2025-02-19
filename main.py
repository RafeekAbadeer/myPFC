import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from database import Database
from data_display import display_data


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Personal Finance Manager")
        self.geometry("800x600")
        self.database = Database("finance.db")

        # Create a paned window
        self.paned_window = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Create a frame for the treeview
        self.tree_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.tree_frame, weight=1)

        # Create a treeview
        self.tree = ttk.Treeview(self.tree_frame, show="tree")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Create a frame for the content
        self.content_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.content_frame, weight=3)

        # Create the treeview structure
        self.tree["columns"] = ("",)
        self.tree.column("#0", width=200, minwidth=200, stretch=tk.NO)
        self.tree.column("", width=0, minwidth=0, stretch=tk.NO)
        self.tree.heading("#0", text="Tree", anchor=tk.W)

        # Add treeview items
        transactions_item = self.tree.insert("", "end", text="Transactions")
        settings_item = self.tree.insert("", "end", text="Settings")

        # Add sub-items
        self.tree.insert(settings_item, "end", text="Categories")
        self.tree.insert(settings_item, "end", text="Accounts")
        self.tree.insert(settings_item, "end", text="Credit Cards")
        self.tree.insert(transactions_item, "end", text="Transaction List")
        self.tree.insert(settings_item, "end", text="Currencies")

        # Remove expand button and display all items
        self.tree.item(transactions_item, open=True)
        self.tree.item(settings_item, open=True)

        # Alternate row colors
        for i, item in enumerate(self.tree.get_children()):
            if i % 2 == 0:
                self.tree.item(item, tags=("even",))
            else:
                self.tree.item(item, tags=("odd",))

        # Configure tags for alternating row colors
        self.tree.tag_configure("even", background="#f0f0f0")
        self.tree.tag_configure("odd", background="#ffffff")

        # Configure the paned window to have a 20/80 ratio
        self.paned_window.pane(0, weight=1)
        self.paned_window.pane(1, weight=100)

        # Bind the treeview selection event
        self.tree.bind("<<TreeviewSelect>>", self.tree_selection_event)

        self.create_menu()

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        add_menu = tk.Menu(menubar, tearoff=0)
        add_menu.add_command(label="Category", command=self.add_category)
        add_menu.add_command(label="Currency", command=self.add_currency)
        add_menu.add_command(label="Account", command=self.add_account)
        add_menu.add_command(label="Credit Card", command=self.add_credit_card)
        add_menu.add_command(label="Transaction", command=self.add_transaction)
        menubar.add_cascade(label="Add", menu=add_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        # Add edit commands here
        menubar.add_cascade(label="Edit", menu=edit_menu)

        about_menu = tk.Menu(menubar, tearoff=0)
        about_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="About", menu=about_menu)

    def tree_selection_event(self, event):
        selected_item = self.tree.selection()[0]
        selected_text = self.tree.item(selected_item, "text")

        # Clear the content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Display the corresponding content
        if selected_text == "Categories":
            self.display_categories(self.content_frame)
        elif selected_text == "Accounts":
            self.display_accounts(self.content_frame)
        elif selected_text == "Credit Cards":
            self.display_credit_cards(self.content_frame)
        elif selected_text == "Transaction List":
            self.display_transaction_list(self.content_frame)
        elif selected_text == "Currencies":
            self.display_currencies(self.content_frame)

    def display_categories(self, content_frame):
        display_data("cat", content_frame)

    def display_accounts(self, content_frame):
        display_data("accounts", content_frame)

    def display_credit_cards(self, content_frame):
        display_data("ccards", content_frame)

    def display_transaction_list(self, content_frame):
        display_data("transactions", content_frame)

    def display_currencies(self, content_frame):
        display_data("currency", content_frame)

    def add_category(self):
        self.open_input_window("Add Category", [("Category Name", "name")], self.database.insert_category)

    def add_currency(self):
        self.open_input_window("Add Currency", [("Currency Name", "name"), ("Exchange Rate", "rate", float)],
                               self.database.insert_currency)

    def add_account(self):
        self.open_input_window("Add Account",
                               [("Account Name", "name"), ("Category", "category", self.database.get_categories),
                                ("Default Currency", "currency", self.database.get_currencies)],
                               self.database.insert_account)

    def add_credit_card(self):
        def save_credit_card(data):
            credit_card_name = data['Credit Card Name']
            close_day = data['Close Day']
            due_day = data['Due Day']
            credit_limit = data['Credit Limit']

            # Get the Liability category ID
            liability_cat_id = self.database.get_category_id("Liability")
            if liability_cat_id is None:
                messagebox.showerror("Error", "Liability category not found.")
                return

            # Create a new account record
            self.database.insert_account(credit_card_name, liability_cat_id)

            # Get the account ID
            account_id = self.database.get_account_id(credit_card_name)

            # Create a new credit card record
            self.database.insert_credit_card(account_id, credit_limit, close_day, due_day)

        self.open_input_window("Add Credit Card", [("Credit Card Name", "name"), ("Close Day", "close_day", int),
                                                   ("Due Day", "due_day", int),
                                                   ("Credit Limit", "credit_limit", float)], save_credit_card)


    def add_transaction(self):
        self.open_input_window("Add Transaction", [
            ("Description", "description"),
            ("Currency", "currency", self.database.get_currencies)
        ], self.save_transaction)

    def save_transaction(self, data):
        description = data['Description']
        currency_id = self.database.get_currency_id(data['Currency'])
        transaction_id = self.database.insert_transaction(description, currency_id)
        self.add_transaction_lines(transaction_id)

    def add_transaction_lines(self, transaction_id):
        self.open_input_window("Add Transaction Line", [
            ("Account", "account", self.database.get_accounts),
            ("Debit", "debit", float, False),
            ("Credit", "credit", float, False),
            ("Date", "date")
        ], lambda data: self.save_transaction_line(transaction_id, data))

    def save_transaction_line(self, transaction_id, data):
        account_id = self.database.get_account_id(data['Account'])
        debit = data['Debit'] if 'Debit' in data else None
        credit = data['Credit'] if 'Credit' in data else None
        date = data['Date']
        self.database.insert_transaction_line(transaction_id, account_id, debit, credit, date)

    def show_about(self):
        messagebox.showinfo("About", "Personal Finance Manager\nVersion 1.0\nCopyright 2023")

    def open_input_window(self, title, fields, save_command):
        window = tk.Toplevel(self)
        window.title(title)

        entries = {}
        for i, (label, name, *options) in enumerate(fields):
            tk.Label(window, text=label).grid(row=i, column=0)
            if options:
                var_type = options[0]
                if var_type == self.database.get_categories or var_type == self.database.get_currencies:
                    var = tk.StringVar(window)
                    var.set(var_type()[0])
                    menu = tk.OptionMenu(window, var, *var_type())
                    menu.grid(row=i, column=1)
                    entries[name] = var
                else:
                    entry = tk.Entry(window)
                    if len(options) > 1 and not options[1]:  # Optional field
                        entry.insert(0, "")
                    else:
                        entry.insert(0, "")
                    entry.grid(row=i, column=1)
                    entries[name] = (entry, var_type)
            else:
                entry = tk.Entry(window)
                entry.insert(0, "")
                entry.grid(row=i, column=1)
                entries[name] = (entry, str)

        def save_and_close():
            try:
                data = {name: (var.get() if isinstance(var, tk.StringVar) else var[1](var[0].get())) for name, var in entries.items()}
                save_command(data)
                window.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(window, text="Save", command=save_and_close).grid(row=len(fields), column=0, columnspan=2)

if __name__ == "__main__":
    app = Application()
    app.mainloop()
