"""
database.py - Database connection, multi-engine support (SQLite & PostgreSQL),
schema migration, and product seeding for NexusMart E-Commerce.
"""

import os
import re
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "ecommerce.db")


class PostgresCursorWrapper:
    """
    Cursor proxy wrapper for PostgreSQL that adapts SQLite conventions:
    - Automatically converts '?' parameter placeholders to '%s'
    - Wraps rows to provide both dict (row['col']) and index (row[0]) access
    - Emulates cursor.lastrowid
    """
    def __init__(self, raw_cursor):
        self._cursor = raw_cursor
        self.lastrowid = None

    def execute(self, query, params=None):
        adapted_query = query.replace("?", "%s")
        # Handle SQLite-specific PRAGMAs gracefully
        if adapted_query.strip().upper().startswith("PRAGMA"):
            return self

        # Handle AUTOINCREMENT / lastrowid tracking for INSERTs
        is_insert = adapted_query.strip().upper().startswith("INSERT INTO")
        has_returning = "RETURNING" in adapted_query.upper()

        if is_insert and not has_returning:
            # Append RETURNING id to capture lastrowid if inserting into tables with id
            trimmed = adapted_query.rstrip("; \t\n")
            adapted_query = f"{trimmed} RETURNING id;"

        if params:
            self._cursor.execute(adapted_query, params)
        else:
            self._cursor.execute(adapted_query)

        if is_insert:
            try:
                row = self._cursor.fetchone()
                if row and "id" in row:
                    self.lastrowid = row["id"]
                elif row and len(row) > 0:
                    self.lastrowid = list(row.values())[0] if isinstance(row, dict) else row[0]
            except Exception:
                self.lastrowid = None

        return self

    def executemany(self, query, seq_of_params):
        adapted_query = query.replace("?", "%s")
        if adapted_query.strip().upper().startswith("PRAGMA"):
            return self
        return self._cursor.executemany(adapted_query, seq_of_params)

    def fetchone(self):
        row = self._cursor.fetchone()
        return PostgresRow(row) if row is not None else None

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [PostgresRow(r) for r in rows]

    def close(self):
        return self._cursor.close()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def __iter__(self):
        for row in self._cursor:
            yield PostgresRow(row)


