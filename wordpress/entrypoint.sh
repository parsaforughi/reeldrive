#!/bin/bash
# Production entrypoint for the Reeldrive Pro shop (WordPress + WooCommerce +
# BalePay) on Railway. Our fixes are applied on every container start, then
# control hands off to the official wordpress:php8.3-apache image's own
# docker-entrypoint.sh (with "apache2-foreground" as its argument) --
# that's the script responsible for downloading WordPress core and
# generating wp-config.php from WORDPRESS_DB_* on a fresh/empty volume. We
# used to call apache2-foreground directly here, which skipped all of that
# (docker-entrypoint.sh only runs its setup logic when it recognizes the
# command it's given, e.g. "apache2-foreground" -- passing it our own
# script name instead made it a no-op), leaving WordPress never installed
# on a brand-new volume (wp-config.php missing, 403/no DirectoryIndex).

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

# 4) Standalone healthcheck file (see healthz.php) -- exists as a real file
#    on disk so WordPress's .htaccess rewrite never routes it through
#    index.php. Railway's healthcheck now targets this instead of "/", so
#    nothing inside WordPress can ever break it again.
cp /usr/local/bin/healthz.php /var/www/html/healthz.php

# Hand off to the official image's entrypoint -- it installs WordPress core
# and generates wp-config.php if missing, fixes ownership, then execs
# apache2-foreground itself. Safe to run every time: it no-ops the install
# step once wp-config.php/core files already exist on the volume.
exec docker-entrypoint.sh apache2-foreground
