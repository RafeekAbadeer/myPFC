import tkinter as tk
from tkinter import ttk
import sqlite3
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

        # Configure the treeview to display items in a flat list
        #self.tree.column("#0", width=200, minwidth=200, stretch=tk.NO)
        #self.tree.heading("#0", text="Tree", anchor=tk.W)

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

    def display_categories(content_frame, event=None):
        display_data("categories", content_frame)

    def display_accounts(content_frame, event=None):
        display_data("accounts", content_frame)

    def display_credit_cards(content_frame, event=None):
        display_data("credit_cards", content_frame)

    def display_transaction_list(content_frame, event=None):
        display_data("transactions", content_frame)

    def display_currencies(content_frame, event=None):
        display_data("currencies", content_frame)

    def add_category(self):
        # Create a new window to input category data
        category_window = tk.Toplevel(self)
        category_window.title("Add Category")

        tk.Label(category_window, text="Category Name:").grid(row=0, column=0)
        category_name = tk.Entry(category_window)
        category_name.grid(row=0, column=1)

        def save_category():
            name = category_name.get()
            self.database.insert_category(name)
            category_window.destroy()

        tk.Button(category_window, text="Save", command=save_category).grid(row=1, column=0, columnspan=2)

    def add_currency(self):
        # Create a new window to input currency data
        currency_window = tk.Toplevel(self)
        currency_window.title("Add Currency")

        tk.Label(currency_window, text="Currency Name:").grid(row=0, column=0)
        currency_name = tk.Entry(currency_window)
        currency_name.grid(row=0, column=1)

        tk.Label(currency_window, text="Exchange Rate:").grid(row=1, column=0)
        exchange_rate = tk.Entry(currency_window)
        exchange_rate.grid(row=1, column=1)

        def save_currency():
            name = currency_name.get()
            rate = float(exchange_rate.get())
            self.database.insert_currency(name, rate)
            currency_window.destroy()

        tk.Button(currency_window, text="Save", command=save_currency).grid(row=2, column=0, columnspan=2)

    def add_account(self):
        # Create a new window to input account data
        account_window = tk.Toplevel(self)
        account_window.title("Add Account")

        tk.Label(account_window, text="Account Name:").grid(row=0, column=0)
        account_name = tk.Entry(account_window)
        account_name.grid(row=0, column=1)

        tk.Label(account_window, text="Category:").grid(row=1, column=0)
        categories = self.database.get_categories()
        category_var = tk.StringVar(account_window)
        category_var.set(categories[0])
        category_menu = tk.OptionMenu(account_window, category_var, *categories)
        category_menu.grid(row=1, column=1)

        tk.Label(account_window, text="Default Currency:").grid(row=2, column=0)
        currencies = self.database.get_currencies()
        currency_var = tk.StringVar(account_window)
        currency_var.set(currencies[0])
        currency_menu = tk.OptionMenu(account_window, currency_var, *currencies, "None")
        currency_menu.grid(row=2, column=1)

        def save_account():
            name = account_name.get()
            cat_id = self.database.get_category_id(category_var.get())
            currency_id = self.database.get_currency_id(currency_var.get()) if currency_var.get() != "None" else None
            self.database.insert_account(name, cat_id, currency_id)
            account_window.destroy()

        tk.Button(account_window, text="Save", command=save_account).grid(row=3, column=0, columnspan=2)

    def add_credit_card(self):

        # Create a new window to input credit card data
        credit_card_window = tk.Toplevel(self)
        credit_card_window.title("Add Credit Card")

        # Create entry fields for credit card data
        tk.Label(credit_card_window, text="Credit Card Name:").grid(row=0, column=0)
        credit_card_name_entry = tk.Entry(credit_card_window)
        credit_card_name_entry.grid(row=0, column=1)

        tk.Label(credit_card_window, text="Close Day:").grid(row=1, column=0)
        close_day_entry = tk.Entry(credit_card_window)
        close_day_entry.grid(row=1, column=1)

        tk.Label(credit_card_window, text="Due Day:").grid(row=2, column=0)
        due_day_entry = tk.Entry(credit_card_window)
        due_day_entry.grid(row=2, column=1)

        tk.Label(credit_card_window, text="Credit Limit:").grid(row=3, column=0)
        credit_limit_entry = tk.Entry(credit_card_window)
        credit_limit_entry.grid(row=3, column=1)

        def save_credit_card():
            credit_card_name = credit_card_name_entry.get()
            close_day = close_day_entry.get()
            due_day = due_day_entry.get()
            credit_limit = credit_limit_entry.get()

            # Get the Liability category ID
            liability_cat_id = self.database.get_category_id("Liability")
            if liability_cat_id is None:
                error_window = tk.Toplevel(self)
                error_window.title("Error")
                tk.Label(error_window, text="Liability category is not found").pack()
                return

            # Create a new account record
            self.database.insert_account(credit_card_name, liability_cat_id)

            # Get the account ID
            account_id = self.database.get_account_id(credit_card_name)

            # Create a new credit card record
            self.database.insert_credit_card(account_id, close_day, due_day, credit_limit)
            credit_card_window.destroy()

        tk.Button(credit_card_window, text="Save", command=save_credit_card).grid(row=4, column=0, columnspan=2)

    def add_transaction(self):
        # Create a new window to input transaction data
        transaction_window = tk.Toplevel(self)
        transaction_window.title("Add Transaction")

        tk.Label(transaction_window, text="Date:").grid(row=0, column=0)
        date_entry = tk.Entry(transaction_window)
        date_entry.grid(row=0, column=1)

        tk.Label(transaction_window, text="Description:").grid(row=1, column=0)
        description_entry = tk.Entry(transaction_window)
        description_entry.grid(row=1, column=1)

        def save_transaction():
            date = date_entry.get()
            description = description_entry.get()
            transaction_id = self.database.insert_transaction(date, description)
            transaction_window.destroy()
            self.add_transaction_lines(transaction_id)

        tk.Button(transaction_window, text="Save", command=save_transaction).grid(row=2, column=0, columnspan=2)

    def add_transaction_lines(self, transaction_id):
        # Create a new window to input transaction lines data
        transaction_lines_window = tk.Toplevel(self)
        transaction_lines_window.title("Add Transaction Lines")

        tk.Label(transaction_lines_window, text="Account:").grid(row=0, column=0)
        accounts = self.database.get_accounts()
        account_var = tk.StringVar(transaction_lines_window)
        account_var.set(accounts[0])
        account_menu = tk.OptionMenu(transaction_lines_window, account_var, *accounts)
        account_menu.grid(row=0, column=1)

        tk.Label(transaction_lines_window, text="Debit:").grid(row=1, column=0)
        debit_entry = tk.Entry(transaction_lines_window)
        debit_entry.grid(row=1, column=1)

        tk.Label(transaction_lines_window, text="Credit:").grid(row=2, column=0)
        credit_entry = tk.Entry(transaction_lines_window)
        credit_entry.grid(row=2, column=1)

        tk.Label(transaction_lines_window, text="Amount:").grid(row=3, column=0)
        amount_entry = tk.Entry(transaction_lines_window)
        amount_entry.grid(row=3, column=1)

        tk.Label(transaction_lines_window, text="Currency:").grid(row=4, column=0)
        currencies = self.database.get_currencies()
        currency_var = tk.StringVar(transaction_lines_window)
        currency_var.set(currencies[0])
        currency_menu = tk.OptionMenu(transaction_lines_window, currency_var, *currencies)
        currency_menu.grid(row=4, column=1)

        def save_transaction_line():
            account_id = self.database.get_account_id(account_var.get())
            debit = float(debit_entry.get()) if debit_entry.get() else 0
            credit = float(credit_entry.get()) if credit_entry.get() else 0
            amount = float(amount_entry.get())
            currency_id = self.database.get_currency_id(currency_var.get())
            self.database.insert_transaction_line(transaction_id, account_id, debit, credit, amount, currency_id)
            transaction_lines_window.destroy()
        tk.Button(transaction_lines_window, text="Save", command=save_transaction_line).grid(row=5, column=0, columnspan=2)

    def show_about(self):
        about_window = tk.Toplevel(self)
        about_window.title("About")
        tk.Label(about_window, text="Personal Finance Manager").pack()
        tk.Label(about_window, text="Version 1.0").pack()
        tk.Label(about_window, text="Copyright 2023").pack()

if __name__ == "__main__":
    app = Application()
    app.mainloop()
