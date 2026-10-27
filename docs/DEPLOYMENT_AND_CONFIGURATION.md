# NexusMart E-Commerce Platform — Deployment & Configuration Guide

This comprehensive guide details the production deployment, environment variable configuration, cloud database setup, Google OAuth 2.0 provisioning, and Razorpay payment gateway integration for the **NexusMart** E-Commerce platform.

---

## 1. Architecture & Deployment Overview

NexusMart is engineered to run seamlessly across local development, staging environments, and production cloud providers (such as **Render**, **Railway**, or **Heroku**) with dual database support:
- **Local Development**: Python 3.10+ / Flask, SQLite (`ecommerce.db`).
- **Production Deployment**: Gunicorn WSGI HTTP Server with multi-threading, Managed PostgreSQL database, HTTPS reverse-proxy termination, and CDN-ready static asset delivery.

### Production Start Command
```bash
gunicorn --chdir ecommerce_practical10 --bind 0.0.0.0:$PORT --workers 2 --threads 4 wsgi:app
```

### Health Check Endpoint
- **URL**: `https://<YOUR_DEPLOYED_DOMAIN>/healthz`
- **Method**: `GET`
- **Response**: `{"status": "healthy", "service": "NexusMart Web", "database": "connected"}` (HTTP 200)

---

## 2. Environment Variables Configuration Guide

The application requires 8 key environment variables. In production, configure these via your hosting platform's Environment Settings dashboard. For local development, copy `.env.example` to `.env`.

| Variable Name | Sensitive? | Target Environment | Purpose & Description | Where to Obtain | How to Verify Loaded Safely |
|---|---|---|---|---|---|
| `FLASK_ENV` | No | All | Sets Flask runtime mode (`production` or `development`). When `production`, debug mode is disabled. | Developer configuration | Inspect start log; confirm `Debug mode: off`. |
| `FLASK_SECRET_KEY` | **YES** | All (Mandatory in prod) | Cryptographically signs session cookies and anti-CSRF tokens. Must remain constant across restarts. | Generate locally: `python -c "import secrets; print(secrets.token_hex(32))"` | Log in, restart service, refresh page; session should remain active. |
| `APP_BASE_URL` | No | Production / Staging | Canonical public HTTPS base URL (e.g. `https://nexusmart.onrender.com`). Used for absolute redirect URI generation. | Provided by hosting platform dashboard | Initiate Google login; verify redirect URI starts with this base URL. |
| `DATABASE_URL` | **YES** | Production | Connection string for PostgreSQL (e.g., `postgresql://user:pass@host:5432/dbname`). If unset, defaults to local SQLite. | Render Managed Postgres Dashboard -> "Internal Database URL" | Visit `/healthz`; confirm `"database": "connected"`. |
| `RAZORPAY_KEY_ID` | Semi (Public ID) | All | Public API Key identifier for Razorpay Test or Live Mode account. Passed to client-side modal. | Razorpay Dashboard -> Settings -> API Keys | Open checkout page; check that Razorpay modal opens with valid key ID. |
| `RAZORPAY_KEY_SECRET` | **YES** | All | Server-only secret key used for order creation and HMAC-SHA256 signature verification. Never sent to browser. | Razorpay Dashboard -> Settings -> API Keys | Complete test payment; verify signature verification succeeds. |
| `RAZORPAY_WEBHOOK_SECRET` | **YES** | Production / Staging | Secret key configured for Razorpay Webhook endpoint. Used to verify raw request body HMAC signature. | Chosen by developer when creating webhook in Razorpay Dashboard | Webhook deliveries in Razorpay dashboard show HTTP 200 OK. |
| `GOOGLE_CLIENT_ID` | No | All | Public OAuth 2.0 Web Application client identifier for Google Sign-In. | Google Cloud Console -> APIs & Services -> Credentials | Click "Sign in with Google"; Google authorization page opens. |
| `GOOGLE_CLIENT_SECRET` | **YES** | All | Server-only secret key used to exchange Google authorization codes for identity tokens. | Google Cloud Console -> APIs & Services -> Credentials | Complete Google sign-in; verify user dashboard loads. |
| `ENABLE_MOCK_PAYMENT` | No | Dev / Test | Feature flag (`true`/`false`). When `false`, hides test simulator controls from customer checkout. | Developer configuration | Check payment options on `/checkout`; only Razorpay and COD visible. |

---

## 3. Step-by-Step Setup: Google Cloud OAuth 2.0

To enable customer sign-in with Google:

