"""
conftest.py - Pytest and Unittest Configuration & Fixtures for Practical-11.
Provides isolated temporary database setup, test clients, and session helpers.
"""

import os
import sys
import tempfile
import sqlite3
import pytest

# Ensure ecommerce_practical10 is on sys.path
PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ecommerce_practical10")
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import database
import app as flask_app

# Global reference to temporary test database file
_TEMP_DB_FILE = None


def setup_temp_db():
    """Create a temporary SQLite database file and initialize schema and seed data."""
    global _TEMP_DB_FILE
    if _TEMP_DB_FILE is None or not os.path.exists(_TEMP_DB_FILE.name):
        _TEMP_DB_FILE = tempfile.NamedTemporaryFile(suffix="_test_p11.db", delete=False)
        _TEMP_DB_FILE.close()
    
    database.DB_PATH = _TEMP_DB_FILE.name
    database.init_db()
    return _TEMP_DB_FILE.name


def teardown_temp_db():
    """Remove temporary SQLite database file if it exists."""
    global _TEMP_DB_FILE
    if _TEMP_DB_FILE and os.path.exists(_TEMP_DB_FILE.name):
        try:
            os.unlink(_TEMP_DB_FILE.name)
        except OSError:
            pass
        _TEMP_DB_FILE = None


# Initialize temp database at module load time for unittest compatibility
setup_temp_db()


@pytest.fixture(scope="session", autouse=True)
def test_db_session():
    """Session-scoped fixture ensuring isolated temporary database lifecycle."""
    temp_path = setup_temp_db()
    yield temp_path
    teardown_temp_db()


@pytest.fixture
def app():
    """Pytest fixture providing configured Flask application."""
    app_instance = flask_app.app
    app_instance.config["TESTING"] = True
    app_instance.config["WTF_CSRF_ENABLED"] = False
    return app_instance


@pytest.fixture
def client(app):
    """Pytest fixture providing test client with fresh customer & cart state."""
    # Reset mutable tables between tests
    conn = database.get_db_connection()
    conn.execute("DELETE FROM order_items;")
    conn.execute("DELETE FROM orders;")
    conn.execute("DELETE FROM customer_addresses;")
    conn.execute("DELETE FROM cart_items;")
    conn.execute("DELETE FROM customers WHERE email LIKE '%@test.com' OR email LIKE '%@example.com';")
    conn.commit()
    conn.close()

    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def auth_client(client):
    """Pytest fixture providing an authenticated test client."""
    # Register and log in a baseline test customer
    client.post("/register", data={
        "name": "Auth User",
        "email": "authuser@test.com",
        "password": "password123",
        "confirm_password": "password123"
    }, follow_redirects=True)

    client.post("/login", data={
        "email": "authuser@test.com",
        "password": "password123"
    }, follow_redirects=True)

    yield client


class BaseTestCase:
    """Base class for unittest.TestCase test classes providing clean isolation."""
    def setUp(self):
        setup_temp_db()
        self.app = flask_app.app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

        # Clean mutable tables before each test
        conn = database.get_db_connection()
        conn.execute("DELETE FROM order_items;")
        conn.execute("DELETE FROM orders;")
        conn.execute("DELETE FROM customer_addresses;")
        conn.execute("DELETE FROM cart_items;")
        conn.execute("DELETE FROM customers WHERE email LIKE '%@test.com' OR email LIKE '%@example.com';")
        conn.commit()
        conn.close()

    def register(self, name="Test User", email="test@test.com", password="password123", confirm="password123"):
        return self.client.post("/register", data={
            "name": name,
            "email": email,
            "password": password,
            "confirm_password": confirm
        }, follow_redirects=True)

    def login(self, email="test@test.com", password="password123"):
        return self.client.post("/login", data={
            "email": email,
            "password": password
        }, follow_redirects=True)