class PostgresRow:
    """Wrapper that provides dict-key and tuple-index access like sqlite3.Row."""
    def __init__(self, data_dict):
        self._data = dict(data_dict) if data_dict else {}
        self._keys = list(self._data.keys())
        self._values = list(self._data.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def __contains__(self, key):
        return key in self._data

    def __repr__(self):
        return f"<PostgresRow {self._data}>"


class PostgresConnectionWrapper:
    """Connection proxy wrapper for PostgreSQL connection."""
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        import psycopg2.extras
        raw_cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return PostgresCursorWrapper(raw_cur)

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()


def get_db_connection():
    """
    Establish and return a database connection:
    - If DATABASE_URL is set (PostgreSQL), connects via psycopg2 with dictionary cursor.
    - Otherwise, connects to SQLite with foreign keys enabled and sqlite3.Row factory.
    """
    database_url = os.environ.get("DATABASE_URL", "").strip()

    if database_url and (database_url.startswith("postgres://") or database_url.startswith("postgresql://")):
        import psycopg2
        # Render and Heroku use postgres://, but SQLAlchemy/psycopg2 prefer postgresql://
        if database_url.startswith("postgres://"):
            database_url = "postgresql://" + database_url[len("postgres://"):]
        raw_conn = psycopg2.connect(database_url)
        return PostgresConnectionWrapper(raw_conn)

    # Default: Local SQLite database
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def is_postgres():
    """Check if the active database is PostgreSQL."""
    database_url = os.environ.get("DATABASE_URL", "").strip()
    return bool(database_url and (database_url.startswith("postgres://") or database_url.startswith("postgresql://")))


def init_db():
    """Create database tables if they do not exist and seed initial sample products."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if is_postgres():
        _init_postgres_schema(cursor)
    else:
        _init_sqlite_schema(cursor)

    conn.commit()

    # Check and seed initial products if catalog is empty
    count_row = conn.execute("SELECT COUNT(*) AS count FROM products;").fetchone()
    count = count_row["count"] if count_row else 0

    if count == 0:
        sample_products = [
            (
                "Noise-Canceling Wireless Headphones",
                "Electronics",
                2999.00,
                15,
                "Over-ear Bluetooth headphones with active noise cancellation and 30-hour battery life."
            ),
            (
                "Smart Fitness Tracker Watch",
                "Electronics",
                1899.00,
                20,
                "Waterproof smartwatch featuring continuous heart rate monitoring and OLED touch display."
            ),
            (
                "Classic Cotton Crewneck T-Shirt",
                "Clothing",
                499.00,
                35,
                "100% breathable organic cotton daily wear t-shirt with premium stitching."
            ),
            (
                "Slim Fit Stretch Denim Jeans",
                "Clothing",
                1299.00,
                25,
                "Durable and comfortable dark indigo denim jeans with flexible stretch fabric."
            ),
            (
                "Lightweight Running Sports Shoes",
                "Footwear",
                1799.00,
                18,
                "Breathable mesh athletic shoes with shock-absorbing EVA sole for daily running."
            ),
            (
                "Casual Canvas Low-Top Sneakers",
                "Footwear",
                899.00,
                22,
                "Classic street-style vulcanized rubber sole sneakers for everyday comfort."
            ),
            (
                "UV-Protected Polarized Sunglasses",
                "Accessories",
                699.00,
                30,
                "Unisex polarized sunglasses with anti-glare coating and lightweight alloy frame."
            ),
            (
                "Minimalist Stainless Steel Wristwatch",
                "Accessories",
                1499.00,
                12,
                "Sleek analog quartz watch with scratch-resistant mineral glass and metal strap."
            ),
            (
                "Water-Resistant Laptop Backpack",
                "Bags",
                1199.00,
                16,
                "Spacious multi-compartment travel backpack with dedicated 15.6-inch padded laptop sleeve."
            ),
            (
                "Multi-Utility Canvas Duffel Bag",
                "Bags",
                999.00,
                14,
                "Sturdy weekend travel bag with reinforced handles and detachable shoulder strap."
            )
        ]

        for p in sample_products:
            cursor.execute("""
            INSERT INTO products (name, category, price, stock, description)
            VALUES (?, ?, ?, ?, ?);
            """, p)

        conn.commit()

    # Seed default promo coupons if missing
    coupon_count = conn.execute("SELECT COUNT(*) AS count FROM coupons;").fetchone()["count"]
    if coupon_count == 0:
        sample_coupons = [
            ("WELCOME10", "percentage", 10.0, 500.0, 100, 0, None, None, 1),
            ("FLAT100", "fixed", 100.0, 1000.0, 50, 0, None, None, 1),
            ("FESTIVE20", "percentage", 20.0, 2000.0, 20, 0, None, None, 1),
        ]
        for c in sample_coupons:
            cursor.execute("""
            INSERT INTO coupons (code, discount_type, discount_value, min_cart_value, usage_limit, used_count, start_date, expiry_date, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, c)
        conn.commit()

    conn.close()


def _init_sqlite_schema(cursor):
    """SQLite-specific table schemas and migrations."""
    # 1. Customers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        google_id TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Products Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER NOT NULL,
        description TEXT
    );
    """)

    # 3. Cart Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
        UNIQUE (customer_id, product_id)
    );
    """)

    # 4. Customer Delivery Addresses Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        address_line TEXT NOT NULL,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        postal_code TEXT NOT NULL,
        is_default INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_addresses_customer_id ON customer_addresses (customer_id);")

    # 5. Discount Coupons Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        discount_type TEXT NOT NULL,
        discount_value REAL NOT NULL,
        min_cart_value REAL DEFAULT 0.0,
        usage_limit INTEGER DEFAULT NULL,
        used_count INTEGER DEFAULT 0,
        start_date DATE DEFAULT NULL,
        expiry_date DATE DEFAULT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_coupons_code ON coupons (code);")

    # 6. Orders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_reference TEXT UNIQUE NOT NULL,
        customer_id INTEGER NOT NULL,
        shipping_address_line TEXT NOT NULL,
        shipping_city TEXT NOT NULL,
        shipping_state TEXT NOT NULL,
        shipping_postal_code TEXT NOT NULL,
        subtotal REAL NOT NULL,
        discount_amount REAL NOT NULL DEFAULT 0.0,
        final_total REAL NOT NULL,
        coupon_code TEXT DEFAULT NULL,
        order_status TEXT NOT NULL DEFAULT 'Confirmed',
        payment_status TEXT NOT NULL DEFAULT 'Pending',
        payment_method TEXT NOT NULL,
        payment_reference TEXT DEFAULT NULL,
        razorpay_order_id TEXT DEFAULT NULL,
        razorpay_payment_id TEXT DEFAULT NULL,
        razorpay_signature TEXT DEFAULT NULL,
        idempotency_key TEXT UNIQUE DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE RESTRICT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id);")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_reference ON orders (order_reference);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_idempotency_key ON orders (idempotency_key);")

    # Migration: Ensure Razorpay columns exist if table was created earlier
    existing_cols = [row["name"] for row in cursor.execute("PRAGMA table_info(orders);").fetchall()]
    if "razorpay_order_id" not in existing_cols:
        cursor.execute("ALTER TABLE orders ADD COLUMN razorpay_order_id TEXT DEFAULT NULL;")
    if "razorpay_payment_id" not in existing_cols:
        cursor.execute("ALTER TABLE orders ADD COLUMN razorpay_payment_id TEXT DEFAULT NULL;")
    if "razorpay_signature" not in existing_cols:
        cursor.execute("ALTER TABLE orders ADD COLUMN razorpay_signature TEXT DEFAULT NULL;")

    # 7. Order Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        unit_price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        line_total REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE SET NULL
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id);")

    # 8. Webhook Events Table (for Idempotent Razorpay Webhook Deduplication)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_webhooks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT UNIQUE NOT NULL,
        event_type TEXT NOT NULL,
        payload TEXT,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_processed_webhooks_event_id ON processed_webhooks (event_id);")


