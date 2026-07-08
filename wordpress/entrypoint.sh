#!/bin/bash
# Production entrypoint for the Reeldrive Pro shop (WordPress + WooCommerce +
# BalePay) on Railway. Three fixes are applied on every container start,
# then Apache runs in the foreground as PID 1.

# 1) Force exactly one MPM enabled (mod_php requires mpm_prefork). The
#    build-time image has only mpm_prefork, but mpm_event.load/.conf
#    reappear in /etc/apache2/mods-enabled by the time the container
#    actually starts (cause not fully explained -- likely something in
#    Railway's own platform-level container init). Redo the fix here,
#    unconditionally, every time, immediately before Apache starts.
rm -f /etc/apache2/mods-enabled/mpm_event.load /etc/apache2/mods-enabled/mpm_event.conf
rm -f /etc/apache2/mods-enabled/mpm_worker.load /etc/apache2/mods-enabled/mpm_worker.conf
ln -sf ../mods-available/mpm_prefork.load /etc/apache2/mods-enabled/mpm_prefork.load
ln -sf ../mods-available/mpm_prefork.conf /etc/apache2/mods-enabled/mpm_prefork.conf

# 2) Pin WP_HOME/WP_SITEURL to the real public domain in wp-config.php
#    (these constants override whatever's stored in the database). Fixes a
#    stale siteurl/home value left over from initial setup.
php /usr/local/bin/fix-siteurl.php || true

# 3) Disable WordPress's redirect_canonical(). It builds its
#    comparison/redirect URL from $_SERVER['SERVER_NAME'] (which Apache
#    reports without the port, UseCanonicalName being Off by default) --
#    not home_url()/WP_HOME -- and fires a 301 whenever the request's Host
#    header doesn't exactly match, including Railway's own healthcheck
#    prober hitting the container over an internal address rather than the
#    public domain. This was the actual cause of the healthcheck never
#    passing. redirect_canonical() mainly handles pretty-permalink
#    slug/trailing-slash cleanup, non-essential for this shop.
mkdir -p /var/www/html/wp-content/mu-plugins
cp /usr/local/bin/disable-canonical-redirect.php /var/www/html/wp-content/mu-plugins/disable-canonical-redirect.php

exec apache2-foreground
