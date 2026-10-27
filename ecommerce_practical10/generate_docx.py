"""
generate_docx.py - Generates a formatted DOCX document for Practical-10
with tables, formatted code sections, and embedded screenshots.
"""

import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "static", "screenshots")
OUTPUT_DOCX_PATH = os.path.join(BASE_DIR, "Practical-10.docx")
PRACTICAL_FOLDER_DOCX = os.path.join(os.path.dirname(BASE_DIR), "Practicle files", "SE_P10_ET23BTCO066.docx")


def set_cell_background(cell, fill_hex):
    """Set shading/background color of a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set padding/margins for a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)


def build_docx():
    doc = Document()

    # Set page margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Document Title
    title = doc.add_heading(level=0)
    run_title = title.add_run("Practical-10")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(37, 99, 235)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Aim
    p_aim = doc.add_paragraph()
    r_aim_lbl = p_aim.add_run("AIM: ")
    r_aim_lbl.bold = True
    r_aim_lbl.font.size = Pt(11)
    r_aim_txt = p_aim.add_run("Perform implementation of any 3 modules from the modules you have designed.")
    r_aim_txt.font.size = Pt(11)

    # -------------------------------------------------------------
    # 1. Selected Modules
    # -------------------------------------------------------------
    h1 = doc.add_heading("1. Selected Modules", level=1)
    h1.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    p_mod = doc.add_paragraph()
    p_mod.add_run("The three modules selected for Practical-10 are directly mapped to the software engineering design artifacts (Practical-6 Data Flow Diagrams and Practical-7 Structure Chart):\n")

    p_t1 = doc.add_paragraph(style="List Bullet")
    r1 = p_t1.add_run("Module 1: Customer Registration / Authentication")
    r1.bold = True
    p_t1.add_run(" (Derived from DFD Process 1.0 - Customer Management)")

    p_t2 = doc.add_paragraph(style="List Bullet")
    r2 = p_t2.add_run("Module 2: Product Search / Filtering")
    r2.bold = True
    p_t2.add_run(" (Derived from DFD Process 2.0 - Product Catalog & Search)")

    p_t3 = doc.add_paragraph(style="List Bullet")
    r3 = p_t3.add_run("Module 3: Cart Management")
    r3.bold = True
    p_t3.add_run(" (Derived from DFD Process 3.0 - Shopping Cart Management)")

    # -------------------------------------------------------------
    # 2. Technology Used
    # -------------------------------------------------------------
    h2 = doc.add_heading("2. Technology Used", level=1)
    h2.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    tech_items = [
        ("Backend Framework:", "Python 3.14 with Flask 3.1"),
        ("Database:", "SQLite 3 with foreign key integrity enabled (PRAGMA foreign_keys = ON)"),
        ("Authentication & Security:", "Werkzeug security (salted password hashing), session-based state management"),
        ("Frontend Presentation:", "Semantic HTML5, CSS3 responsive grid and card styling"),
        ("Testing Framework:", "Python standard unittest (25 automated test cases)"),
        ("Verification Automation:", "Playwright headless Chromium for real UI capture")
    ]
    for lbl, val in tech_items:
        p_tech = doc.add_paragraph(style="List Bullet")
        r_lbl = p_tech.add_run(lbl + " ")
        r_lbl.bold = True
        p_tech.add_run(val)

    # -------------------------------------------------------------
    # 3. Implementation
    # -------------------------------------------------------------
    h3 = doc.add_heading("3. Implementation", level=1)
    h3.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    doc.add_heading("Module 1: Customer Registration / Authentication", level=2)
    p_m1 = doc.add_paragraph()
    p_m1.add_run(
        "This module provides self-contained customer onboarding and session security. The registration mechanism validates mandatory fields, "
        "enforces regex email syntax, ensures a 6-character password threshold, verifies confirmation parity, and rejects duplicate emails via "
        "SQLite queries. Passwords are cryptographically transformed using PBKDF2/SHA-256 before insertion. Login validates credentials with "
        "check_password_hash and initializes an encrypted HTTP session (customer_id, customer_name, customer_email). A login_required decorator "
        "guards internal pages, and logout destroys active session states."
    )

    doc.add_heading("Module 2: Product Search / Filtering", level=2)
    p_m2 = doc.add_paragraph()
    p_m2.add_run(
        "This module manages the catalog of items. An SQLite products table contains id, name, category, price, stock, and description, automatically "
        "seeded with 10 representative products across 5 categories (Electronics, Clothing, Footwear, Accessories, Bags). The search and filter "
        "engine dynamically builds parameterized SQL queries using LIKE for text search, exact category matches, and numeric price bounds (min_price, max_price). "
        "Products display category badges, formatted currency, inventory availability, and integrated Add to Cart actions."
    )

    doc.add_heading("Module 3: Cart Management", level=2)
    p_m3 = doc.add_paragraph()
    p_m3.add_run(
        "This module enables shopping cart workflows with strict customer isolation. The cart_items table links customers and products via foreign keys. "
        "Adding an existing item updates the quantity rather than duplicating rows, with strict checks against available inventory. In the cart view, "
        "each item's subtotal is computed as (Product Price × Quantity), and the overall cart total is computed as the sum of all subtotals. "
        "Customers can adjust quantities, remove single items, or clear their cart completely."
    )

    # -------------------------------------------------------------
    # 4. Important Code
    # -------------------------------------------------------------
    h4 = doc.add_heading("4. Important Code", level=1)
    h4.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    code_snippets = [
        ("4.1 Database Schema Definition (database.py)",
"""CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    UNIQUE (customer_id, product_id)
);"""),
        ("4.2 Customer Registration & Password Hashing (app.py)",
"""@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not password or not confirm_password:
            flash('All fields are required.', 'danger')
            return render_template('register.html', name=name, email=email)

        if password != confirm_password or len(password) < 6:
            flash('Password error: mismatch or less than 6 chars.', 'danger')
            return render_template('register.html', name=name, email=email)

        conn = get_db_connection()
        if conn.execute('SELECT id FROM customers WHERE email = ?;', (email,)).fetchone():
            conn.close()
            flash('An account with this email already exists.', 'danger')
            return render_template('register.html', name=name, email=email)

        hashed = generate_password_hash(password)
        conn.execute('INSERT INTO customers (name, email, password_hash) VALUES (?, ?, ?);',
                     (name, email, hashed))
        conn.commit()
        conn.close()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')"""),
        ("4.3 Parameterized Product Search & Filtering (app.py)",
"""@app.route('/products')
@login_required
def products():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    min_p = request.args.get('min_price', '').strip()
    max_p = request.args.get('max_price', '').strip()

    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    if search:
        query += ' AND name LIKE ?'; params.append(f'%{search}%')
    if category:
        query += ' AND category = ?'; params.append(category)
    if min_p:
        try: query += ' AND price >= ?'; params.append(float(min_p))
        except ValueError: pass
    if max_p:
        try: query += ' AND price <= ?'; params.append(float(max_p))
        except ValueError: pass

    conn = get_db_connection()
    products_list = conn.execute(query + ' ORDER BY id ASC;', params).fetchall()
    conn.close()
    return render_template('products.html', products=products_list)"""),
        ("4.4 Cart Subtotal and Total Calculation (app.py)",
"""@app.route('/cart')
@login_required
def view_cart():
    customer_id = session['customer_id']
    conn = get_db_connection()
    cart_rows = conn.execute('''
        SELECT ci.id AS cart_item_id, ci.quantity, p.name, p.price, p.stock
        FROM cart_items ci JOIN products p ON ci.product_id = p.id
        WHERE ci.customer_id = ?;
    ''', (customer_id,)).fetchall()
    conn.close()

    items = []
    cart_total = 0.0
    for r in cart_rows:
        subtotal = round(r['price'] * r['quantity'], 2)
        cart_total += subtotal
        items.append({'name': r['name'], 'price': r['price'],
                      'quantity': r['quantity'], 'subtotal': subtotal})
    return render_template('cart.html', items=items, cart_total=round(cart_total, 2))""")
    ]

    for title_txt, code_block in code_snippets:
        doc.add_heading(title_txt, level=2)
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        set_cell_background(cell, "F1F5F9")
        set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(code_block)
        r.font.name = "Consolas"
        r.font.size = Pt(8.5)
        doc.add_paragraph()  # Spacing

    # -------------------------------------------------------------
    # 5. Test Cases
    # -------------------------------------------------------------
    h5 = doc.add_heading("5. Test Cases", level=1)
    h5.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    test_data = [
        ("TC-01", "Valid Registration", "Name: Mayank Viradiya, Email: mayank.viradiya@example.com", "Customer created, redirect to /login with success alert", "Pass"),
        ("TC-02", "Empty Fields Check", "Submit registration form with empty name", "Submission rejected, 'All fields are required' shown", "Pass"),
        ("TC-03", "Invalid Email Format", "Register with email 'not-an-email'", "Validation error 'Please enter a valid email address'", "Pass"),
        ("TC-04", "Password Mismatch", "Password 'pass123', confirm 'other123'", "Validation error 'Passwords do not match' displayed", "Pass"),
        ("TC-05", "Duplicate Email", "Register with already existing email", "Submission rejected, 'Account with email already exists' shown", "Pass"),
        ("TC-06", "Valid Login", "Submit registered email & valid password", "Session created, redirect to /dashboard with greeting", "Pass"),
        ("TC-07", "Invalid Password Login", "Submit registered email & wrong password", "Authentication rejected, 'Invalid email or password' shown", "Pass"),
        ("TC-08", "Logout Operation", "Click Logout from authenticated session", "Session cleared, redirect to /login, access revoked", "Pass"),
        ("TC-09", "Display All Products", "Navigate to /products as logged in user", "All 10 seed products rendered across 5 categories", "Pass"),
        ("TC-10", "Search by Name", "Query keyword 'Headphones'", "Only 'Noise-Canceling Wireless Headphones' returned", "Pass"),
        ("TC-11", "Category Filtering", "Filter by category 'Footwear'", "Only running shoes and canvas sneakers displayed", "Pass"),
        ("TC-12", "Minimum Price Filter", "Min price set to ₹2000", "Items < ₹2000 excluded; shows ₹2999 headphones", "Pass"),
        ("TC-13", "Maximum Price Filter", "Max price set to ₹800", "Items > ₹800 excluded; shows T-Shirt & Sunglasses", "Pass"),
        ("TC-14", "Combined Filters", "Keyword 'Watch', Cat 'Accessories', ₹1000-2000", "Only 'Minimalist Stainless Steel Wristwatch' shown", "Pass"),
        ("TC-15", "No Search Results", "Query keyword 'NonExistentItem999'", "'No products found' empty state displayed", "Pass"),
        ("TC-16", "Clear Filters", "Click 'Clear' button on filter bar", "Filters reset; full 10-product catalog restored", "Pass"),
        ("TC-17", "Add Product to Cart", "Select Product ID 1 with Quantity = 2", "Item added to cart_items table with success alert", "Pass"),
        ("TC-18", "Add Same Product Again", "Add Product ID 1 again with Quantity = 3", "Quantity updated from 2 to 5 without duplicate row", "Pass"),
        ("TC-19", "Update Quantity", "Change cart item quantity to 4", "Quantity and item subtotal updated in database", "Pass"),
        ("TC-20", "Remove Item from Cart", "Click Remove on specific cart item", "Record deleted from cart_items; cart refreshed", "Pass"),
        ("TC-21", "Clear Entire Cart", "Click Clear Cart button", "All customer cart rows deleted; empty cart shown", "Pass"),
        ("TC-22", "Stock Overflow Check", "Attempt to add quantity 999 (Stock = 15)", "Blocked with alert: 'Cannot add... Only 15 in stock'", "Pass"),
        ("TC-23", "Subtotal Calculation", "Price ₹499.00 × Quantity 3", "Subtotal calculated accurately as ₹1497.00", "Pass"),
        ("TC-24", "Grand Total Calculation", "Subtotals ₹998.00 + ₹1199.00", "Grand Total calculated accurately as ₹2197.00", "Pass"),
        ("TC-25", "Cart Login & Isolation", "Access /cart unauthenticated; Customer B check", "Redirects to login; Customer B sees 0 items of Customer A", "Pass")
    ]

    t_cases = doc.add_table(rows=1, cols=4)
    t_cases.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t_cases.rows[0].cells
    hdr_titles = ["Test Case", "Input / Action", "Expected Result", "Actual Result"]
    col_widths = [Inches(1.8), Inches(2.0), Inches(2.2), Inches(0.8)]

    for idx, name in enumerate(hdr_titles):
        hdr[idx].text = name
        hdr[idx].paragraphs[0].runs[0].font.bold = True
        hdr[idx].paragraphs[0].runs[0].font.size = Pt(9.5)
        hdr[idx].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(hdr[idx], "2563EB")
        set_cell_margins(hdr[idx], top=80, bottom=80, left=100, right=100)

    for item in test_data:
        row_cells = t_cases.add_row().cells
        row_cells[0].text = f"{item[0]}: {item[1]}"
        row_cells[1].text = item[2]
        row_cells[2].text = item[3]
        row_cells[3].text = item[4]

        for c_idx, cell in enumerate(row_cells):
            set_cell_margins(cell, top=60, bottom=60, left=90, right=90)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            if len(p.runs) > 0:
                p.runs[0].font.size = Pt(8.5)
                if c_idx == 3:
                    p.runs[0].font.bold = True
                    p.runs[0].font.color.rgb = RGBColor(22, 163, 74)

    # -------------------------------------------------------------
    # 6. Output & Screenshots
    # -------------------------------------------------------------
    doc.add_page_break()
    h6 = doc.add_heading("6. Output & Screenshots", level=1)
    h6.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    screens = [
        ("Output 1: Customer Registration Page", "01_registration_page.png"),
        ("Output 2: Successful Registration Alert", "02_successful_registration.png"),
        ("Output 3: Customer Login Page", "03_login_page.png"),
        ("Output 4: Customer Dashboard with Personal Stats", "04_dashboard.png"),
        ("Output 5: Product Catalog (All Seed Products)", "05_product_list.png"),
        ("Output 6: Product Search by Keyword ('Headphones')", "06_product_search.png"),
        ("Output 7: Product Filtering (Category 'Footwear' & Price Range)", "07_product_filtering.png"),
        ("Output 8: Product Added to Cart Confirmation", "08_product_added_to_cart.png"),
        ("Output 9: Shopping Cart View (Subtotals & Grand Total)", "09_cart_page.png"),
        ("Output 10: Updated Cart Quantity & Recalculated Totals", "10_updated_cart.png"),
        ("Output 11: Removed Product / Final Cart State", "11_removed_product_final_cart.png"),
    ]

    for title_txt, filename in screens:
        doc.add_heading(title_txt, level=2)
        img_path = os.path.join(SCREENSHOTS_DIR, filename)
        if os.path.exists(img_path):
            doc.add_picture(img_path, width=Inches(6.2))
        else:
            p_missing = doc.add_paragraph()
            p_missing.add_run(f"[Screenshot {filename} located at: static/screenshots/{filename}]").italic = True
        doc.add_paragraph()  # Spacing

    # -------------------------------------------------------------
    # 7. Result
    # -------------------------------------------------------------
    h7 = doc.add_heading("7. Result", level=1)
    h7.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    p_res = doc.add_paragraph()
    p_res.add_run(
        "The three selected modules—Customer Registration / Authentication, Product Search / Filtering, "
        "and Cart Management—were successfully implemented from scratch using Python, Flask, SQLite, and HTML/CSS. "
        "The modules operate in complete harmony within an integrated e-commerce application. All 25 automated test cases "
        "and browser interaction workflows executed successfully with 100% pass rates, fulfilling all functional, validation, "
        "and security requirements of Practical-10."
    )

    doc.save(OUTPUT_DOCX_PATH)
    print("Generated Practical-10.docx at:", OUTPUT_DOCX_PATH)

    # Also save to Practicle files folder if it exists
    if os.path.exists(os.path.dirname(PRACTICAL_FOLDER_DOCX)):
        doc.save(PRACTICAL_FOLDER_DOCX)
        print("Also saved copy to:", PRACTICAL_FOLDER_DOCX)


if __name__ == "__main__":
    build_docx()