def _init_postgres_schema(cursor):
    """PostgreSQL-specific table schemas and constraints."""
    # 1. Customers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255),
        google_id VARCHAR(255) UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Products Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        category VARCHAR(100) NOT NULL,
        price NUMERIC(10, 2) NOT NULL,
        stock INTEGER NOT NULL,
        description TEXT
    );
    """)

    # 3. Cart Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart_items (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL DEFAULT 1,
        UNIQUE (customer_id, product_id)
    );
    """)

    # 4. Customer Delivery Addresses Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_addresses (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
        address_line TEXT NOT NULL,
        city VARCHAR(100) NOT NULL,
        state VARCHAR(100) NOT NULL,
        postal_code VARCHAR(20) NOT NULL,
        is_default INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_customer_addresses_customer_id ON customer_addresses (customer_id);")

    # 5. Discount Coupons Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coupons (
        id SERIAL PRIMARY KEY,
        code VARCHAR(50) UNIQUE NOT NULL,
        discount_type VARCHAR(20) NOT NULL,
        discount_value NUMERIC(10, 2) NOT NULL,
        min_cart_value NUMERIC(10, 2) DEFAULT 0.0,
        usage_limit INTEGER DEFAULT NULL,
        used_count INTEGER DEFAULT 0,
        start_date DATE DEFAULT NULL,
        expiry_date DATE DEFAULT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 6. Orders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        order_reference VARCHAR(64) UNIQUE NOT NULL,
        customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
        shipping_address_line TEXT NOT NULL,
        shipping_city VARCHAR(100) NOT NULL,
        shipping_state VARCHAR(100) NOT NULL,
        shipping_postal_code VARCHAR(20) NOT NULL,
        subtotal NUMERIC(10, 2) NOT NULL,
        discount_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
        final_total NUMERIC(10, 2) NOT NULL,
        coupon_code VARCHAR(50) DEFAULT NULL,
        order_status VARCHAR(50) NOT NULL DEFAULT 'Confirmed',
        payment_status VARCHAR(50) NOT NULL DEFAULT 'Pending',
        payment_method VARCHAR(50) NOT NULL,
        payment_reference VARCHAR(255) DEFAULT NULL,
        razorpay_order_id VARCHAR(255) DEFAULT NULL,
        razorpay_payment_id VARCHAR(255) DEFAULT NULL,
        razorpay_signature VARCHAR(255) DEFAULT NULL,
        idempotency_key VARCHAR(128) UNIQUE DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_reference ON orders (order_reference);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_idempotency_key ON orders (idempotency_key);")

    # 7. Order Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
        product_name VARCHAR(255) NOT NULL,
        unit_price NUMERIC(10, 2) NOT NULL,
        quantity INTEGER NOT NULL,
        line_total NUMERIC(10, 2) NOT NULL
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id);")

    # 8. Webhook Events Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_webhooks (
        id SERIAL PRIMARY KEY,
        event_id VARCHAR(255) UNIQUE NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        payload TEXT,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_webhooks_event_id ON processed_webhooks (event_id);")
