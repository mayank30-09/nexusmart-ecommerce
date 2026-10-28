# NexusMart E-Commerce Platform — Known Limitations & Operational Considerations

## 1. Overview & Transparency Statement

In accordance with rigorous Software Engineering standards (Pressman SQA, IEEE 830, and academic evaluation criteria), this document transparently describes known boundaries, external dependencies, operational limits, and intentional design tradeoffs in the NexusMart platform.

---

## 2. External Service & Gateway Limitations

### 2.1 Razorpay Payment Gateway (Test Mode vs Live Mode)
- **Current State**: Operating exclusively in **Razorpay Test Mode** using simulated cards, UPI IDs, and net banking sandbox credentials.
- **Limitation**: Real currency transactions are intentionally disabled. Razorpay requires corporate business verification, GST registration, bank account validation, and KYC approval before activating Live Mode.
- **Action Required for Live Activation**:
  1. Complete merchant onboarding at [Razorpay Dashboard](https://dashboard.razorpay.com/).
  2. Toggle to "Live Mode" and generate Live API Keys.
  3. Update `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in production environment variables.

### 2.2 Google OAuth 2.0 Consent Screen (Testing Audience vs Production Verification)
- **Current State**: Operating under Google Cloud's **Testing Publishing Status**.
- **Limitation**: While in Testing mode, only Google accounts explicitly listed under "Test Users" in the Google Cloud Console OAuth consent screen can authenticate. Arbitrary public Google users will see an "Access Blocked: Authorization Error" screen until the app is submitted for verification or published.
- **Action Required for Public Audience**:
  1. Add customer tester emails to the Authorized Test Users list during review/evaluation.
  2. Submit the OAuth Consent Screen for public verification if launching publicly to external consumers.

---

## 3. Infrastructure & Deployment Limitations

### 3.1 Free-Tier Cloud Platform Cold Starts (e.g. Render Free Tier)
- **Behavior**: Free-tier web services on managed platforms such as Render automatically spin down into a sleep state after 15 minutes of inactivity.
- **Impact**: The initial HTTP request after a period of dormancy may experience a 30 to 50-second cold-start latency while the container is provisioned. Subsequent requests respond in under 200ms.
- **Mitigation**: Upgrading to a paid instance tier ($7/month) provides 24/7 always-on container execution without cold starts.

### 3.2 Automated Email Notifications
- **Current State**: Order confirmations and receipts are rendered on screen as high-fidelity digital invoices and stored in the database. Email delivery is simulated in flash messages and order records.
- **Future Enhancement**: Connecting a transactional email provider (such as SendGrid, Resend, or AWS SES) requires an authenticated sender domain and API key configured in `app.py`.

### 3.3 Concurrency Scaling Horizon
- **Current State**: Concurrency is safely handled using database write locks (`BEGIN IMMEDIATE` in SQLite, row-level `SELECT ... FOR UPDATE` in PostgreSQL), preventing double-spending and overselling of stock up to ~100 concurrent checkout sessions.
- **High-Scale Limitation**: For high-volume enterprise traffic (>10,000 requests/sec flash sales), a distributed caching and queuing layer (such as Redis with Celery) would be recommended to queue order placements rather than relying solely on relational database row locks.

### 3.4 Administrative Portal & Staff Operations
- **Current State**: Full Admin Operations Portal implemented (`FR-17` through `FR-20`) accessible at `/admin/login` and `/admin/dashboard`, protected by `@admin_required` RBAC check (`is_admin=1`). Provides live KPI monitoring (gross revenue, orders, catalog count, low-stock threshold), product catalog CRUD (`/admin/products`), direct warehouse stock adjustments (`/admin/products/<id>/stock`), order status transitions (`/admin/orders/<id>/status`), and promotional coupon management (`/admin/coupons`).
- **Future Enhancement**: Granular multi-tiered role definitions (e.g. warehouse staff vs financial auditor) and multi-factor authentication (MFA) for staff logins.
