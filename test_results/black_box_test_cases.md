# Black-Box Test Cases & Execution Report

**Project:** E-Commerce Website (Practical-11)  
**Methodology:** Black-Box Testing (Equivalence Partitioning, Boundary Value Analysis, Error Guessing, State Transition)  
**Execution Date:** 2026-10-24  
**Test Framework:** Flask Test Client / Automated HTTP Verification  

---

## 1. Summary of Test Execution

| Module | Total Cases | PASS | FAIL | NOT TESTED | Pass Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Module 1: Customer Registration / Auth** | 12 | 11 | 0 | 1 | 91.7% (100% of executable) |
| **Module 2: Product Search / Filtering** | 10 | 10 | 0 | 0 | 100.0% |
| **Module 3: Cart Management** | 11 | 11 | 0 | 0 | 100.0% |
| **TOTAL** | **33** | **32** | **0** | **1** | **97.0% (100% of executable)** |

*Note on NOT TESTED case:* Live end-to-end interactive Google OAuth sign-in against `accounts.google.com` requires production Google Cloud Console credentials (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) and human browser interaction. The route behavior, error handling, CSRF defense, and mock verification are fully tested under white-box test cases.

---

## 2. Module 1: Customer Registration / Authentication

| Test ID | Module | Input / Action | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **TC-BB-AUTH-01** | Customer Auth | Submit registration form with valid Name ("John Doe"), valid Email ("john.doe@test.com"), password ("pass123"), and matching confirmation ("pass123"). | Account created in database, redirect to `/login` with success message: *"Registration successful! Please login with your credentials."* | HTTP 200/302, redirected to login, success message displayed, user record persisted in database. | **PASS** |
| **TC-BB-AUTH-02** | Customer Auth | Submit registration form with one or more empty fields (e.g., Name="", Email="test@test.com", Password="123", Confirm="123"). | Form rejected with danger alert: *"All fields are required."*, user remains on registration page. | HTTP 200, danger flash displayed: *"All fields are required."*, no record created. | **PASS** |
| **TC-BB-AUTH-03** | Customer Auth | Submit registration with invalid email formats (e.g., "not-an-email", "@missinguser.com", "user@"). | Validation fails with message: *"Please enter a valid email address."*, form re-rendered with entered values. | HTTP 200, alert displayed: *"Please enter a valid email address."*, registration blocked. | **PASS** |
| **TC-BB-AUTH-04** | Customer Auth | Submit registration with mismatched passwords (Password="password123", Confirm="different456"). | Validation error displayed: *"Passwords do not match. Please re-enter."*, account creation rejected. | HTTP 200, alert displayed: *"Passwords do not match. Please re-enter."*, no user created. | **PASS** |
| **TC-BB-AUTH-05** | Customer Auth | Submit registration with duplicate email address already present in `customers` table. | System blocks duplicate and displays: *"An account with this email already exists. Please login."* | HTTP 200, danger alert displayed: *"An account with this email already exists. Please login."*, duplicate prevented. | **PASS** |
| **TC-BB-AUTH-06** | Customer Auth | Submit login form with registered email ("john.doe@test.com") and valid password ("pass123"). | Authenticated session created (`customer_id`, `customer_name`), redirect to `/dashboard` with *"Welcome back, John Doe!"* | HTTP 200/302, redirect to `/dashboard`, session established, personalized greeting rendered. | **PASS** |
| **TC-BB-AUTH-07** | Customer Auth | Submit login form with wrong password or unregistered email. | Authentication rejected with message: *"Invalid email or password. Please try again."*, session remains unauthenticated. | HTTP 200, alert displayed: *"Invalid email or password. Please try again."*, no session created. | **PASS** |
| **TC-BB-AUTH-08** | Customer Auth | Submit login form with blank email or blank password. | Form rejected with message: *"Please enter both email and password."* | HTTP 200, danger message displayed: *"Please enter both email and password."* | **PASS** |
| **TC-BB-AUTH-09** | Customer Auth | Authenticated user clicks Logout (`/logout`). | Session cleared, redirected to `/login` with notification: *"You have been logged out successfully."* | HTTP 200/302, session destroyed, user redirected to login with confirmation alert. | **PASS** |
| **TC-BB-AUTH-10** | Customer Auth | Unauthenticated visitor navigates directly to protected routes: `/dashboard`, `/products`, `/cart`. | Access blocked, redirected to `/login` with warning: *"Please login to access this page."* | HTTP 200/302, redirected to `/login`, flash message displayed for all protected endpoints. | **PASS** |
| **TC-BB-AUTH-11** | Customer Auth | Navigate to `/auth/google/login` without configured server credentials (`GOOGLE_CLIENT_ID` unset). | Graceful redirect to `/login` with message: *"Google OAuth is not configured on this server. Please configure GOOGLE_CLIENT_ID..."* | HTTP 200/302, redirect to login, clear configuration message displayed without unhandled crash. | **PASS** |
| **TC-BB-AUTH-12** | Customer Auth | Live interactive Google Sign-In with external Google account pop-up and OAuth token grant. | Redirect to Google consent screen, user logs into Google account, redirects to `/auth/google/callback`, logs in. | Cannot execute in headless environment without production Google OAuth Client Secret & live user interaction. | **NOT TESTED** |

