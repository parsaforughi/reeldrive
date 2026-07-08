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

echo "=== starting apache now ==="
exec apache2-foreground
