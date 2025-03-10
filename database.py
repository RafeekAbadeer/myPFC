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
                classification_id INTEGER,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id),
                FOREIGN KEY (account_id) REFERENCES accounts (id),
                FOREIGN KEY (classification_id) REFERENCES classifications (id)
            )
        ''')

        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    UNIQUE(name)
                )
            ''')

        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    classification_id INTEGER NOT NULL,
                    FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
                    FOREIGN KEY (classification_id) REFERENCES classifications (id) ON DELETE CASCADE,
                    UNIQUE(account_id, classification_id)
                )
            ''')

        # Create indexes
        self.cursor.execute('''CREATE INDEX IF NOT EXISTS idx_ccards_account_id ON ccards (account_id)''')
        self.cursor.execute(
            '''CREATE INDEX IF NOT EXISTS idx_transaction_lines_account_id ON transaction_lines (account_id)''')
        self.cursor.execute(
            '''CREATE INDEX IF NOT EXISTS idx_transaction_lines_transaction_id ON transaction_lines (transaction_id)''')
        self.cursor.execute('''CREATE INDEX IF NOT EXISTS idx_transaction_lines_classification_id 
                               ON transaction_lines (classification_id)''')

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

    def insert_credit_card(self, account_id, credit_limit, close_day, due_day):
        self.cursor.execute("INSERT INTO ccards (account_id, credit_limit, close_day, due_day) VALUES (?, ?, ?, ?)", (account_id, credit_limit, close_day, due_day))
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

    # Add these methods to the Database class

    def update_category(self, id, name):
        self.cursor.execute("UPDATE cat SET name = ? WHERE id = ?", (name, id))
        self.conn.commit()

    def delete_category(self, id):
        self.cursor.execute("DELETE FROM cat WHERE id = ?", (id,))
        self.conn.commit()

    def update_currency(self, id, name, exchange_rate):
        self.cursor.execute("UPDATE currency SET name = ?, exchange_rate = ? WHERE id = ?",
                            (name, exchange_rate, id))
        self.conn.commit()

    def delete_currency(self, id):
        self.cursor.execute("DELETE FROM currency WHERE id = ?", (id,))
        self.conn.commit()

    def update_account(self, id, name, cat_id, default_currency_id=None):
        self.cursor.execute("UPDATE accounts SET name = ?, cat_id = ?, default_currency_id = ? WHERE id = ?",
                            (name, cat_id, default_currency_id, id))
        self.conn.commit()

    def delete_account(self, id):
        self.cursor.execute("DELETE FROM accounts WHERE id = ?", (id,))
        self.conn.commit()

    def update_credit_card(self, account_id, credit_limit, close_day, due_day):
        self.cursor.execute("UPDATE ccards SET credit_limit = ?, close_day = ?, due_day = ? WHERE account_id = ?",
                            (credit_limit, close_day, due_day, account_id))
        self.conn.commit()

    def delete_credit_card(self, account_id):
        self.cursor.execute("DELETE FROM ccards WHERE account_id = ?", (account_id,))
        self.conn.commit()

    def get_credit_card_by_account_id(self, account_id):
        self.cursor.execute("SELECT * FROM ccards WHERE account_id = ?", (account_id,))
        return self.cursor.fetchone()

    # Add to database.py
    def get_credit_card_details(self, account_id):
        self.cursor.execute("""
            SELECT id, credit_limit, close_day, due_day
            FROM ccards
            WHERE account_id = ?
        """, (account_id,))
        result = self.cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'credit_limit': result[1],
                'close_day': result[2],
                'due_day': result[3]
            }
        return None

    def is_credit_card(self, account_id):
        self.cursor.execute("SELECT COUNT(*) FROM ccards WHERE account_id = ?", (account_id,))
        return self.cursor.fetchone()[0] > 0

    def get_all_classifications(self):
        self.cursor.execute("SELECT id, name FROM classifications")
        return self.cursor.fetchall()

    def get_classification_by_id(self, id):
        self.cursor.execute("SELECT * FROM classifications WHERE id = ?", (id,))
        return self.cursor.fetchone()

    def get_classification_by_name(self, name):
        self.cursor.execute("SELECT * FROM classifications WHERE name = ?", (name,))
        return self.cursor.fetchone()

    def update_classification(self, id, name):
        self.cursor.execute("UPDATE classifications SET name = ? WHERE id = ?", (name, id))
        self.conn.commit()

    def delete_classification(self, id):
        self.cursor.execute("DELETE FROM classifications WHERE id = ?", (id,))
        self.conn.commit()

    def get_account_by_id(self, id):
        self.cursor.execute("SELECT * FROM accounts WHERE id = ?", (id,))
        return self.cursor.fetchone()

    def get_category_by_id(self, id):
        self.cursor.execute("SELECT * FROM cat WHERE id = ?", (id,))
        return self.cursor.fetchone()

    def get_currency_by_id(self, id):
        self.cursor.execute("SELECT * FROM currency WHERE id = ?", (id,))
        return self.cursor.fetchone()

    def get_category_by_name(self, name):
        self.cursor.execute("SELECT * FROM cat WHERE name = ?", (name,))
        return self.cursor.fetchone()

    def get_all_categories(self):
        self.cursor.execute("SELECT id, name FROM cat")
        return self.cursor.fetchall()

    def get_all_currencies(self):
        self.cursor.execute("SELECT id, name, exchange_rate FROM currency")
        return self.cursor.fetchall()

    def get_all_accounts(self):
        self.cursor.execute("""
            SELECT a.id, a.name, c.name as category, cu.name as currency
            FROM accounts a
            JOIN cat c ON a.cat_id = c.id
            LEFT JOIN currency cu ON a.default_currency_id = cu.id
        """)
        return self.cursor.fetchall()

    def get_all_credit_cards(self):
        self.cursor.execute("""
            SELECT cc.id, a.name, cc.credit_limit, cc.close_day, cc.due_day, cu.name as currency
            FROM ccards cc
            JOIN accounts a ON cc.account_id = a.id
            LEFT JOIN currency cu ON a.default_currency_id = cu.id
        """)
        return self.cursor.fetchall()

    def get_credit_card_by_id(self, id):
        self.cursor.execute("""
            SELECT cc.id, cc.account_id, cc.credit_limit, cc.close_day, cc.due_day
            FROM ccards cc
            WHERE cc.id = ?
        """, (id,))
        result = self.cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'account_id': result[1],
                'credit_limit': result[2],
                'close_day': result[3],
                'due_day': result[4]
            }
        return None

    def get_account_details(self, account_id):
        self.cursor.execute("""
            SELECT a.id, a.name, a.cat_id, a.default_currency_id, c.name, cu.name
            FROM accounts a
            JOIN cat c ON a.cat_id = c.id
            LEFT JOIN currency cu ON a.default_currency_id = cu.id
            WHERE a.id = ?
        """, (account_id,))
        result = self.cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'name': result[1],
                'category_id': result[2],
                'currency_id': result[3],
                'category_name': result[4],
                'currency_name': result[5]
            }
        return None

    def account_has_transactions(self, account_id):
        self.cursor.execute("""
            SELECT COUNT(*) FROM transaction_lines
            WHERE account_id = ?
        """, (account_id,))
        count = self.cursor.fetchone()[0]
        return count > 0

    def get_credit_card_statement(self, account_id, month, year):
        # Format date ranges for the given month
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-31" if month != 2 else f"{year}-{month:02d}-28"

        self.cursor.execute("""
            SELECT tl.date, t.description, tl.debit - tl.credit as amount
            FROM transaction_lines tl
            JOIN transactions t ON tl.transaction_id = t.id
            WHERE tl.account_id = ? AND tl.date BETWEEN ? AND ?
            ORDER BY tl.date
        """, (account_id, start_date, end_date))

        results = []
        for row in self.cursor.fetchall():
            results.append({
                'date': row[0],
                'description': row[1],
                'amount': row[2]
            })
        return results

    def insert_classification(self, name):
        self.cursor.execute("INSERT INTO classifications (name) VALUES (?)", (name,))
        self.conn.commit()
        return self.cursor.lastrowid

    def link_account_classification(self, account_id, classification_id):
        self.cursor.execute(
            "INSERT INTO account_classifications (account_id, classification_id) VALUES (?, ?)",
            (account_id, classification_id)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_classifications_for_account(self, account_id):
        self.cursor.execute("""
            SELECT c.id, c.name
            FROM classifications c
            JOIN account_classifications ac ON c.id = ac.classification_id
            WHERE ac.account_id = ?
            ORDER BY c.name
        """, (account_id,))
        return self.cursor.fetchall()

    def update_transaction_line_classification(self, transaction_line_id, classification_id):
        self.cursor.execute(
            "UPDATE transaction_lines SET classification_id = ? WHERE id = ?",
            (classification_id, transaction_line_id)
        )
        self.conn.commit()

    def unlink_account_classification(self, account_id, classification_id):
        self.cursor.execute(
            "DELETE FROM account_classifications WHERE account_id = ? AND classification_id = ?",
            (account_id, classification_id)
        )
        self.conn.commit()

# Initialize the database
db = Database('finance.db')

