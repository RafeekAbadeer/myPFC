import sqlite3

class Database:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cat (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS currency (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                exchange_rate REAL NOT NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                cat_id INTEGER NOT NULL,
                default_currency_id INTEGER,
                FOREIGN KEY (cat_id) REFERENCES cat (id),
                FOREIGN KEY (default_currency_id) REFERENCES currency (id) ON DELETE SET NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ccards(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                credit_limit REAL,
                close_day INTEGER,
                due_day INTEGER,
                balance REAL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                description TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_lines (
                id INTEGER PRIMARY KEY,
                transaction_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                debit REAL,
                credit REAL,
                amount REAL NOT NULL,
                currency_id INTEGER NOT NULL,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id),
                FOREIGN KEY (account_id) REFERENCES accounts (id),
                FOREIGN KEY (currency_id) REFERENCES currency (id)
            )
        ''')

        self.conn.commit()

    def close_connection(self):
        self.conn.close()


    def insert_category(self, name):
        self.cursor.execute("INSERT INTO cat (name) VALUES (?)", (name,))
        self.conn.commit()
        return self.cursor.lastrowid

    def insert_currency(self, name, exchange_rate):
        self.cursor.execute("INSERT INTO currency (name, exchange_rate) VALUES (?, ?)", (name, exchange_rate))
        self.conn.commit()
        return self.cursor.lastrowid

    def insert_account(self, name, cat_id, default_currency_id=None):
        self.cursor.execute("INSERT INTO accounts (name, cat_id, default_currency_id) VALUES (?, ?, ?)", (name, cat_id, default_currency_id))
        self.conn.commit()
        return self.cursor.lastrowid

    def insert_credit_card(self, account_id, credit_limit, close_day, due_day, balance=0):
        self.cursor.execute("INSERT INTO ccards (account_id, credit_limit, close_day, due_day, balance) VALUES (?, ?, ?, ?, ?)", (account_id, credit_limit, close_day, due_day, balance))
        self.conn.commit()
        return self.cursor.lastrowid

    def insert_transaction(self, date, description=None):
        self.cursor.execute("INSERT INTO transactions (date, description) VALUES (?, ?)", (date, description))
        self.conn.commit()
        return self.cursor.lastrowid

    def insert_transaction_line(self, transaction_id, account_id, amount, debit=None, credit=None, currency_id=None):
        if debit is None and credit is None:
            raise ValueError("Either debit or credit must be specified")
        self.cursor.execute("INSERT INTO transaction_lines (transaction_id, account_id, debit, credit, amount, currency_id) VALUES (?, ?, ?, ?, ?, ?)", (transaction_id, account_id, debit, credit, amount, currency_id))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_categories(self):
        self.cursor.execute("SELECT name FROM cat")
        return [row[0] for row in self.cursor.fetchall()]

    def get_category_id(self, name):
        self.cursor.execute("SELECT id FROM cat WHERE name = ?", (name,))
        return self.cursor.fetchone()[0]

    def get_currencies(self):
        self.cursor.execute("SELECT name FROM currency")
        return [row[0] for row in self.cursor.fetchall()]

    def get_currency_id(self, name):
        self.cursor.execute("SELECT id FROM currency WHERE name = ?", (name,))
        return self.cursor.fetchone()[0]

    def get_accounts(self):
        self.cursor.execute("SELECT name FROM accounts")
        return [row[0] for row in self.cursor.fetchall()]

    def get_account_id(self, name):
        self.cursor.execute("SELECT id FROM accounts WHERE name = ?", (name,))
        return self.cursor.fetchone()[0]

