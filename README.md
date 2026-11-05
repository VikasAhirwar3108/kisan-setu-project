# Kisan Setu

Flask-based digital agriculture marketplace.

## Deployment (Vercel + Neon)

1. Create a Neon PostgreSQL project and copy its pooled connection string.
2. In Vercel Project Settings, add `DATABASE_URL` with that connection string for Production and Preview.
3. Add a strong random `SECRET_KEY` environment variable.
4. Optional: add `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_NAME` to provision the first admin account. Use a unique password and keep it private.
5. Add `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` only when Razorpay test/live account setup and webhook verification are ready.
6. Redeploy after setting environment variables.

The app creates its PostgreSQL tables automatically on first database request. It seeds public catalog products only; it does not create shared demo login credentials. Users can register through the app.

## Local run

Set `DATABASE_URL` to a Neon PostgreSQL connection string and `SECRET_KEY` in your shell, then run:

```bash
pip install -r requirements.txt
python app.py
```

Do not commit `.env`, database passwords, Razorpay secrets, or production credentials.
