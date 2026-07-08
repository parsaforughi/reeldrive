#!/bin/bash
# Runtime fixes + diagnostics for the Railway WordPress deployment.
#
# Everything printed in the first fraction of a second of container start
# seems to get dropped by Railway's log shipper (confirmed across several
# deploys: the same echo statements show up in some runs and not others,
# always the ones right at the top). So: do all silent fixes first, THEN
# sleep briefly to let the log pipe attach, THEN print diagnostics -- the
# later "listening sockets"/curl section below has shown up reliably in
# every single deploy so far, which is the pattern this follows.

# --- Fix 1: MPM conflict -----------------------------------------------
# Build-time image has only mpm_prefork enabled, but mpm_event.load/.conf
# reappear in /etc/apache2/mods-enabled by container start (cause unknown,
# likely Railway platform init). Redo the fix unconditionally every start.
rm -f /etc/apache2/mods-enabled/mpm_event.load /etc/apache2/mods-enabled/mpm_event.conf
rm -f /etc/apache2/mods-enabled/mpm_worker.load /etc/apache2/mods-enabled/mpm_worker.conf
ln -sf ../mods-available/mpm_prefork.load /etc/apache2/mods-enabled/mpm_prefork.load
ln -sf ../mods-available/mpm_prefork.conf /etc/apache2/mods-enabled/mpm_prefork.conf

# --- Fix 2: siteurl/home stuck on 127.0.0.1 -----------------------------
# WordPress redirects "/" to http://127.0.0.1/ (port stripped). Pin
# WP_HOME/WP_SITEURL constants in wp-config.php (they override the DB
# value), idempotent via a marker comment.
php /usr/local/bin/fix-siteurl.php >/tmp/wpfix.log 2>&1
WPFIX_EXIT=$?

# --- Fix 3 (diagnostic): install debug mu-plugin ------------------------
# WP_HOME/WP_SITEURL are confirmed defined already, yet the redirect to
# 127.0.0.1 persists -- so something isn't using home_url() at all. This
# must-use plugin logs every wp_redirect() call + backtrace to a file.
mkdir -p /var/www/html/wp-content/mu-plugins
cp /usr/local/bin/reeldrive-debug-mu.php /var/www/html/wp-content/mu-plugins/reeldrive-debug-mu.php
rm -f /var/www/html/reeldrive-debug.log

# --- Fix 3b (the real fix): disable redirect_canonical() ----------------
# The debug logger caught it: redirect_canonical() (WP core) is the one
# calling wp_redirect() to http://127.0.0.1/, built from
# $_SERVER['SERVER_NAME'] (port-less), independent of WP_HOME/WP_SITEURL.
# This fires whenever the Host header doesn't exactly match -- including,
# very likely, Railway's own healthcheck prober. Disable it.
cp /usr/local/bin/disable-canonical-redirect.php /var/www/html/wp-content/mu-plugins/disable-canonical-redirect.php

# --- Fix 4: strip any page/object cache serving a stale response --------
# WP_HOME fix had zero effect AND the redirect logger never fired even
# once -- both point to a caching plugin replaying a pre-saved response
# (headers baked in from before the real domain was configured) without
# WordPress (or our mu-plugin) ever running for that request. Remove any
# cache drop-ins/static cache directory and any cache-plugin rewrite block
# in .htaccess, unconditionally, every start.
rm -f /var/www/html/wp-content/advanced-cache.php
rm -f /var/www/html/wp-content/object-cache.php
rm -rf /var/www/html/wp-content/cache
if [ -f /var/www/html/.htaccess ]; then
    sed -i '/# BEGIN WPSuperCache/,/# END WPSuperCache/d' /var/www/html/.htaccess
    sed -i '/# BEGIN W3TC/,/# END W3TC/d' /var/www/html/.htaccess
fi

# Let Railway's log shipper catch up before we print anything.
sleep 2

echo "=== wp-config.php fix (exit $WPFIX_EXIT) ==="
cat /tmp/wpfix.log
grep -n "WP_HOME\|WP_SITEURL" /var/www/html/wp-config.php 2>&1

echo "=== mu-plugin installed? ==="
ls -la /var/www/html/wp-content/mu-plugins/ 2>&1

echo "=== cache drop-ins remaining (should be empty) ==="
ls -la /var/www/html/wp-content/advanced-cache.php /var/www/html/wp-content/object-cache.php 2>&1

echo "=== mods-enabled (mpm) ==="
ls -la /etc/apache2/mods-enabled/ 2>&1 | grep -i mpm

# Start Apache in the background so we can probe it locally before handing
# off to the real foreground process.
apache2ctl start 2>&1
sleep 3

echo "=== local curl to 127.0.0.1:8080/ (Host: 127.0.0.1:8080, mismatched on purpose) ==="
curl -sv -o /tmp/curl-body.txt http://127.0.0.1:8080/ 2>&1
echo "--- body (first 20 lines) ---"
head -n 20 /tmp/curl-body.txt 2>&1

echo "=== local curl to 127.0.0.1:8080/ (Host: shopreeldrive.up.railway.app, the real domain) ==="
curl -sv -o /tmp/curl-body2.txt -H "Host: shopreeldrive.up.railway.app" http://127.0.0.1:8080/ 2>&1
echo "--- body (first 20 lines) ---"
head -n 20 /tmp/curl-body2.txt 2>&1

echo "=== reeldrive-debug.log (wp_redirect calls, should be empty/gone now) ==="
cat /var/www/html/reeldrive-debug.log 2>&1 || echo "(no file -- no redirect fired, good)"

apache2ctl stop 2>&1
sleep 1

echo "=== starting apache in foreground now ==="
exec apache2-foreground