---

## 3. Module 2: Product Search / Filtering

| Test ID | Module | Input / Action | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **TC-BB-PROD-01** | Search & Filter | Navigate to `/products` without query parameters. | Displays full product catalog (10 items) and populates category dropdown with all 5 distinct categories. | HTTP 200, all 10 products rendered across Electronics, Clothing, Footwear, Accessories, Bags. | **PASS** |
| **TC-BB-PROD-02** | Search & Filter | Enter keyword "Headphones" into product name search input (`/products?search=Headphones`). | Only "Noise-Canceling Wireless Headphones" displayed; unrelated catalog items excluded. | HTTP 200, only Headphones displayed, search summary badge confirms 1 item found. | **PASS** |
| **TC-BB-PROD-03** | Search & Filter | Enter search keyword "shoes" (case-insensitive substring match). | "Lightweight Running Sports Shoes" displayed, matching regardless of letter case. | HTTP 200, sports shoes displayed; non-matching items excluded. | **PASS** |
| **TC-BB-PROD-04** | Search & Filter | Select "Footwear" in Category filter dropdown (`/products?category=Footwear`). | Only products with `category='Footwear'` displayed ("Running Sports Shoes", "Canvas Low-Top Sneakers"). | HTTP 200, exactly 2 footwear items displayed; items from other categories excluded. | **PASS** |
| **TC-BB-PROD-05** | Search & Filter | Apply minimum price filter of ₹2000 (`/products?min_price=2000`). | Only products with `price >= 2000` displayed (e.g. Headphones ₹2999); lower-priced items excluded. | HTTP 200, only items $\ge 2000$ displayed; T-Shirts (₹499) and Backpacks (₹1199) excluded. | **PASS** |
| **TC-BB-PROD-06** | Search & Filter | Apply maximum price filter of ₹800 (`/products?max_price=800`). | Only products with `price <= 800` displayed (T-Shirt ₹499, Sunglasses ₹699). | HTTP 200, only items $\le 800$ displayed; premium items excluded. | **PASS** |
| **TC-BB-PROD-07** | Search & Filter | Combine keyword "Watch", category "Accessories", min_price=1000, max_price=2000 (`/products?search=Watch&category=Accessories&min_price=1000&max_price=2000`). | Displays only "Minimalist Stainless Steel Wristwatch" (₹1499). Electronics watch excluded due to category. | HTTP 200, exact single item matching all 4 constraints displayed. | **PASS** |
| **TC-BB-PROD-08** | Search & Filter | Search for non-existent keyword "NonExistentItem999" (`/products?search=NonExistentItem999`). | Zero products displayed; friendly message *"No products found matching your search and filter criteria"* rendered. | HTTP 200, empty search state with clear user guidance displayed. | **PASS** |
| **TC-BB-PROD-09** | Search & Filter | Supply non-numeric or inverted price values (`min_price=3000&max_price=1000` or `min_price=abc`). | Non-numeric input ignored gracefully; inverted range yields 0 items without server exception (HTTP 200). | HTTP 200, invalid strings handled safely by type parser, inverted range displays zero items gracefully. | **PASS** |
| **TC-BB-PROD-10** | Search & Filter | Click "Clear" button or navigate back to base `/products` URL. | All active search and filter constraints removed; full catalog of 10 items re-displayed. | HTTP 200, filter inputs reset, complete product catalog restored. | **PASS** |

