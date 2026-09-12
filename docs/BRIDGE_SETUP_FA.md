# Instagram DMs to Telegram (bridge)

The bot reads DMs for `@reeldrivebot` through the Instagram web API (`www.instagram.com`). It uses a browser cookie and does not need a proxy for error `467`.

One variable:

```
INSTAGRAM_BRIDGE_SESSION_ID=<sessionid cookie value>
```

In the browser: log in as `reeldrivebot` → DevTools → Application → Cookies → `instagram.com` → `sessionid`. `%3A` or `:` both work.

After restart, the log should show `Bridge IG ready (web DM API)`.

## If DMs do not arrive

The session expired or was revoked. Copy a fresh `sessionid`:

1. Log in again as `reeldrivebot` in the browser
2. Copy the new `sessionid` cookie
3. Update `INSTAGRAM_BRIDGE_SESSION_ID` and restart

The log should again show `Bridge IG ready (web DM API)`.

## If you see `TelegramConflictError`

The bot is polling in two places (for example a host plus your Mac). Stop the extra process with Ctrl+C. Only one instance may poll.

Not required: password, csrftoken, mid, proxy — only `sessionid`.

## Local test on a Mac

```bash
echo 'SESSIONID_HERE' > scripts/.bridge_sessionid
./scripts/ig_export_from_sessionid_file.sh
```
