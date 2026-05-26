# Privacy Policy — PhotoOrganizer

> Effective date : 2026-05-19. Version : 1.0.
> Contact : manugrolleau48@gmail.com.

This document explains exactly what data PhotoOrganizer handles, why, and what it does **not** do.

Short version (TL;DR) :

- PhotoOrganizer is a **local-only** desktop application. **Your photos never leave your computer.**
- We do not run any telemetry, analytics, or tracking.
- The only outbound network request, if you enable it, is to OpenStreetMap Nominatim for reverse geocoding (turning GPS coordinates into place names). It sends `(latitude, longitude)` only, never your photos.
- For the **Pro edition**, your email address is processed by our payment provider (Lemon Squeezy) and by us for license issuance and update notices. Nothing else.

---

## 1. Free / Open-Source edition ("Core")

The free desktop application :

- Runs **100 % locally** on your computer.
- Reads photo files from folders you explicitly select.
- Writes organized copies (or moves files) within folders you explicitly select.
- Stores small SQLite caches in `%LOCALAPPDATA%\PhotoOrganizer\` to speed up repeated scans.
- Writes log files in `%LOCALAPPDATA%\PhotoOrganizer\logs\`.

**No data of any kind is sent to us or to any third party**, with one optional exception below.

### 1.1 Optional : reverse geocoding via OpenStreetMap

If you keep the *"Geocoding enabled"* setting ON (default), and you organize photos that contain GPS metadata, the application sends the `(latitude, longitude)` pair of each unique location to <https://nominatim.openstreetmap.org/reverse> to obtain a human-readable place name (used as folder name).

- **What is sent** : `latitude`, `longitude`, a generic `User-Agent: PhotoOrganizer/2.x` header.
- **What is NOT sent** : your photos, your folder names, your email, any other personal data.
- **How to disable** : open the *Settings* tab → uncheck *"Geocoding enabled"*. The application will use coordinates as folder names instead.

OpenStreetMap is operated by the OpenStreetMap Foundation. Their privacy policy : <https://wiki.osmfoundation.org/wiki/Privacy_Policy>.

### 1.2 Logs

Application logs are written locally in `%LOCALAPPDATA%\PhotoOrganizer\logs\photoorganizer.log`. They contain file paths (the same that you see in the UI) and error messages. **They are never transmitted.** Delete them at any time.

---

## 2. Pro edition

The Pro edition adds two modules (batch CLI, watch-folder scheduler). These modules operate locally exactly like the Core edition.

The **only** difference, from a privacy perspective, is the license activation process :

### 2.1 Purchase

You purchase a license via **Lemon Squeezy** (<https://www.lemonsqueezy.com>), which acts as the Merchant of Record. Their privacy policy : <https://www.lemonsqueezy.com/privacy>.

Lemon Squeezy collects whatever they need for payment processing and EU VAT compliance (typically : your email, billing address, payment method via Stripe or PayPal). We do not see your payment method or billing address.

### 2.2 What we receive and why

When a purchase completes, Lemon Squeezy sends us a webhook containing :

- Your **email address**.
- The **edition purchased** (Personal / Studio / Lifetime).
- The **order ID** and **timestamp**.

We use this strictly for two purposes :

1. **Generate your license key** (a signed string, locally validated, no server contact required).
2. **Send you your license key by email** and, occasionally, update or security notices regarding the Pro edition.

We do not :

- Sell, rent, or share your email with anyone.
- Send marketing emails unrelated to the product.
- Profile you, track your behaviour, or analyze your usage.

### 2.3 License validation — fully offline

Your license key is **validated locally** on your computer by signature verification. **No license server is ever contacted.** You can use the Pro edition completely offline.

### 2.4 Your rights (GDPR)

If you are in the European Union, you have the following rights regarding the email we hold :

- **Access** : request a copy of the data we hold about you.
- **Rectification** : ask us to correct inaccurate data.
- **Erasure** : ask us to delete your email from our records (this will revoke your future update notices but does **not** invalidate your already-purchased license, which works offline).
- **Portability** : request your data in a structured format.
- **Objection / withdraw consent** : opt out of update notices at any time.

To exercise any of these rights, email <manugrolleau48@gmail.com>. We will respond within 30 days as required by GDPR.

For complaints, you can contact the French data protection authority (CNIL) : <https://www.cnil.fr>.

---

## 3. Data retention

| Data | Where | Retention |
|---|---|---|
| Your photos | Your computer (we never see them) | You decide |
| Local cache and logs | `%LOCALAPPDATA%\PhotoOrganizer\` | You decide (delete the folder anytime) |
| (Pro) email + license issuance record | Our records | Until you request deletion, or 7 years for accounting purposes if you purchased a license |
| (Pro) Lemon Squeezy payment data | Lemon Squeezy | Governed by their policy |

---

## 4. Cookies, tracking, ads

PhotoOrganizer is a desktop application. There are **no cookies, no trackers, no ads** anywhere in the application.

This document, when hosted on our website, may be served by a static file host (GitHub Pages or similar) and is subject to that host's standard server logs. We do not run any analytics on documentation pages.

---

## 5. Changes to this policy

If we change this policy in a way that materially affects your rights, we will :

- Update the *"Effective date"* at the top of this document.
- For Pro license holders, send a one-time email notice describing the change.

You can always find the latest version at : <https://github.com/Kiriiaq/PhotoOrganizer/blob/main/docs/PRIVACY.md>.

---

## 6. Contact

For any privacy-related question :

- **Email** : manugrolleau48@gmail.com
- **Subject line** : `[PhotoOrganizer Privacy] <your question>`
- **Response time target** : 30 days (GDPR maximum), usually much faster.