---

## 4. Module 3: Cart Management

| Test ID | Module | Input / Action | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **TC-BB-CART-01** | Cart Management | Logged-in user adds Product 1 (Headphones, qty=2) via POST `/cart/add`. | Item added to `cart_items` table, redirect to `/cart`, success alert: *"Added 2 x 'Noise-Canceling Wireless Headphones' to your shopping cart."* | HTTP 200/302, item displayed in cart with qty=2 and subtotal ₹5998.00. | **PASS** |
| **TC-BB-CART-02** | Cart Management | Add same Product 1 again with qty=3 via POST `/cart/add`. | Existing item row updated to quantity=5; no duplicate row created in `cart_items`. | HTTP 200/302, single row for Product 1 displayed with updated quantity 5. | **PASS** |
| **TC-BB-CART-03** | Cart Management | Change item quantity from 2 to 4 via POST `/cart/update/<id>`. | Quantity updated in database, flash: *"Updated quantity of '...' to 4."*, subtotal recomputed. | HTTP 200/302, quantity updated to 4, subtotal updated dynamically. | **PASS** |
| **TC-BB-CART-04** | Cart Management | Click Remove button on cart item via POST `/cart/remove/<id>`. | Record deleted from `cart_items`, alert: *"Removed '...' from your cart."*, row removed from table. | HTTP 200/302, item deleted from customer cart, table reflects deletion. | **PASS** |
| **TC-BB-CART-05** | Cart Management | Click "Clear Cart" button via POST `/cart/clear`. | All records for customer deleted, displays empty cart view: *"Your Cart is Currently Empty"*. | HTTP 200/302, all items wiped, empty state banner displayed with "Explore Products Now" button. | **PASS** |
| **TC-BB-CART-06** | Cart Management | Attempt to add or update quantity exceeding available stock (e.g. qty=25 for stock=12). | Operation rejected with boundary alert: *"Cannot add... Only 12 item(s) in stock..."*, inventory protected. | HTTP 200/302, request rejected, inventory limit respected, cart quantity unchanged. | **PASS** |
| **TC-BB-CART-07** | Cart Management | Verify item subtotal calculation for 3 units of ₹499.00 T-Shirt. | Subtotal equals $\text{Price} \times \text{Quantity} = 499.00 \times 3 = ₹1497.00$. | Subtotal rendered as `₹1497.00` in cart table. | **PASS** |
| **TC-BB-CART-08** | Cart Management | Verify cart grand total with 2 items: 2x ₹499.00 (₹998.00) + 1x ₹1199.00 (₹1199.00). | Grand total equals sum of subtotals: $998.00 + 1199.00 = ₹2197.00$. | Grand total rendered as `₹2197.00` in total amount box. | **PASS** |
| **TC-BB-CART-09** | Cart Management | Navigate to `/cart` when customer has 0 items. | Displays friendly empty state: *"Your Cart is Currently Empty"* and button to explore products. | HTTP 200, empty cart banner rendered with link to catalog. | **PASS** |
| **TC-BB-CART-10** | Cart Management | Unauthenticated visitor attempts to access `/cart`, `/cart/add`, `/cart/update/1`, or `/cart/clear`. | Directs to `/login` with warning: *"Please login to access this page."* | HTTP 200/302, all cart routes enforce login requirement. | **PASS** |
| **TC-BB-CART-11** | Cart Management | Customer A adds items to cart. Customer B logs in and navigates to `/cart`. | Customer B sees an empty cart; Customer B cannot view, edit, or delete Customer A's items. | HTTP 200, complete customer cart isolation verified; cross-customer ID mutation rejected with "Cart item not found". | **PASS** |
