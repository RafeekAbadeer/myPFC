import sqlite3
import datetime

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
                term TEXT CHECK (term IN ('long term', 'medium term', 'short term', 'undefined')) DEFAULT 'undefined',
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

        self.cursor.execute('''
                        CREATE TABLE IF NOT EXISTS filter_profiles (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            target_entity TEXT NOT NULL,
                            is_default BOOLEAN DEFAULT 0
                        )
                    ''')

        self.cursor.execute('''
                                CREATE TABLE IF NOT EXISTS filter_criteria (
                                    id INTEGER PRIMARY KEY,
                                    profile_id INTEGER NOT NULL,
                                    field_name TEXT NOT NULL,
                                    operator TEXT NOT NULL,
                                    value TEXT,
                                    FOREIGN KEY (profile_id) REFERENCES filter_profiles(id) ON DELETE CASCADE
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

    def insert_account(self, name, cat_id, default_currency_id=None, nature='both', term='undefined'):
        self.cursor.execute(
            "INSERT INTO accounts (name, cat_id, default_currency_id, nature, term) VALUES (?, ?, ?, ?, ?)",
            (name, cat_id, default_currency_id, nature, term))
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

    def get_accounts_by_nature(self, nature=None):
        """
        Get accounts filtered by their nature

        Args:
            nature: 'debit', 'credit', or None (for all accounts)

        Returns:
            List of accounts matching the nature criteria
        """
        query = """
            SELECT a.id, a.name
            FROM accounts a
        """

        params = []

        if nature:
            query += " WHERE a.nature = ? OR a.nature = 'both'"
            params.append(nature)

        query += " ORDER BY a.name"

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

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

    def update_account(self, id, name, cat_id, default_currency_id=None, nature='both', term='undefined'):
        self.cursor.execute(
            "UPDATE accounts SET name = ?, cat_id = ?, default_currency_id = ?, nature = ?, term = ? WHERE id = ?",
            (name, cat_id, default_currency_id, nature, term, id))
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
            SELECT a.id, a.name, c.name as category, cu.name as currency, a.nature, a.term
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
            SELECT a.id, a.name, a.cat_id, a.default_currency_id, c.name, cu.name, a.nature, a.term
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
                'currency_name': result[5],
                'nature': result[6],
                'term': result[7]
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

    def consume_orphan_line(self, orphan_line_id, transaction_id):
        self.cursor.execute("""
            UPDATE orphan_transaction_lines 
            SET status = 'consumed', transaction_id = ? 
            WHERE id = ?
        """, (transaction_id, orphan_line_id))
        self.conn.commit()

    def get_orphan_transactions(self, status=None):
        """Get orphan transactions with optional status filter"""
        query = "SELECT id, reference, import_date, status FROM orphan_transactions"
        params = []

        if status:
            query += " WHERE status = ?"
            params.append(status)

        query += " ORDER BY import_date DESC"
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_orphan_lines(self, orphan_transaction_id=None, status=None):
        """Get orphan transaction lines with optional filters"""
        query = """
            SELECT otl.id, otl.orphan_transaction_id, otl.description, 
                   otl.account_id, a.name as account_name, 
                   otl.debit, otl.credit, otl.status, otl.transaction_id, otl.notes
            FROM orphan_transaction_lines otl
            LEFT JOIN accounts a ON otl.account_id = a.id
            WHERE 1=1
        """
        params = []

        if orphan_transaction_id:
            query += " AND otl.orphan_transaction_id = ?"
            params.append(orphan_transaction_id)

        if status:
            query += " AND otl.status = ?"
            params.append(status)

        query += " ORDER BY otl.id"
        self.cursor.execute(query, params)

        results = []
        for row in self.cursor.fetchall():
            results.append({
                'id': row[0],
                'orphan_transaction_id': row[1],
                'description': row[2],
                'account_id': row[3],
                'account_name': row[4] if row[4] else "Unknown",
                'debit': row[5],
                'credit': row[6],
                'status': row[7],
                'transaction_id': row[8],
                'notes': row[9] if len(row) > 9 else None
            })

        return results

    def insert_orphan_transaction(self, reference, lines_data):
        """
        Insert a new orphan transaction with its lines

        Args:
            reference: Reference for this batch import (e.g., filename)
            lines_data: List of dicts with line data (description, account_id, debit, credit)

        Returns:
            Orphan transaction ID
        """
        try:
            # Start a transaction
            self.begin_transaction()

            # Insert the orphan transaction
            import_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "INSERT INTO orphan_transactions (reference, import_date, status) VALUES (?, ?, 'new')",
                (reference, import_date)
            )
            orphan_transaction_id = self.cursor.lastrowid

            # Insert each line
            for line in lines_data:
                # Set status based on validity
                status = 'new' if line.get('valid', True) else 'error'

                description = line.get('description', '')
                account_id = line.get('account_id')
                debit = line.get('debit')
                credit = line.get('credit')

                # Store original account name if it couldn't be resolved
                notes = None
                if not account_id and line.get('account_name'):
                    notes = f"Original account name: {line.get('account_name')}"

                # Add a notes column to orphan_transaction_lines if it doesn't exist
                try:
                    self.cursor.execute("SELECT notes FROM orphan_transaction_lines LIMIT 1")
                except sqlite3.OperationalError:
                    self.cursor.execute("ALTER TABLE orphan_transaction_lines ADD COLUMN notes TEXT")

                self.cursor.execute("""
                    INSERT INTO orphan_transaction_lines 
                    (orphan_transaction_id, description, account_id, debit, credit, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    orphan_transaction_id,
                    description,
                    account_id,
                    debit,
                    credit,
                    status,
                    notes
                ))

            # Commit transaction
            self.commit_transaction()
            return orphan_transaction_id

        except Exception as e:
            # Rollback on error
            self.rollback_transaction()
            raise e

    def update_orphan_line(self, line_id, description=None, account_id=None, debit=None, credit=None, date=None,
                           status=None):
        """Update an orphan transaction line"""
        updates = []
        params = []

        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if account_id is not None:
            updates.append("account_id = ?")
            params.append(account_id)

        if debit is not None:
            updates.append("debit = ?")
            params.append(debit)

        if credit is not None:
            updates.append("credit = ?")
            params.append(credit)

        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if not updates:
            return

        query = f"UPDATE orphan_transaction_lines SET {', '.join(updates)} WHERE id = ?"
        params.append(line_id)

        self.cursor.execute(query, params)
        self.conn.commit()

    def create_transaction_from_orphans(self, description, currency_id, orphan_line_ids,
                                        balancing_account_id, balancing_date):
        """
        Create a balanced transaction from orphan lines by adding a balancing entry

        Args:
            description: Transaction description
            currency_id: Currency ID
            orphan_line_ids: List of orphan line IDs to include
            balancing_account_id: Account to use for balancing
            balancing_date: Date for the balancing entry

        Returns:
            New transaction ID
        """
        try:
            # Start a transaction
            self.begin_transaction()

            # Get all the orphan lines
            orphan_lines = []
            for line_id in orphan_line_ids:
                self.cursor.execute("""
                    SELECT description, account_id, debit, credit
                    FROM orphan_transaction_lines
                    WHERE id = ? AND status = 'new'
                """, (line_id,))

                line = self.cursor.fetchone()
                if not line:
                    raise ValueError(f"Orphan line {line_id} not found or already processed")

                orphan_lines.append({
                    'id': line_id,
                    'description': line[0],
                    'account_id': line[1],
                    'debit': line[2] or 0,
                    'credit': line[3] or 0
                })

            # Calculate the imbalance
            total_debit = sum(line['debit'] for line in orphan_lines)
            total_credit = sum(line['credit'] for line in orphan_lines)
            imbalance = total_debit - total_credit

            # Create the new transaction
            self.cursor.execute("INSERT INTO transactions (description, currency_id) VALUES (?, ?)",
                                (description, currency_id))
            transaction_id = self.cursor.lastrowid

            # Add all orphan lines to the transaction
            for line in orphan_lines:
                self.cursor.execute("""
                    INSERT INTO transaction_lines
                    (transaction_id, account_id, debit, credit, date, classification_id)
                    VALUES (?, ?, ?, ?, ?, NULL)
                """, (
                    transaction_id,
                    line['account_id'],
                    line['debit'] or None,
                    line['credit'] or None,
                    balancing_date,  # Use the balancing date for consistency
                    None
                ))

                # Mark the orphan line as consumed
                self.cursor.execute("""
                    UPDATE orphan_transaction_lines
                    SET status = 'consumed', transaction_id = ?
                    WHERE id = ?
                """, (transaction_id, line['id']))

            # Add balancing entry if needed
            if abs(imbalance) > 0.001:  # Use small epsilon for floating point comparison
                if imbalance > 0:
                    # Need a credit to balance
                    self.cursor.execute("""
                        INSERT INTO transaction_lines
                        (transaction_id, account_id, debit, credit, date, classification_id)
                        VALUES (?, ?, NULL, ?, ?, NULL)
                    """, (transaction_id, balancing_account_id, imbalance, balancing_date))
                else:
                    # Need a debit to balance
                    self.cursor.execute("""
                        INSERT INTO transaction_lines
                        (transaction_id, account_id, debit, credit, date, classification_id)
                        VALUES (?, ?, ?, NULL, ?, NULL)
                    """, (transaction_id, balancing_account_id, abs(imbalance), balancing_date))

            # Commit the transaction
            self.commit_transaction()
            return transaction_id

        except Exception as e:
            # Rollback on error
            self.rollback_transaction()
            raise e

    def update_orphan_transaction_status(self, orphan_transaction_id, status):
        """Update the status of an orphan transaction"""
        if status not in ('new', 'processed', 'ignored'):
            raise ValueError(f"Invalid status: {status}")

        self.cursor.execute(
            "UPDATE orphan_transactions SET status = ? WHERE id = ?",
            (status, orphan_transaction_id)
        )
        self.conn.commit()

    def update_orphan_line_status(self, orphan_line_id, status):
        """Update the status of an orphan transaction line"""
        if status not in ('new', 'consumed', 'ignored'):
            raise ValueError(f"Invalid status: {status}")

        self.cursor.execute(
            "UPDATE orphan_transaction_lines SET status = ? WHERE id = ?",
            (status, orphan_line_id)
        )
        self.conn.commit()

        def filter_accounts(self, category_filter=None, name_filter=None, nature_filter=None, term_filter=None):
            """Filter accounts by category, name, nature, and/or term"""
            query = """
                SELECT a.id, a.name, c.name as category, cu.name as currency, a.nature, a.term
                FROM accounts a
                JOIN cat c ON a.cat_id = c.id
                LEFT JOIN currency cu ON a.default_currency_id = cu.id
                WHERE 1=1
            """
            params = []

            if category_filter:
                query += " AND c.name = ?"
                params.append(category_filter)

            if name_filter:
                query += " AND a.name LIKE ?"
                params.append(f"%{name_filter}%")

            if nature_filter:
                query += " AND a.nature = ?"
                params.append(nature_filter)

            if term_filter:
                query += " AND a.term = ?"
                params.append(term_filter)

            query += " ORDER BY a.name"

            self.cursor.execute(query, params)
            return self.cursor.fetchall()

# Initialize the database
db = Database('finance.db')


def get_counterpart_suggestions(description, amount, is_credit):
    """Get more intelligent counterpart account suggestions"""
    suggestions = []

    # 1. Exact match by description (case insensitive)
    exact_matches = db.execute_query("""
        SELECT a.id, a.name, COUNT(*) as count
        FROM transactions t
        JOIN transaction_lines tl1 ON t.id = tl1.transaction_id
        JOIN transaction_lines tl2 ON t.id = tl2.transaction_id
        JOIN accounts a ON tl2.account_id = a.id
        WHERE LOWER(t.description) = LOWER(?)
        AND tl1.credit IS NOT NULL AND tl1.credit > 0
        AND tl2.debit IS NOT NULL AND tl2.debit > 0
        GROUP BY a.id
        ORDER BY count DESC
        LIMIT 3
    """, (description,))

    for match in exact_matches:
        suggestions.append({
            'account_id': match[0],
            'account_name': match[1],
            'confidence': 90,
            'reason': 'Exact description match'
        })

    # 2. Partial match by description keywords
    keywords = [word.lower() for word in description.split() if len(word) > 3]
    for keyword in keywords:
        partial_matches = db.execute_query("""
            SELECT a.id, a.name, COUNT(*) as count
            FROM transactions t
            JOIN transaction_lines tl1 ON t.id = tl1.transaction_id
            JOIN transaction_lines tl2 ON t.id = tl2.transaction_id
            JOIN accounts a ON tl2.account_id = a.id
            WHERE LOWER(t.description) LIKE ?
            AND tl1.credit IS NOT NULL AND tl1.credit > 0
            AND tl2.debit IS NOT NULL AND tl2.debit > 0
            GROUP BY a.id
            ORDER BY count DESC
            LIMIT 2
        """, (f'%{keyword}%',))

        for match in partial_matches:
            # Avoid duplicates
            if not any(s['account_id'] == match[0] for s in suggestions):
                suggestions.append({
                    'account_id': match[0],
                    'account_name': match[1],
                    'confidence': 60,
                    'reason': f'Contains keyword "{keyword}"'
                })

    # 3. Match by amount range (similar transaction amounts)
    amount_matches = db.execute_query("""
        SELECT a.id, a.name, COUNT(*) as count
        FROM transactions t
        JOIN transaction_lines tl1 ON t.id = tl1.transaction_id
        JOIN transaction_lines tl2 ON t.id = tl2.transaction_id
        JOIN accounts a ON tl2.account_id = a.id
        WHERE tl1.credit BETWEEN ? AND ?
        AND tl2.debit IS NOT NULL AND tl2.debit > 0
        GROUP BY a.id
        ORDER BY count DESC
        LIMIT 2
    """, (amount * 0.95, amount * 1.05))  # 5% range

    for match in amount_matches:
        # Avoid duplicates
        if not any(s['account_id'] == match[0] for s in suggestions):
            suggestions.append({
                'account_id': match[0],
                'account_name': match[1],
                'confidence': 40,
                'reason': f'Similar amount (${amount:.2f})'
            })

    # 4. Recently used accounts (as a fallback)
    recent_accounts = db.execute_query("""
        SELECT a.id, a.name
        FROM accounts a
        JOIN transaction_lines tl ON a.id = tl.account_id
        GROUP BY a.id
        ORDER BY MAX(tl.date) DESC
        LIMIT 5
    """)

    for account in recent_accounts:
        # Avoid duplicates
        if not any(s['account_id'] == account[0] for s in suggestions):
            suggestions.append({
                'account_id': account[0],
                'account_name': account[1],
                'confidence': 20,
                'reason': 'Recently used account'
            })

    # Sort by confidence
    suggestions.sort(key=lambda s: s['confidence'], reverse=True)

    return suggestions


# Add to database.py class
def execute_query(self, query, params=()):
    """Execute a custom SQL query with parameters"""
    self.cursor.execute(query, params)
    return self.cursor.fetchall()


def get_orphan_line_by_id(self, line_id):
    """Get an orphan transaction line by ID"""
    self.cursor.execute("""
        SELECT id, orphan_transaction_id, description, account_id, debit, credit, status
        FROM orphan_transaction_lines
        WHERE id = ?
    """, (line_id,))

    row = self.cursor.fetchone()
    if row:
        return {
            'id': row[0],
            'orphan_transaction_id': row[1],
            'description': row[2],
            'account_id': row[3],
            'debit': row[4],
            'credit': row[5],
            'status': row[6]
        }
    return None

