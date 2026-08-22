# Advanced Instagram connect

This path only reads content the connected account is already allowed to see:

- Stories on a private page that accepted a Follow from the connected account
- The following list of that private page
- Public pages still go through HikerAPI
- The shared bridge session is never used for the user request

## Setup

Set the same high-entropy key on every process that runs the bot or the dashboard:

```bash
openssl rand -hex 32
```

```text
INSTAGRAM_SESSION_ENCRYPTION_KEY=<random-hex-value>
```

The key must be at least 32 characters. The command above yields 64.

Optional, to reduce Instagram Challenge on datacenter IPs:

```text
ADVANCED_INSTAGRAM_PROXY=http://user:pass@host:port
```

Advanced connect does not take a username or password. The user pastes the `sessionid` cookie from a browser already logged into Instagram into the Mini App. If Instagram rejects the session from a datacenter IP, a sticky/residential proxy is required.

Do not rotate the encryption key later. Old sessions become unreadable and users must connect again.

## Manual test

1. In the bot, run `/advancedconnect`.
2. In a browser logged into Instagram, copy only the `sessionid` cookie for `instagram.com`.
3. Open the Mini App and paste that value.
4. The test account must Follow a private page that has accepted the request.
5. In the bot, send `story private_username`.
6. Then send `following private_username`.
7. Repeat both on a public page to confirm the HikerAPI path is unchanged.
8. In the Mini App, disconnect advanced connect and retry a private command. The bot should ask to connect again.

## Security and limits

- Username, password, and 2FA are not accepted for advanced connect.
- Do not send `sessionid` in a Telegram chat. That cookie is full account access.
- `sessionid`, cookies, and device state are stored with authenticated encryption in PostgreSQL.
- Private data does not enter the shared HikerAPI cache.
- Each user has a separate client and request lock.
- An unofficial session can trigger an Instagram Challenge or a temporary limit.
- If the session expires, status becomes `reconnect_required` and the user must connect again.
- Disconnecting advanced connect deletes only Reeldrive's encrypted copy. It does not log the user's browser out of Instagram.
