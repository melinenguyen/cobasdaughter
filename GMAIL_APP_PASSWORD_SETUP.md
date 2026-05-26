# Gmail Setup — CoBa's Daughter Daily Brief

This takes **5 minutes**. No coding. No Google Cloud. Just copy and paste.

After doing this once, you'll get the daily brief email automatically every morning at **9 AM**.

---

## Step 1 — Turn on 2-Step Verification

> Skip this step if you already use Google Authenticator or get texts when you log in.

1. Open this link in your browser:
   **[myaccount.google.com/security](https://myaccount.google.com/security)**
   *(sign in as `meline.nguyen@lixibox.com`)*

2. Scroll down to **"How you sign in to Google"**

3. Click **2-Step Verification** → follow the steps to turn it on

---

## Step 2 — Create an App Password

1. Open this link:
   **[myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)**

2. In the box that says **"App name"**, type:
   ```
   CoBa Brief
   ```

3. Click **Create**

4. Google will show you a **16-letter password** like this:
   ```
   abcd efgh ijkl mnop
   ```
   **Copy it now** — you only see it once.

> If you don't see the App Passwords page, ask your IT admin to enable it for your Google Workspace account.

---

## Step 3 — Add It to Your `.env` File

Open the file `.env` in the project folder (create it if it doesn't exist) and add this line:

```
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
```

Replace `abcd efgh ijkl mnop` with the password you just copied. Spaces are fine — keep them.

---

## Step 4 — Test It

Run this in your terminal to send a test email right now:

```bash
python3 scripts/daily_brief.py
```

You should see:
```
[daily_brief] Starting for Tuesday, May 27, 2026
[daily_brief] Brief ready (1423 chars)
[daily_brief] Posting to Slack…
[daily_brief] Email sent.
[daily_brief] Done.
```

Check your inbox at `meline.nguyen@lixibox.com` — the email should arrive within a minute.

---

## That's it!

The scheduler sends the brief automatically every day at **9:02 AM GMT+7**.
No further steps needed.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `GMAIL_APP_PASSWORD not set` | Check your `.env` file is in the project root folder and has no typos |
| `SMTPAuthenticationError` | The password is wrong — go back to Step 2 and create a new one |
| `App Passwords page not available` | Ask your IT admin to allow App Passwords for your Workspace |
| Email goes to spam | Add `meline.nguyen@lixibox.com` to your own contacts |
