#!/bin/bash
# Runtime MPM fix — not just diagnostics anymore.
#
# Proven by the last debug run: the build-time image has ONLY mpm_prefork
# enabled (verified via `apache2ctl -M` right after the a2dismod/a2enmod RUN
# step in the Dockerfile), but at container *start*, /etc/apache2/mods-enabled
# has BOTH mpm_event.load/.conf AND mpm_prefork.load/.conf present again,
# which makes Apache refuse to start with:
#   AH00534: apache2: Configuration error: More than one MPM loaded.
#
# Whatever restores mpm_event between build and run (Railway's own platform
# init, a stale cached layer being deployed, something on the /var/www/html
# volume's init scripts, etc.) — we no longer need to know. Instead of
# relying on the build-time fix surviving untouched, redo it here, every
# single time, in the seconds right before Apache actually starts. This is
# idempotent and safe to run unconditionally.

echo "=== mods-enabled BEFORE runtime fix ==="
ls -la /etc/apache2/mods-enabled/ 2>&1 | grep -i mpm

# Force exactly one MPM: remove any event/worker symlinks, (re)create prefork.
rm -f /etc/apache2/mods-enabled/mpm_event.load /etc/apache2/mods-enabled/mpm_event.conf
rm -f /etc/apache2/mods-enabled/mpm_worker.load /etc/apache2/mods-enabled/mpm_worker.conf
ln -sf ../mods-available/mpm_prefork.load /etc/apache2/mods-enabled/mpm_prefork.load
ln -sf ../mods-available/mpm_prefork.conf /etc/apache2/mods-enabled/mpm_prefork.conf

echo "=== mods-enabled AFTER runtime fix ==="
ls -la /etc/apache2/mods-enabled/ 2>&1 | grep -i mpm

echo "=== apache2ctl -M after fix ==="
apache2ctl -M 2>&1

echo "=== ports.conf ==="
cat /etc/apache2/ports.conf 2>&1

echo "=== VirtualHost line in 000-default.conf ==="
grep -i "VirtualHost" /etc/apache2/sites-enabled/*.conf 2>&1

# Last deploy's local curl showed WordPress 301-redirecting "/" straight to
# http://127.0.0.1/ (port stripped) — the DB's siteurl/home option is stuck
# on a stale 127.0.0.1 value from initial setup, so nothing outside the
# container can ever get past that redirect. Pin WP_HOME/WP_SITEURL to the
# real public domain (constants override the DB value), idempotent.
echo "=== fixing wp-config.php siteurl/home ==="
php /usr/local/bin/fix-siteurl.php 2>&1

# MPM conflict is fixed now (confirmed clean start), but the healthcheck to
# "/" still times out ("service unavailable") even though Railway's target
# port is correctly set to 8080. Start Apache in the background first so we
# can actually probe it locally and see what a real request gets back
# (wrong port? WordPress/DB error? nothing listening at all?) before handing
# off to the real foreground process.
apache2ctl start 2>&1
sleep 3

echo "=== listening sockets ==="
(ss -ltnp 2>&1 || netstat -ltnp 2>&1 || cat /proc/net/tcp 2>&1)

echo "=== local curl to 127.0.0.1:8080/ ==="
curl -sv -o /tmp/curl-body.txt http://127.0.0.1:8080/ 2>&1
echo "--- body (first 40 lines) ---"
head -n 40 /tmp/curl-body.txt 2>&1

apache2ctl stop 2>&1
sleep 1

echo "=== starting apache in foreground now ==="
exec apache2-foreground
