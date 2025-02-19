import sqlite3

class Database:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS currency (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                exchange_rate REAL NOT NULL,
                UNIQUE(name)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cat_id INTEGER NOT NULL,
                default_currency_id INTEGER,
                FOREIGN KEY (cat_id) REFERENCES cat (id),
                FOREIGN KEY (default_currency_id) REFERENCES currency (id) ON DELETE SET NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ccards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                credit_limit REAL NOT NULL,
                close_day INTEGER NOT NULL,
                due_day INTEGER NOT NULL,
                balance REAL NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT,
                currency_id INTEGER NOT NULL,
                FOREIGN KEY (currency_id) REFERENCES currency (id)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                debit REAL,
                credit REAL,
                date DATE NOT NULL,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id),
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        ''')

        # Create indexes
        self.cursor.execute('''CREATE INDEX IF NOT EXISTS idx_ccards_account_id ON ccards (account_id)''')
        self.cursor.execute(
            '''CREATE INDEX IF NOT EXISTS idx_transaction_lines_account_id ON transaction_lines (account_id)''')
        self.cursor.execute(
            '''CREATE INDEX IF NOT EXISTS idx_transaction_lines_transaction_id ON transaction_lines (transaction_id)''')

        # Create triggers
        self.cursor.execute('''CREATE TRIGGER IF NOT EXISTS ensure_debit_credit_positive
                               BEFORE INSERT ON transaction_lines
                               FOR EACH ROW
                               BEGIN
                                   SELECT CASE
                                       WHEN (NEW.debit + NEW.credit) <= 0 THEN
                                           RAISE(ABORT, 'Debit + Credit must be greater than 0')
                                   END;
                               END;''')

        self.cursor.execute('''CREATE TRIGGER IF NOT EXISTS ensure_debit_credit_positive_update
                               BEFORE UPDATE ON transaction_lines
                               FOR EACH ROW
                               BEGIN
                                   SELECT CASE
                                       WHEN (NEW.debit + NEW.credit) <= 0 THEN
                                           RAISE(ABORT, 'Debit + Credit must be greater than 0')
                                   END;
                               END;''')

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


    def insert_transaction(self, description, currency_id):
        self.cursor.execute("INSERT INTO transactions (description, currency_id) VALUES (?, ?)",
                            (description, currency_id))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_transactions(self):
        self.cursor.execute("SELECT * FROM transactions")
        return self.cursor.fetchall()


    def insert_transaction_line(self, transaction_id, account_id, debit=None, credit=None, date=None):
        if debit is None and credit is None:
            raise ValueError("Either debit or credit must be specified")
        self.cursor.execute(
            "INSERT INTO transaction_lines (transaction_id, account_id, debit, credit, date) VALUES (?, ?, ?, ?, ?)",
            (transaction_id, account_id, debit, credit, date))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_transaction_lines(self, transaction_id):
        self.cursor.execute('''
            SELECT tl.id, tl.transaction_id, tl.account_id, tl.debit, tl.credit, tl.date, t.currency_id
            FROM transaction_lines tl
            JOIN transactions t ON tl.transaction_id = t.id
            WHERE tl.transaction_id = ?
        ''', (transaction_id,))
        return self.cursor.fetchall()

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

# Initialize the database
db = Database('finance.db')