1. **Access Google Cloud Console**:
   - Navigate to [https://console.cloud.google.com/](https://console.cloud.google.com/) and sign in with your Google account.
2. **Select or Create a Project**:
   - Click the project dropdown at the top of the console and click **New Project**.
   - Project Name: `NexusMart-Store` (or your preferred name), then click **Create**.
3. **Configure OAuth Consent Screen**:
   - Go to **APIs & Services** > **OAuth consent screen**.
   - Select User Type: **External**, then click **Create**.
   - App Information:
     - **App name**: `NexusMart`
     - **User support email**: Select your email address.
     - **Developer contact information**: Enter your email address.
   - Click **Save and Continue**.
   - Scopes: Click **Add or Remove Scopes**, select `.../auth/userinfo.email`, `.../auth/userinfo.profile`, and `openid`. Click **Update**, then **Save and Continue**.
   - Test Users (while in Testing status): Add your own Google email address as an authorized test user. Click **Save and Continue**.
4. **Create Web Application OAuth Credentials**:
   - Go to **APIs & Services** > **Credentials**.
   - Click **+ Create Credentials** > **OAuth client ID**.
   - Application type: **Web application**.
   - Name: `NexusMart Web Client`.
   - **Authorized JavaScript origins**:
     - `http://127.0.0.1:5000` (for local dev)
     - `https://<YOUR_RENDER_APP_NAME>.onrender.com` (for production)
   - **Authorized redirect URIs** (*Crucial: must match exactly*):
     - `http://127.0.0.1:5000/auth/google/callback` (for local dev)
     - `https://<YOUR_RENDER_APP_NAME>.onrender.com/auth/google/callback` (for production)
   - Click **Create**.
5. **Record Credentials**:
   - Copy the **Client ID** into `GOOGLE_CLIENT_ID`.
   - Copy the **Client Secret** into `GOOGLE_CLIENT_SECRET`.

---

## 4. Step-by-Step Setup: Razorpay Payment Gateway

To enable credit card, debit card, UPI, and NetBanking payments via Razorpay:

1. **Access Razorpay Dashboard**:
   - Sign up or log in at [https://dashboard.razorpay.com/](https://dashboard.razorpay.com/).
2. **Switch to Test Mode**:
   - Ensure the toggle in the top-right header is set to **Test Mode**.
   - *Never switch to Live Mode until you are ready to accept real payments and have submitted business verification.*
3. **Generate API Keys**:
   - Go to **Settings** > **API Keys**.
   - Click **Generate Test Key**.
   - Copy the generated **Key Id** into `RAZORPAY_KEY_ID`.
   - Copy the generated **Key Secret** into `RAZORPAY_KEY_SECRET`.
   - Note: Download or save the Key Secret immediately; it cannot be viewed again.
4. **Configure Webhook Endpoint**:
   - Go to **Settings** > **Webhooks**.
   - Click **+ Add New Webhook**.
   - Webhook URL: `https://<YOUR_DEPLOYED_DOMAIN>/webhooks/razorpay`
   - Secret: Choose a strong random string (e.g. `whsec_nexusmart_2026`) and paste into `RAZORPAY_WEBHOOK_SECRET`.
   - Active Events:
     - `payment.captured`
     - `payment.failed`
     - `order.paid`
   - Click **Create Webhook**.

---

## 5. Step-by-Step Setup: Cloud Deployment on Render

Render is the recommended hosting platform because it offers native Python support, automated SSL certificates, zero-config Managed PostgreSQL, and direct Git redeployments.

1. **Create Managed PostgreSQL Database**:
   - Log in to [https://dashboard.render.com/](https://dashboard.render.com/).
   - Click **New +** > **PostgreSQL**.
   - Name: `nexusmart-db`
   - Database: `nexusmart`
   - User: `nexusmart_admin`
   - Region: Select closest to your customers (e.g. `Singapore` or `Frankfurt`).
   - Plan: **Free** (or Starter).
   - Click **Create Database**.
   - Once provisioned, copy the **Internal Database URL** (starts with `postgresql://`).
2. **Create Web Service**:
   - In Render Dashboard, click **New +** > **Web Service**.
   - Connect your GitHub repository containing the NexusMart code.
   - Name: `nexusmart`
   - Region: Same region as your database.
   - Branch: `main`
   - Root Directory: Leave blank (uses repository root).
   - Runtime: **Python 3**.
   - Build Command:
     ```bash
     pip install -r requirements.txt
     ```
   - Start Command:
     ```bash
     gunicorn --chdir ecommerce_practical10 --bind 0.0.0.0:$PORT --workers 2 --threads 4 wsgi:app
     ```
3. **Configure Environment Variables in Render**:
   - Go to the **Environment** tab of your new Web Service.
   - Add each variable:
     - `FLASK_ENV` = `production`
     - `FLASK_SECRET_KEY` = `<your-generated-64-char-hex-secret>`
     - `APP_BASE_URL` = `https://nexusmart.onrender.com`
     - `DATABASE_URL` = `<pasted-Internal-Database-URL-from-step-1>`
     - `RAZORPAY_KEY_ID` = `rzp_test_...`
     - `RAZORPAY_KEY_SECRET` = `...`
     - `RAZORPAY_WEBHOOK_SECRET` = `...`
     - `GOOGLE_CLIENT_ID` = `...apps.googleusercontent.com`
     - `GOOGLE_CLIENT_SECRET` = `GOCSPX-...`
     - `GOOGLE_REDIRECT_URI` = `https://nexusmart.onrender.com/auth/google/callback`
     - `ENABLE_MOCK_PAYMENT` = `false`
4. **Deploy & Verify**:
   - Click **Deploy Web Service**.
   - Monitor the **Logs** tab. The application will automatically invoke `init_db()`, create PostgreSQL tables, populate seed products, and start Gunicorn.
   - Check the deployment URL: `https://nexusmart.onrender.com/healthz`.
