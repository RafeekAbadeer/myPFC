import sqlite3

class Database:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name, isolation_level="DEFERRED")
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
                nature TEXT CHECK (nature IN ('debit', 'credit', 'both')) DEFAULT 'both',
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

        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS orphan_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reference TEXT,
                    import_date TEXT,
                    status TEXT CHECK (status IN ('new', 'processed', 'ignored'))
                )
            ''')

        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS orphan_transaction_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    orphan_transaction_id INTEGER,
                    description TEXT,
                    account_id INTEGER,
                    debit REAL,
                    credit REAL,
                    status TEXT CHECK (status IN ('new', 'consumed', 'ignored')) DEFAULT 'new',
                    transaction_id INTEGER,  -- Reference to the transaction that consumed this line (NULL if not consumed)
                    FOREIGN KEY (orphan_transaction_id) REFERENCES orphan_transactions(id) ON DELETE CASCADE,
                    FOREIGN KEY (account_id) REFERENCES accounts(id),
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
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
        # Add these indexes
        self.cursor.execute('''CREATE INDEX IF NOT EXISTS idx_transaction_lines_date ON transaction_lines (date)''')
        self.cursor.execute('''CREATE INDEX IF NOT EXISTS idx_transaction_lines_transaction_date 
                               ON transaction_lines (transaction_id, date)''')

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
        #self.conn.commit()
        return self.cursor.lastrowid

    def get_transactions(self):
        self.cursor.execute("SELECT * FROM transactions")
        return self.cursor.fetchall()

    def get_transaction_lines(self, transaction_id):
        self.cursor.execute('''
            SELECT tl.id, tl.transaction_id, tl.account_id, tl.debit, tl.credit, tl.date, t.currency_id, tl.classification_id
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

    def update_transaction(self, id, description, currency_id):
        self.cursor.execute("UPDATE transactions SET description = ?, currency_id = ? WHERE id = ?",
                            (description, currency_id, id))
        #self.conn.commit()

    def delete_transaction(self, id):
        # First delete all associated transaction lines (using foreign key constraints)
        self.cursor.execute("DELETE FROM transaction_lines WHERE transaction_id = ?", (id,))
        # Then delete the transaction itself
        self.cursor.execute("DELETE FROM transactions WHERE id = ?", (id,))
        self.conn.commit()

    def insert_transaction_line(self, transaction_id, account_id, debit=None, credit=None, date=None,
                                classification_id=None):
        if debit is None and credit is None:
            raise ValueError("Either debit or credit must be specified")
        self.cursor.execute(
            "INSERT INTO transaction_lines (transaction_id, account_id, debit, credit, date, classification_id) VALUES (?, ?, ?, ?, ?, ?)",
            (transaction_id, account_id, debit, credit, date, classification_id))
        #self.conn.commit()
        return self.cursor.lastrowid

    def get_transaction_line(self, id):
        self.cursor.execute("""
            SELECT tl.id, tl.transaction_id, tl.account_id, tl.debit, tl.credit, tl.date, tl.classification_id,
                   a.name as account_name, t.currency_id
            FROM transaction_lines tl
            JOIN accounts a ON tl.account_id = a.id
            JOIN transactions t ON tl.transaction_id = t.id
            WHERE tl.id = ?
        """, (id,))

        result = self.cursor.fetchone()
        if result:
            # Determine if this is a debit or credit line
            line_type = "Debit" if result[3] else "Credit"

            return {
                'id': result[0],
                'transaction_id': result[1],
                'account_id': result[2],
                'debit': result[3],
                'credit': result[4],
                'date': result[5],
                'classification_id': result[6],
                'account_name': result[7],
                'currency_id': result[8],
                'type': line_type
            }
        return None

    def update_transaction_line(self, id, account_id, debit=None, credit=None, date=None, classification_id=None):
        self.cursor.execute("""
            UPDATE transaction_lines 
            SET account_id = ?, debit = ?, credit = ?, date = ?, classification_id = ?
            WHERE id = ?
        """, (account_id, debit, credit, date, classification_id, id))
        #self.conn.commit()

    def delete_transaction_line(self, id):
        self.cursor.execute("DELETE FROM transaction_lines WHERE id = ?", (id,))
        #self.conn.commit()

    def begin_transaction(self):
        """Begin a database transaction"""
        #conn = db.get_connection()
        self.conn.execute("BEGIN TRANSACTION")

    def commit_transaction(self):
        """Commit a database transaction"""
        #conn = db.get_connection()
        self.conn.execute("COMMIT")

    def rollback_transaction(self):
        """Rollback a database transaction"""
        #conn = db.get_connection()
        self.conn.execute("ROLLBACK")

    def get_transaction_count(self, filter_params=None):
        """Get the total number of transactions matching the filter"""
        # Build the query dynamically based on filters
        base_query = """
            SELECT COUNT(DISTINCT t.id)
            FROM transactions t
            JOIN transaction_lines tl ON t.id = tl.transaction_id
        """

        where_clauses = []
        params = []

        # Apply filters if provided
        if filter_params:
            if 'date_from' in filter_params:
                where_clauses.append("tl.date >= ?")
                params.append(filter_params['date_from'])

            if 'date_to' in filter_params:
                where_clauses.append("tl.date <= ?")
                params.append(filter_params['date_to'])

            if 'account_id' in filter_params:
                where_clauses.append("tl.account_id = ?")
                params.append(filter_params['account_id'])

            if 'description' in filter_params:
                where_clauses.append("t.description LIKE ?")
                params.append(f"%{filter_params['description']}%")

        # Add WHERE clause if we have conditions
        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        # Execute the query
        self.cursor.execute(base_query, params)
        count = self.cursor.fetchone()[0]

        # Apply amount filters if specified (needs to be done post-query)
        if filter_params and ('min_amount' in filter_params or 'max_amount' in filter_params):
            # For amount filters, we need to get all transactions and filter in Python
            # This is because the amount is a calculated value from the lines
            transactions = []
            filtered_count = 0

            # Get all transaction IDs that match the other filters
            if not where_clauses:
                self.cursor.execute(
                    "SELECT DISTINCT t.id FROM transactions t JOIN transaction_lines tl ON t.id = tl.transaction_id")
            else:
                self.cursor.execute(
                    "SELECT DISTINCT t.id FROM transactions t JOIN transaction_lines tl ON t.id = tl.transaction_id WHERE " +
                    " AND ".join(where_clauses),
                    params
                )

            transaction_ids = [row[0] for row in self.cursor.fetchall()]

            # For each transaction, calculate the total and apply amount filters
            for transaction_id in transaction_ids:
                self.cursor.execute(
                    "SELECT SUM(IFNULL(tl.debit, 0)) FROM transaction_lines tl WHERE tl.transaction_id = ?",
                    (transaction_id,)
                )
                total_amount = self.cursor.fetchone()[0] or 0

                # Apply amount filters
                include = True
                if 'min_amount' in filter_params and total_amount < filter_params['min_amount']:
                    include = False

                if 'max_amount' in filter_params and total_amount > filter_params['max_amount']:
                    include = False

                if include:
                    filtered_count += 1

            return filtered_count

        return count

    def get_transaction_by_id(self, id):
        """Get a transaction by ID"""
        self.cursor.execute("""
            SELECT t.id, t.description, t.currency_id, c.name as currency_name
            FROM transactions t
            JOIN currency c ON t.currency_id = c.id
            WHERE t.id = ?
        """, (id,))
        result = self.cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'description': result[1],
                'currency_id': result[2],
                'currency_name': result[3]
            }
        return None

    def get_transaction_lines_by_type(self, transaction_id, is_debit=True):
        """Get transaction lines of a specific type (debit or credit)"""
        query = """
            SELECT tl.id, tl.account_id, a.name as account_name, 
                   tl.debit, tl.credit, tl.date, tl.classification_id, 
                   c.name as classification_name
            FROM transaction_lines tl
            JOIN accounts a ON tl.account_id = a.id
            LEFT JOIN classifications c ON tl.classification_id = c.id
            WHERE tl.transaction_id = ? AND 
        """

        if is_debit:
            query += "tl.debit IS NOT NULL AND tl.debit > 0"
        else:
            query += "tl.credit IS NOT NULL AND tl.credit > 0"

        self.cursor.execute(query, (transaction_id,))

        results = []
        for row in self.cursor.fetchall():
            results.append({
                'id': row[0],
                'account_id': row[1],
                'account_name': row[2],
                'amount': row[3] if is_debit else row[4],
                'date': row[5],
                'classification_id': row[6],
                'classification_name': row[7] if row[7] else None
            })

        return results

    def consume_orphan_line(orphan_line_id, transaction_id):
        db.cursor.execute("""
            UPDATE orphan_transaction_lines 
            SET status = 'consumed', transaction_id = ? 
            WHERE id = ?
        """, (transaction_id, orphan_line_id))
        db.conn.commit()

# Initialize the database
db = Database('finance.db')

