"""
Root test runner: allows running `python test_app.py` directly from workspace root.
"""
import os
import sys
import subprocess

PROJECT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecommerce_practical10")
TEST_SCRIPT = os.path.join(PROJECT_DIR, "test_app.py")

if __name__ == "__main__":
    result = subprocess.run([sys.executable, TEST_SCRIPT], cwd=PROJECT_DIR)
    sys.exit(result.returncode)
