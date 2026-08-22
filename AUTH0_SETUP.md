# LunaTicK Native Sign-In Setup

LunaTicK now uses **Streamlit native OpenID Connect authentication** with **Auth0** as its non-Google identity provider. Auth0 handles account creation, email-and-password sign-in, password reset, and verification. Streamlit stores the managed identity session and restores a returning user automatically for up to 30 days.

> **Do not commit Auth0 credentials.** Add them only through Streamlit Community Cloud's **App settings → Secrets** panel.

## 1. Create the Auth0 application

Create or sign in to your Auth0 tenant, then create an application with the type **Regular Web Application**. Give it a clear internal name such as `LunaTicK Streamlit`.

In the application settings, add the following values. Replace `YOUR-STREAMLIT-APP` with the actual Community Cloud subdomain for LunaTicK.

| Auth0 setting | Value |
|---|---|
| Allowed Callback URLs | `https://YOUR-STREAMLIT-APP.streamlit.app/oauth2callback` |
| Allowed Logout URLs | `https://YOUR-STREAMLIT-APP.streamlit.app` |
| Allowed Web Origins | `https://YOUR-STREAMLIT-APP.streamlit.app` |
| Application Login URI | `https://YOUR-STREAMLIT-APP.streamlit.app` |

Copy the **Domain**, **Client ID**, and **Client Secret** from that Auth0 application.

## 2. Enable email-and-password accounts only

In **Authentication → Database**, create or enable the Auth0 database connection that uses email and password. Enable that connection for the `LunaTicK Streamlit` application.

Do not enable Google or any social connection. The Universal Login page will then offer the native LunaTicK email-and-password experience, including account creation and password recovery, without a Google dependency.

## 3. Add the Streamlit Community Cloud secrets

Open the LunaTicK deployment in Streamlit Community Cloud. Navigate to **App settings → Secrets** and paste this configuration after replacing every placeholder.

```toml
[auth]
redirect_uri = "https://YOUR-STREAMLIT-APP.streamlit.app/oauth2callback"
cookie_secret = "PASTE_A_LONG_RANDOM_PRIVATE_VALUE_HERE"

[auth.auth0]
client_id = "PASTE_THE_AUTH0_CLIENT_ID"
client_secret = "PASTE_THE_AUTH0_CLIENT_SECRET"
server_metadata_url = "https://YOUR_AUTH0_DOMAIN/.well-known/openid-configuration"
# Keep this value aligned with the enabled Auth0 database connection.
database_connection = "Username-Password-Authentication"
```

Generate the `cookie_secret` with a password manager or a cryptographic random generator. It must remain stable after deployment; changing it deliberately signs all users out.

## 4. Verify the alpha flow

After deploying the code and secrets, open LunaTicK in an incognito browser window. Select **Continue to secure sign-in**, create a new email-and-password account, and complete the provider's verification process if it asks for one. You should return to the LunaTicK home screen.

Close the tab entirely, reopen the same app URL in the same browser, and confirm that the home screen loads directly without asking for credentials. Finally, choose **Log out** in Settings, reopen the app, and confirm that the sign-in screen returns.

## 5. Verify password recovery

From LunaTicK's sign-in screen, open **Forgot your password?**, enter the account email, and select **Email password-reset link**. Auth0 sends the recovery email and hosts the new-password page; LunaTicK never receives, stores, or changes a password. A signed-in user can request the same Auth0 reset link in **Settings → Password & Sign-in**. For privacy, the app shows a generic success message rather than revealing whether an email address has an account.

## Notes for the current alpha

Native sign-in is durable because Streamlit manages the identity cookie rather than LunaTicK writing a custom cookie from a third-party component. LunaTicK maps the OIDC provider's immutable `sub` claim to its existing `user_hash`, keeping journals, cards, and community records associated with the same person while the current SQLite-based alpha database is available.

The existing local username/password accounts are intentionally retired by this migration. There is no safe automatic account-linking path because the legacy accounts do not hold verified email identities. Test accounts can simply be recreated through the Auth0 sign-in screen. Durable user-profile storage remains the next infrastructure task: move local SQLite data to Supabase/Postgres before opening the alpha broadly.
