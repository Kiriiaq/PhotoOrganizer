# Privacy Policy — PhotoOrganizer

> Effective date : 2026-05-26. Version : 2.0 (post-pivot trial+unlock).
> Contact : manugrolleau48@gmail.com.

This document explains exactly what data PhotoOrganizer handles, why, and what it does **not** do.

Short version (TL;DR) :

- PhotoOrganizer is a **local-only** desktop application. **Your photos never leave your computer.**
- We do not run any telemetry, analytics, or tracking.
- The only outbound network request, if you enable it, is to OpenStreetMap Nominatim for reverse geocoding (turning GPS coordinates into place names). It sends `(latitude, longitude)` only, never your photos.
- A **local trial counter** (10 free runs) and a **machine binding** for activated licences are stored on your computer. They never leave it.
- If you **purchase an unlock licence**, your email is processed by our payment provider (Lemon Squeezy) and by us for license issuance. Nothing else.

---

## 1. The application — what stays on your computer

The application :

- Runs **100 % locally**.
- Reads photo files from folders you explicitly select.
- Writes organized copies (or moves files) within folders you explicitly select.
- Stores small SQLite caches in `%LOCALAPPDATA%\PhotoOrganizer\` to speed up repeated scans.
- Writes log files in `%LOCALAPPDATA%\PhotoOrganizer\logs\`.
- Stores a **trial counter** (HMAC-signed JSON) in `%LOCALAPPDATA%\PhotoOrganizer\usage.dat`. See §2.
- Stores a **licence binding** (HMAC-signed JSON) in `%LOCALAPPDATA%\PhotoOrganizer\license.dat` once you activate. See §3.

**No data of any kind is sent to us or to any third party**, with one optional exception (geocoding, §1.1) and one purchase-time interaction (Lemon Squeezy, §3.1).

### 1.1 Optional : reverse geocoding via OpenStreetMap

If you keep the *"Geocoding enabled"* setting ON (default), and you organize photos that contain GPS metadata, the application sends the `(latitude, longitude)` pair of each unique location to <https://nominatim.openstreetmap.org/reverse> to obtain a human-readable place name (used as folder name).

- **What is sent** : `latitude`, `longitude`, a generic `User-Agent: PhotoOrganizer/2.x` header.
- **What is NOT sent** : your photos, your folder names, your email, any other personal data.
- **How to disable** : open the *Settings* tab → uncheck *"Geocoding enabled"*. The application will use coordinates as folder names instead.

OpenStreetMap is operated by the OpenStreetMap Foundation. Their privacy policy : <https://wiki.osmfoundation.org/wiki/Privacy_Policy>.

### 1.2 Logs

Application logs are written locally in `%LOCALAPPDATA%\PhotoOrganizer\logs\photoorganizer.log`. They contain file paths (the same that you see in the UI) and error messages. **They are never transmitted.** Delete them at any time.

---

## 2. Trial counter (`usage.dat`)

PhotoOrganizer offers **10 free organization runs** before requiring activation. To enforce this fairly, we store a tiny counter on your computer :

- **Location** : `%LOCALAPPDATA%\PhotoOrganizer\usage.dat`
- **Content** : a JSON object containing `count`, a timestamp, and a derived machine identifier (see §2.1). Signed with HMAC-SHA256 to detect tampering.
- **Stays local** : this file is never transmitted to us or to any third party.
- **You can delete it**. Doing so resets the counter to 0. This is a deliberate trade-off — we trust users at the 10 € price point.

### 2.1 Derived machine identifier

The counter contains a SHA-256 hash of your `MachineGuid` (Windows registry) concatenated with the volume serial number of your `C:` drive. This is :

- Computed and used **only locally**.
- **Not** transmitted to us at any point.
- Used solely to detect copies of `usage.dat` between different computers.

You cannot opt out of this computation (it is required for the counter to be tamper-resistant), but the hash is purely local data.

---

## 3. Licence purchase and activation (`license.dat`)

If you choose to purchase a lifetime unlock (10 €), the following happens.

### 3.1 Purchase via Lemon Squeezy

You buy a licence on <https://photoorganizer.lemonsqueezy.com>, operated by **Lemon Squeezy** as the Merchant of Record. Their privacy policy : <https://www.lemonsqueezy.com/privacy>.

Lemon Squeezy collects whatever they need for payment processing and EU VAT compliance (typically : your email, billing address, payment method via Stripe or PayPal). We do not see your payment method or billing address.

### 3.2 What we receive and why

When a purchase completes, Lemon Squeezy sends us :

- Your **email address**.
- The **order ID** and **timestamp**.

We use this strictly for two purposes :

1. **Generate your licence key** (a signed string, locally validated, no server contact required).
2. **Send you your licence key by email** — and, occasionally, a transactional notice (security advisory, end-of-life announcement). No marketing.

We do not :

- Sell, rent, or share your email with anyone.
- Send marketing emails unrelated to the product.
- Profile you, track your behaviour, or analyze your usage.

### 3.3 Activation and machine binding

When you paste your licence key into the application :

- The key is validated **locally** by signature verification. **No server is contacted.**
- On successful validation, the application stores the licence + your local machine identifier (see §2.1) into `%LOCALAPPDATA%\PhotoOrganizer\license.dat`, signed with HMAC-SHA256.
- Subsequent launches of the application verify that the licence is still bound to the same machine. If you copy `license.dat` to another computer, it will be rejected (the binding will not match).

**One licence = one computer.** This is documented openly before purchase. If you change computer, reinstall Windows, or replace your system drive, the machine identifier changes and a new licence must be purchased (with possible commercial gestures on a case-by-case basis — see Terms of Service).

### 3.4 Your rights (GDPR)

If you are in the European Union, you have the following rights regarding the email we hold :

- **Access** : request a copy of the data we hold about you.
- **Rectification** : ask us to correct inaccurate data.
- **Erasure** : ask us to delete your email from our records (this does **not** invalidate your already-purchased licence, which is validated locally and works offline).
- **Portability** : request your data in a structured format.
- **Objection / withdraw consent** : opt out of transactional notices at any time.

To exercise any of these rights, email <manugrolleau48@gmail.com>. We will respond within 30 days as required by GDPR.

For complaints, you can contact the French data protection authority (CNIL) : <https://www.cnil.fr>.

---

## 4. Data retention

| Data | Where | Retention |
|---|---|---|
| Your photos | Your computer (we never see them) | You decide |
| Local cache, logs, `usage.dat`, `license.dat` | `%LOCALAPPDATA%\PhotoOrganizer\` | You decide (delete the folder anytime) |
| Email + licence issuance record | Our records | Until you request deletion, or 7 years for accounting purposes |
| Payment data | Lemon Squeezy | Governed by their policy |

---

## 5. Cookies, tracking, ads

PhotoOrganizer is a desktop application. There are **no cookies, no trackers, no ads** anywhere in the application.

This document, when hosted on our website, may be served by a static file host (GitHub Pages or similar) and is subject to that host's standard server logs. We do not run any analytics on documentation pages.

---

## 6. Changes to this policy

If we change this policy in a way that materially affects your rights, we will :

- Update the *"Effective date"* at the top of this document.
- For licence holders, send a one-time email notice describing the change.

You can always find the latest version at : <https://github.com/Kiriiaq/PhotoOrganizer/blob/main/docs/PRIVACY.md>.

---

## 7. Contact

For any privacy-related question :

- **Email** : manugrolleau48@gmail.com
- **Subject line** : `[PhotoOrganizer Privacy] <your question>`
- **Response time target** : 30 days (GDPR maximum), usually much faster.
