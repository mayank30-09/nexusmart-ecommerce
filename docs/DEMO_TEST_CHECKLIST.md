# NexusMart — Faculty Demonstration Quick Checklist

Print or keep this concise checklist open during your project presentation to ensure all required academic demonstration criteria are systematically checked off.

---

## 📋 PRE-DEMONSTRATION CHECKLIST (5 Minutes Prior)

- [ ] Open terminal in `d:/AI-Workspace/projects/e-commerce-web/ecommerce_practical10`.
- [ ] Start the server: `python app.py`.
- [ ] Confirm server is running at `http://127.0.0.1:5000`.
- [ ] In browser or curl, check `http://127.0.0.1:5000/healthz` -> returns `{"status": "healthy"}`.
- [ ] Set or verify admin password using the secure interactive CLI prompt:
  ```bash
  python ../manage_admin.py reset-password admin@nexusmart.com
  ```

---

## 🛒 1. CUSTOMER JOURNEY WALKTHROUGH

- [ ] **1.1 Homepage & Navigation:**
  - Show responsive dark mode layout and live cart count pill in navbar.
  - Show featured products carousel and Indian Rupee (₹) pricing.
- [ ] **1.2 Catalog Search & Filters:**
  - Navigate to `/products`.
  - Filter by Category (e.g. select "Audio").
  - Search keyword "Noise".
  - Filter by price range (Min: ₹1000, Max: ₹5000).
  - Click "Clear Filters" to reset.
- [ ] **1.3 Product Details & Quantity Boundary Checks:**
  - Open a product (e.g. "Sony WH-1000XM5").
  - Note live stock indicator badge.
  - Attempt to add an invalid quantity (`-1` or `999`) to show client/server validation.
  - Add `1` unit to cart.
- [ ] **1.4 Cart Operations:**
  - Show shopping cart page with item subtotal.
  - Update quantity to `2`; verify automatic grand total calculation.
- [ ] **1.5 Customer Registration & Login:**
  - Register a new account (`faculty_test@nexusmart.com` / `DemoPass123!`).
  - Log in; observe greeting on Customer Dashboard.
  - Point out AI-Powered Product Recommendations.
- [ ] **1.6 Delivery Address Management:**
  - Navigate to `/profile`.
  - Add a delivery address; observe automatic "Default" tag.
- [ ] **1.7 Checkout & Promotional Coupon:**
  - Proceed to checkout from cart.
  - Apply coupon code `WELCOME10`; observe instant 10% discount deduction.

---

## 💳 2. PAYMENT & TRANSACTION VERIFICATION

- [ ] **2.1 Razorpay Standard Modal:**
  - Select "Online Payment (Razorpay)".
  - Click "Proceed to Payment" -> Razorpay modal opens in Test Mode.
- [ ] **2.2 Simulated Payment Flow:**
  - Use Test Card: `4111 1111 1111 1111`, Expiry: `12/28`, CVV: `123`.
  - Enter test OTP `123456` and submit.
- [ ] **2.3 Digital Invoice & Confirmation:**
  - Verify redirection to Order Confirmation page.
  - Confirm unique Order Reference (`ORD-20261028-XXXX`), status **Paid**, and correct discounted amount.
- [ ] **2.4 Order History & Snapshot Immutability:**
  - Navigate to `/orders`.
  - Open Order Details and show that customer address and unit prices are permanently preserved as immutable snapshots.

---

## 🔒 3. SECURITY & LOGOUT VERIFICATION (Priority 1)

- [ ] **3.1 Customer Logout:**
  - Click **Logout** in the navigation bar.
  - Confirm redirect to `/login` with success banner.
- [ ] **3.2 Browser Back-Button Test (bfcache Invalidation):**
  - Click the browser **Back** button.
  - Confirm the page automatically reloads or blocks cached display.
  - Confirm user is **NOT** logged in and sensitive customer data is **NOT** exposed.
- [ ] **3.3 Direct URL Revisit Test:**
  - Enter `http://127.0.0.1:5000/dashboard` directly in address bar.
  - Enter `http://127.0.0.1:5000/orders` directly in address bar.
  - Confirm immediate redirect to `/login` with `Please log in to access this page.`

---

## 🛠️ 4. ADMINISTRATOR PORTAL & OPERATIONS

- [ ] **4.1 Dedicated Admin Login:**
  - Navigate to `http://127.0.0.1:5000/admin/login`.
  - Log in as `admin@nexusmart.com` with the password configured above.
- [ ] **4.2 Operations Dashboard:**
  - Point out live KPIs: Gross Revenue (₹), Total Orders, Catalog Items, Low-Stock Alerts.
- [ ] **4.3 Direct Warehouse Inventory Adjustment:**
  - Go to `/admin/products`.
  - Adjust stock of a product by `+10` or `-5`; verify immediate reflection.
- [ ] **4.4 Order Fulfillment Lifecycle:**
  - Go to `/admin/orders`.
  - Find the order placed earlier.
  - Update status: `Confirmed` -> `Processing` -> `Shipped`.
- [ ] **4.5 Promotional Coupon Controls:**
  - Go to `/admin/coupons`.
  - Create a new coupon (e.g. `DEMO15` for 15% off).
- [ ] **4.6 Non-Admin Access Blocking:**
  - Log out of Admin.
  - Log in as standard customer.
  - Attempt to open `http://127.0.0.1:5000/admin/dashboard` -> HTTP 403 Forbidden.

---

## 📱 5. RESPONSIVE DESIGN VERIFICATION

- [ ] Press `F12` to open Chrome/Edge DevTools.
- [ ] Toggle Device Emulation (select **iPhone 14** or **Pixel 7**).
- [ ] Show responsive mobile header, stacked product cards, touch-friendly buttons, and checkout form.
