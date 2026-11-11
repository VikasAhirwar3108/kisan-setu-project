# Kisan Setu: Firebase Phone OTP + PostgreSQL patch

This patch is designed for the PostgreSQL/Neon version of Kisan Setu. It does not replace the database schema or product/order features.

## Files to replace/add in the existing GitHub repository

Replace:
- `app.py`
- `templates/login.html`
- `templates/register.html`
- `requirements.txt`

Add or replace:
- `templates/verify_otp.html` (informational fallback; OTP is completed on the login page)
- `.env.example` (documentation only; do not upload real secrets)

Do not upload a local SQLite database such as `greenbasket.db`. Keep your existing Neon `DATABASE_URL`.

## Firebase Console setup

1. Open Firebase Console and select the project.
2. Go to Authentication > Sign-in method and enable **Phone**.
3. In Authentication settings, add your production website domain (for example, your Vercel domain) under Authorized domains.
4. Check the SMS region policy and allow India (+91).
5. In Project settings > General > Your apps, create/select a Web App and copy its Web App configuration.
6. In Project settings > Service accounts, generate a private key for the Firebase Admin SDK. Keep this JSON private.

Firebase Phone Authentication uses reCAPTCHA and SMS. Test with Firebase test phone numbers during development to avoid repeated real SMS sends. Production SMS availability, quotas, and billing depend on Firebase project settings.

## Vercel environment variables

Add these in Vercel > Project > Settings > Environment Variables, for Production (and Preview if needed):

- `SECRET_KEY`: a long random secret
- `DATABASE_URL`: your existing Neon/PostgreSQL connection string
- `FIREBASE_API_KEY`
- `FIREBASE_AUTH_DOMAIN`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_STORAGE_BUCKET` (if shown in your Firebase web config)
- `FIREBASE_MESSAGING_SENDER_ID`
- `FIREBASE_APP_ID`
- `FIREBASE_SERVICE_ACCOUNT_JSON`: the complete service-account JSON on one line

Keep existing Razorpay environment variables if your project uses Razorpay.

**Never put the real Firebase service-account JSON, private key, database URL, or secret key in GitHub.** `.env.example` contains placeholders only.

After changing Vercel environment variables, redeploy the project.

## Login behavior

- Users register with their name, username, strong password, role, phone number, state, and city.
- Registration stores the phone in E.164 format (`+91XXXXXXXXXX`).
- Login sends an SMS OTP using Firebase Phone Authentication.
- The browser receives a Firebase ID token after OTP verification.
- Flask verifies the token with Firebase Admin SDK.
- Flask matches the verified phone number to the existing PostgreSQL `users.phone` record and creates the existing Flask session.
- This patch does not automatically create a new PostgreSQL user during login.

Existing users can use OTP if their `users.phone` field contains the same mobile number. Accounts with an empty, incorrect, or duplicate phone number need their phone data corrected in PostgreSQL before OTP login can work.

## Password policy

Registration requires at least 8 characters, one uppercase letter, one lowercase letter, one number, and one special character. Passwords remain hashed in PostgreSQL. Passwords are not used for OTP login.

## Local installation

```bash
pip install -r requirements.txt
python app.py
```

Set the environment variables before running. For local development, use a `.env` file locally only if you load it yourself; do not commit it.
