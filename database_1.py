import sqlite3

class Database:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Accounts table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT
            );
        ''')

        # Categories table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT
            );
        ''')

        # Sub-categories table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sub_categories (
                id INTEGER PRIMARY KEY,
                category_name TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT
            );
        ''')

        # Transactions table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                description TEXT,
                total_debit REAL NOT NULL,
                total_credit REAL NOT NULL
            );
        ''')

        # Transaction lines table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_lines (
                id INTEGER PRIMARY KEY,
                transaction_id INTEGER NOT NULL,
                account_name TEXT NOT NULL,
                debit REAL,
                credit REAL,
                sub_category_name TEXT,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id)
            );
        ''')

        self.conn.commit()

    def insert_account(self, name, type, description):
        self.cursor.execute('INSERT INTO accounts (name, type, description) VALUES (?, ?, ?)', (name, type, description))
        self.conn.commit()

    def insert_category(self, name, description):
        self.cursor.execute('INSERT INTO categories (name, description) VALUES (?, ?)', (name, description))
        self.conn.commit()

    def insert_sub_category(self, category_name, name, description):
        self.cursor.execute('INSERT INTO sub_categories (category_name, name, description) VALUES (?, ?, ?)', (category_name, name, description))
        self.conn.commit()

    def insert_transaction(self, date, description, total_debit, total_credit):
        self.cursor.execute('INSERT INTO transactions (date, description, total_debit, total_credit) VALUES (?, ?, ?, ?)', (date, description, total_debit, total_credit))
        self.conn.commit()

    def insert_transaction_line(self, transaction_id, account_name, debit, credit, sub_category_name):
        self.cursor.execute('INSERT INTO transaction_lines (transaction_id, account_name, debit, credit, sub_category_name) VALUES (?, ?, ?, ?, ?)', (transaction_id, account_name, debit, credit, sub_category_name))
        self.conn.commit()

    def get_accounts(self):
        self.cursor.execute('SELECT * FROM accounts')
        return self.cursor.fetchall()

    def get_categories(self):
        self.cursor.execute('SELECT * FROM categories')
        return self.cursor.fetchall()

    def get_sub_categories(self):
        self.cursor.execute('SELECT * FROM sub_categories')
        return self.cursor.fetchall()

    def get_transactions(self):
        self.cursor.execute('SELECT * FROM transactions')
        return self.cursor.fetchall()

    def get_transaction_lines(self):
        self.cursor.execute('SELECT * FROM transaction_lines')
        return self.cursor.fetchall()

    def close_connection(self):
        self.conn.close()

## main.py (example usage)
from database import Database

db = Database('financial_database.db')

# Create account
db.insert_account('Checking', 'Asset', 'Primary checking account')

# Create category
db.insert_category('Expenses', 'Personal expenses')

# Create sub-category
db.insert_sub_category('Expenses', 'Rent', 'Monthly rent')

# Create transaction
db.insert_transaction('2024-01-01', 'Rent payment', 1000.0, 0.0)

# Create transaction line
db.insert_transaction_line(1, 'Checking', 1000.0, 0.0, 'Rent')

# Get accounts
accounts = db.get_accounts()
print(accounts)

# Close connection
db.close_connection()