#!/bin/bash
# Temporary diagnostic wrapper — prints the live Apache module state right
# before Apache actually tries to start, so it shows up in Railway's
# runtime Deploy Logs (not just the Build Logs). This is here because the
# build-time check (in Dockerfile) proves the image itself only has
# mpm_prefork enabled, yet the container still fails at startup with
# "More than one MPM loaded" — meaning something changes between build and
# run time, and we need to see the live filesystem state to find out what.

echo "=== DEBUG: mods-enabled contents ==="
ls -la /etc/apache2/mods-enabled/ 2>&1

echo "=== DEBUG: mpm-related LoadModule lines actually present ==="
grep -rn "mpm" /etc/apache2/mods-enabled/ 2>&1

echo "=== DEBUG: apache2ctl -M right now ==="
apache2ctl -M 2>&1

echo "=== DEBUG: ports.conf ==="
cat /etc/apache2/ports.conf 2>&1

echo "=== DEBUG: end, starting apache now ==="

exec apache2-foreground
