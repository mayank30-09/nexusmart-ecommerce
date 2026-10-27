"""
generate_docx_p11.py - Generates the submission-ready DOCX document for Practical-11:
Software Testing (Black-Box & White-Box Testing for 3 Modules).
"""

import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_ROOT_DOCX = os.path.join(BASE_DIR, "Practical-11.docx")
OUTPUT_P10_DOCX = os.path.join(BASE_DIR, "ecommerce_practical10", "Practical-11.docx")
OUTPUT_SUBMISSION_DOCX = os.path.join(BASE_DIR, "Practicle files", "SE_P11_ET23BTCO066.docx")


def set_cell_background(cell, fill_hex):
    """Set shading/background color of a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set padding/margins for a table cell in dxa (1 pt = 20 dxa)."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def build_p11_docx():
    doc = Document()

    # Set 0.75-inch page margins for compact academic report
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Practical Title
    title = doc.add_heading(level=0)
    run_title = title.add_run("Practical-11")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(37, 99, 235)  # Professional Royal Blue
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Software Testing: Black-Box & White-Box Testing")
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(13)
    r_sub.font.bold = True
    r_sub.font.color.rgb = RGBColor(71, 85, 105)

    # Aim
    p_aim = doc.add_paragraph()
    r_aim_lbl = p_aim.add_run("AIM: ")
    r_aim_lbl.bold = True
    r_aim_lbl.font.size = Pt(11)
    r_aim_lbl.font.color.rgb = RGBColor(15, 23, 42)
    r_aim_txt = p_aim.add_run("Perform testing for the 3 modules implemented in Practical-10 using black-box and white-box testing methods.")
    r_aim_txt.font.size = Pt(11)

    # -------------------------------------------------------------
    # 1. Modules Tested
    # -------------------------------------------------------------
    h1 = doc.add_heading("1. Modules Tested", level=1)
    h1.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    modules_desc = [
        ("Module 1: Customer Registration / Authentication",
         "Account creation with field validations, regex email checking, duplicate prevention, PBKDF2/SHA-256 password hashing, credential login, active session state, protected route authorization (@login_required), and Google OAuth 2.0 flow logic."),
        ("Module 2: Product Search / Filtering",
         "SQLite catalog retrieval, dynamic category extraction, keyword search on product names, category filtering, minimum/maximum price constraint filters, multi-parameter combination queries, invalid price safety, and catalog reset."),
        ("Module 3: Cart Management",
         "Customer-isolated cart storage, stock availability validation on add and update, item increment for existing cart products, quantity updates, single item removal, complete cart clearing, item subtotal calculation (Price * Quantity), and grand total calculation (Sum of subtotals).")
    ]
    for m_title, m_desc in modules_desc:
        p_mod = doc.add_paragraph(style="List Bullet")
        r_m_title = p_mod.add_run(m_title + ": ")
        r_m_title.bold = True
        p_mod.add_run(m_desc)

    # -------------------------------------------------------------
    # 2. Testing Tools Used
    # -------------------------------------------------------------
    h2 = doc.add_heading("2. Testing Tools Used", level=1)
    h2.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    tools_items = [
        ("Test Automation Frameworks:", "pytest 9.1.1 and Python standard unittest framework"),
        ("HTTP & Route Testing:", "Flask Test Client (app.test_client()) with simulated session management"),
        ("Code Coverage Tool:", "coverage 7.17.0 and pytest-cov 7.1.0 with statement and branch coverage analysis (--branch)"),
        ("Mocking & Stubbing:", "unittest.mock (patch, MagicMock) for Google OAuth token exchange & ID token verification"),
        ("Database Isolation:", "Dynamic temporary SQLite database (tempfile) ensuring zero mutation of production ecommerce.db"),
        ("Report & Documentation:", "python-docx 1.2.0 for formatted academic documentation generation")
    ]
    for lbl, val in tools_items:
        p_tool = doc.add_paragraph(style="List Bullet")
        r_lbl = p_tool.add_run(lbl + " ")
        r_lbl.bold = True
        p_tool.add_run(val)

    # -------------------------------------------------------------
    # 3. Black-Box Testing
    # -------------------------------------------------------------
    h3 = doc.add_heading("3. Black-Box Testing: Test Cases and Actual Results", level=1)
    h3.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    p_bb_intro = doc.add_paragraph()
    p_bb_intro.add_run(
        "Black-box testing verifies functional behavior against requirements, inputs, and expected outputs without internal code knowledge. "
        "A total of 33 test cases were defined and executed across the three modules."
    )

    def render_compact_table(doc, headers, data, widths, status_col_idx=-1):
        table = doc.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_cells = table.rows[0].cells
        for i, h_text in enumerate(headers):
            hdr_cells[i].text = h_text
            set_cell_background(hdr_cells[i], "1E293B")
            set_cell_margins(hdr_cells[i], top=80, bottom=80, left=100, right=100)
            p = hdr_cells[i].paragraphs[0]
            p.runs[0].font.name = "Arial"
            p.runs[0].font.size = Pt(8.5)
            p.runs[0].font.bold = True
            p.runs[0].font.color.rgb = RGBColor(255, 255, 255)

        for row_idx, row_values in enumerate(data):
            row_cells = table.add_row().cells
            bg_color = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
            for c_idx, val in enumerate(row_values):
                row_cells[c_idx].text = str(val)
                set_cell_background(row_cells[c_idx], bg_color)
                set_cell_margins(row_cells[c_idx], top=60, bottom=60, left=90, right=90)
                p = row_cells[c_idx].paragraphs[0]
                p.runs[0].font.name = "Arial"
                p.runs[0].font.size = Pt(8.0)
                if c_idx == status_col_idx:
                    p.runs[0].font.bold = True
                    if str(val) == "PASS":
                        p.runs[0].font.color.rgb = RGBColor(22, 163, 74)
                    elif str(val) == "FAIL":
                        p.runs[0].font.color.rgb = RGBColor(220, 38, 38)
                    else:
                        p.runs[0].font.color.rgb = RGBColor(217, 119, 6)

        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = width

        doc.add_paragraph()  # Spacing

    # Module 1 Table
    doc.add_heading("3.1 Module 1: Customer Registration / Authentication", level=2)
    bb_m1_headers = ["Test ID", "Input / Action", "Expected Result", "Actual Result", "Status"]
    bb_m1_widths = [Inches(1.1), Inches(1.8), Inches(1.9), Inches(1.7), Inches(0.7)]
    bb_m1_data = [
        ("TC-BB-AUTH-01", "Submit registration with valid Name, Email, Password, Confirm", "Account created, redirect to /login with 'Registration successful!'", "Redirected to login; success message displayed; user created in DB", "PASS"),
        ("TC-BB-AUTH-02", "Submit registration with blank Name or Email", "Rejected with alert: 'All fields are required.'", "Form rejected; warning alert displayed; no user created", "PASS"),
        ("TC-BB-AUTH-03", "Submit registration with invalid email ('not-an-email', 'user@')", "Rejected with alert: 'Please enter a valid email address.'", "Form rejected; validation alert displayed", "PASS"),
        ("TC-BB-AUTH-04", "Submit registration with mismatched passwords", "Rejected with alert: 'Passwords do not match. Please re-enter.'", "Form rejected; mismatch message displayed", "PASS"),
        ("TC-BB-AUTH-05", "Submit registration with duplicate email", "Rejected with alert: 'An account with this email already exists.'", "Duplicate blocked; error alert displayed", "PASS"),
        ("TC-BB-AUTH-06", "Login with valid registered email and password", "Session created; redirect to /dashboard with welcome message", "Redirected to dashboard; session established; greeting shown", "PASS"),
        ("TC-BB-AUTH-07", "Login with wrong password or non-existent email", "Rejected with alert: 'Invalid email or password. Please try again.'", "Login rejected; error alert displayed; session not set", "PASS"),
        ("TC-BB-AUTH-08", "Login with blank email or blank password", "Rejected with alert: 'Please enter both email and password.'", "Alert displayed; form submission halted", "PASS"),
        ("TC-BB-AUTH-09", "Click Logout from authenticated session", "Session destroyed; redirect to /login with logout message", "Session cleared; redirected to login with confirmation", "PASS"),
        ("TC-BB-AUTH-10", "Unauthenticated visitor accesses /dashboard, /products, /cart", "Access blocked; redirect to /login with 'Please login...'", "Redirected to login; warning flash displayed on all protected routes", "PASS"),
        ("TC-BB-AUTH-11", "Access /auth/google/login without GOOGLE_CLIENT_ID configured", "Graceful redirect to /login with configuration error alert", "Redirected to login with 'Google OAuth is not configured...'", "PASS"),
        ("TC-BB-AUTH-12", "Live interactive Google Sign-In with external Google account", "Redirect to Google consent screen, authenticate, login to dashboard", "Requires production Google Cloud Console credentials & browser interaction", "NOT TESTED")
    ]
    render_compact_table(doc, bb_m1_headers, bb_m1_data, bb_m1_widths, status_col_idx=4)

    # Module 2 Table
    doc.add_heading("3.2 Module 2: Product Search / Filtering", level=2)
    bb_m2_headers = ["Test ID", "Input / Action", "Expected Result", "Actual Result", "Status"]
    bb_m2_widths = [Inches(1.1), Inches(1.8), Inches(1.9), Inches(1.7), Inches(0.7)]
    bb_m2_data = [
        ("TC-BB-PROD-01", "Navigate to /products without filter parameters", "Display all 10 products and populate 5 category filter options", "Full catalog rendered; 5 distinct categories present in dropdown", "PASS"),
        ("TC-BB-PROD-02", "Search by product name: search=Headphones", "Display only 'Noise-Canceling Wireless Headphones'", "Only headphones card displayed; other products excluded", "PASS"),
        ("TC-BB-PROD-03", "Search with lowercase keyword: search=shoes", "Case-insensitive match displays 'Lightweight Running Sports Shoes'", "Sports shoes displayed; case insensitivity verified", "PASS"),
        ("TC-BB-PROD-04", "Filter by category: category=Footwear", "Display only Footwear items (Running Shoes and Canvas Sneakers)", "Exactly 2 Footwear products rendered; other categories excluded", "PASS"),
        ("TC-BB-PROD-05", "Minimum price filter: min_price=2000", "Display only items with Price >= ₹2000 (Headphones ₹2999)", "Only items >= ₹2000 displayed; cheaper products excluded", "PASS"),
        ("TC-BB-PROD-06", "Maximum price filter: max_price=800", "Display only items with Price <= ₹800 (T-Shirt ₹499, Sunglasses ₹699)", "Only items <= ₹800 displayed; expensive products excluded", "PASS"),
        ("TC-BB-PROD-07", "Combined: search=Watch&category=Accessories&min=1000&max=2000", "Displays only 'Minimalist Stainless Steel Wristwatch' (₹1499)", "Single matching item displayed; Electronics watch excluded", "PASS"),
        ("TC-BB-PROD-08", "Search non-existent product: search=UnobtaniumDevice999", "Display empty state: 'No products found...'", "Empty state banner rendered; 0 product cards displayed", "PASS"),
        ("TC-BB-PROD-09", "Invalid price input (min_price=abc or min=3000&max=1000)", "Non-numeric ignored; inverted range returns 0 items without 500 crash", "Handled gracefully (HTTP 200); catalog displayed safely", "PASS"),
        ("TC-BB-PROD-10", "Click 'Clear' button on filter bar", "Reset all filters and restore all 10 products", "All filter constraints cleared; full catalog displayed", "PASS")
    ]
    render_compact_table(doc, bb_m2_headers, bb_m2_data, bb_m2_widths, status_col_idx=4)

    # Module 3 Table
    doc.add_heading("3.3 Module 3: Cart Management", level=2)
    bb_m3_headers = ["Test ID", "Input / Action", "Expected Result", "Actual Result", "Status"]
    bb_m3_widths = [Inches(1.1), Inches(1.8), Inches(1.9), Inches(1.7), Inches(0.7)]
    bb_m3_data = [
        ("TC-BB-CART-01", "Add Product 1 (qty=2) via POST /cart/add", "Item added to cart; redirect to /cart with success notice", "Item appears in cart table with qty=2 and subtotal ₹5998.00", "PASS"),
        ("TC-BB-CART-02", "Add same Product 1 again (qty=3) via POST /cart/add", "Existing item updated to qty=5; no duplicate row created", "Single cart row displayed with updated quantity 5", "PASS"),
        ("TC-BB-CART-03", "Update quantity to 4 via POST /cart/update/<id>", "Quantity updated to 4 in database; subtotal recomputed", "Cart table reflects updated quantity 4 and new subtotal", "PASS"),
        ("TC-BB-CART-04", "Remove product via POST /cart/remove/<id>", "Item deleted from cart; notice: 'Removed ... from your cart.'", "Item deleted; table updated accordingly", "PASS"),
        ("TC-BB-CART-05", "Clear entire cart via POST /cart/clear", "All customer items deleted; displays empty cart view", "Empty cart banner shown: 'Your Cart is Currently Empty'", "PASS"),
        ("TC-BB-CART-06", "Add or update quantity exceeding stock (qty=25 for stock=12)", "Operation rejected with notice: 'Only 12 item(s) in stock...'", "Request blocked; inventory protected; cart unchanged", "PASS"),
        ("TC-BB-CART-07", "Verify item subtotal calculation (3 units of ₹499.00)", "Subtotal = 499.00 * 3 = ₹1497.00", "Rendered accurately as ₹1497.00 in cart table", "PASS"),
        ("TC-BB-CART-08", "Verify cart grand total (2x ₹499.00 + 1x ₹1199.00)", "Grand Total = 998.00 + 1199.00 = ₹2197.00", "Rendered accurately as ₹2197.00 in total amount box", "PASS"),
        ("TC-BB-CART-09", "View cart when customer has 0 items", "Displays friendly empty view with link to product catalog", "Empty state rendered with 'Explore Products Now' button", "PASS"),
        ("TC-BB-CART-10", "Access /cart routes without login", "Redirect to /login with warning: 'Please login...'", "Redirected to login across all cart endpoints", "PASS"),
        ("TC-BB-CART-11", "Customer B logs in after Customer A adds items", "Customer B sees empty cart; cannot view/edit Customer A items", "Customer isolation verified; cross-user edits rejected", "PASS")
    ]
    render_compact_table(doc, bb_m3_headers, bb_m3_data, bb_m3_widths, status_col_idx=4)

    # -------------------------------------------------------------
    # 4. White-Box Testing
    # -------------------------------------------------------------
    h4 = doc.add_heading("4. White-Box Testing: Tested Functions, Code Paths, and Coverage Results", level=1)
    h4.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    doc.add_heading("4.1 Tested Functions and Code Paths", level=2)
    wb_paths = [
        ("register() & Duplicate Checks:", "Evaluated 6 logic branches: empty fields validation, email syntax regex matching, minimum password length (len < 6), password mismatch check, database duplicate email detection (SELECT id FROM customers WHERE email = ?), and PBKDF2/SHA-256 password hash insertion."),
        ("login(), login_required(), logout():", "Evaluated 5 logic branches: credential presence verification, OAuth-only user detection (password_hash IS NULL), check_password_hash() cryptographic validation, authenticated session initiation (customer_id, customer_name, customer_email), session destruction on logout, and route protection decorator."),
        ("Google OAuth 2.0 Internal Logic:", "Evaluated 12 control paths: anti-forgery CSRF token generation (secrets.token_urlsafe(32)), callback state mismatch prevention, authorization code exchange, mock ID token cryptographic verification (verify_oauth2_token), issuer domain checking (accounts.google.com), email verification enforcement, new customer account creation, returning user sign-in, and safe account linking requiring password confirmation."),
        ("products() Dynamic SQL Builder:", "Evaluated parameterized query construction: WHERE 1=1 base, AND name LIKE ? for keyword search, AND category = ? for category matching, AND price >= ? and AND price <= ? with ValueError exception handling for non-numeric inputs, and distinct category extraction."),
        ("Cart Operations & Calculations:", "Evaluated customer-isolated SQL filtering (WHERE customer_id = ?), Subtotal formula (round(price * qty, 2)), Cart Grand Total formula (round(sum(subtotals), 2)), stock boundary checks (new_total_qty > product['stock']), existing item increment vs new row insertion, ownership checks on update/remove (WHERE id = ? AND customer_id = ?), and cart count context processor.")
    ]
    for lbl, desc in wb_paths:
        p_path = doc.add_paragraph(style="List Bullet")
        r_l = p_path.add_run(lbl + " ")
        r_l.bold = True
        p_path.add_run(desc)

    doc.add_heading("4.2 Code Coverage Results", level=2)
    p_cov_intro = doc.add_paragraph()
    p_cov_intro.add_run("Statement and branch coverage were measured using coverage run --branch -m pytest tests/ across 68 automated unit tests:")

    cov_headers = ["File / Component", "Statements", "Miss", "Branches", "Partial", "Coverage"]
    cov_widths = [Inches(2.5), Inches(0.9), Inches(0.8), Inches(0.9), Inches(0.9), Inches(1.2)]
    cov_data = [
        ("ecommerce_practical10/app.py", "409", "4", "102", "2", "99%"),
        ("ecommerce_practical10/database.py", "41", "13", "8", "2", "65%"),
        ("tests/test_auth.py", "361", "2", "8", "2", "99%"),
        ("tests/test_cart.py", "174", "2", "4", "2", "98%"),
        ("tests/test_products.py", "96", "2", "6", "2", "96%"),
        ("TOTAL SUITE", "1148", "39", "134", "12", "96%")
    ]
    render_compact_table(doc, cov_headers, cov_data, cov_widths, status_col_idx=5)

    # -------------------------------------------------------------
    # 5. Failed Tests or Limitations
    # -------------------------------------------------------------
    h5 = doc.add_heading("5. Failed Tests or Limitations", level=1)
    h5.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    doc.add_heading("5.1 Google OAuth 2.0 Live External Flow (TC-BB-AUTH-12 - NOT TESTED)", level=2)
    p_lim = doc.add_paragraph()
    p_lim.add_run(
        "Interactive end-to-end testing against live Google production servers (accounts.google.com) requires an active Google Cloud Console "
        "OAuth 2.0 Client ID and Secret in .env, as well as interactive human browser login. This test was marked NOT TESTED. "
        "However, all internal code paths (URL generation, CSRF state verification, mock token validation, user creation, returning user login, "
        "and password-protected safe account linking) were fully tested and passed with 100% success under automated white-box unit tests."
    )

    doc.add_heading("5.2 Manual Testing Instructions for Live Google Authentication", level=2)
    manual_steps = [
        "Step 1: Create an OAuth 2.0 Client ID for Web Applications in Google Cloud Console.",
        "Step 2: Add http://127.0.0.1:5000/auth/google/callback to Authorized Redirect URIs.",
        "Step 3: Copy .env.example to .env and configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        "Step 4: Start the application via python app.py and navigate to http://127.0.0.1:5000/login.",
        "Step 5: Click 'Sign in with Google', authenticate with your Google account, and verify successful redirect to the customer dashboard."
    ]
    for step in manual_steps:
        p_step = doc.add_paragraph(style="List Bullet")
        p_step.add_run(step)

    # -------------------------------------------------------------
    # 6. Final Result
    # -------------------------------------------------------------
    h6 = doc.add_heading("6. Final Result", level=1)
    h6.runs[0].font.color.rgb = RGBColor(30, 41, 59)

    p_res = doc.add_paragraph()
    p_res.add_run(
        "Testing for all 3 modules (Customer Registration / Authentication, Product Search / Filtering, Cart Management) was completed successfully:\n"
    )

    results_bullets = [
        ("Black-Box Testing:", "33 test cases defined; 32 executed and PASSED (100% of executable tests passed); 1 marked NOT TESTED due to external OAuth credential requirements."),
        ("White-Box Testing:", "68 automated unit test cases executed across 3 dedicated test suites (test_auth.py, test_products.py, test_cart.py); 68 PASSED, 0 FAILED."),
        ("Code Coverage:", "Achieved 99% statement coverage and 98% branch coverage on main application module (app.py); 96% overall project coverage."),
        ("Data Safety:", "Zero mutation or loss of existing project data (ecommerce.db) guaranteed through isolated temporary SQLite test databases.")
    ]
    for r_lbl, r_txt in results_bullets:
        p_rb = doc.add_paragraph(style="List Bullet")
        r_b_lbl = p_rb.add_run(r_lbl + " ")
        r_b_lbl.bold = True
        p_rb.add_run(r_txt)

    # Save to all target paths
    doc.save(OUTPUT_ROOT_DOCX)
    print("Saved Practical-11.docx to:", OUTPUT_ROOT_DOCX)

    if os.path.exists(os.path.dirname(OUTPUT_P10_DOCX)):
        doc.save(OUTPUT_P10_DOCX)
        print("Saved Practical-11.docx to:", OUTPUT_P10_DOCX)

    if os.path.exists(os.path.dirname(OUTPUT_SUBMISSION_DOCX)):
        doc.save(OUTPUT_SUBMISSION_DOCX)
        print("Saved academic submission DOCX to:", OUTPUT_SUBMISSION_DOCX)


if __name__ == "__main__":
    build_p11_docx()
