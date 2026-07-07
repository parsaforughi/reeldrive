# Custom WordPress image for the Reeldrive Pro shop (WooCommerce + BalePay).
#
# The stock Railway "WordPress + MySQL" template doesn't ship the ionCube
# Loader, which the BalePay plugin (and most rtl-theme.com plugins) require
# to run their encoded PHP. This adds it on top of the same base image
# (php8.3-apache, matching what the template was already running).
#
# Deploy on Railway: point this service's source at this GitHub repo with
# Root Directory = "wordpress" and Builder = Dockerfile. Keep the existing
# volume mounted at /var/www/html and the same WORDPRESS_DB_* variables
# pointing at the MySQL service.

FROM wordpress:php8.3-apache

# Install ionCube Loader for PHP 8.3 (linux x86-64).
# If your Railway service runs on ARM instead, swap the download URL for
# https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_aarch64.tar.gz
RUN set -eux; \
    cd /tmp; \
    curl -fsSL -o ioncube.tar.gz \
        https://downloads.ioncube.com/loader_downloads/ioncube_loaders_lin_x86-64.tar.gz; \
    tar -xzf ioncube.tar.gz; \
    PHP_EXT_DIR="$(php -r 'echo ini_get("extension_dir");')"; \
    cp ioncube/ioncube_loader_lin_8.3.so "$PHP_EXT_DIR/"; \
    { \
        echo "zend_extension=$PHP_EXT_DIR/ioncube_loader_lin_8.3.so"; \
    } > /usr/local/etc/php/conf.d/00-ioncube.ini; \
    rm -rf /tmp/ioncube*

# Your Railway service's Public Networking target port is 8080 (Railway's
# own port-mismatch fix on the stock image), but Apache defaults to 80.
# Bake the same fix into the image itself so it doesn't depend on a custom
# Railway "start command" that could reset when the source changes.
RUN sed -i 's/Listen 80/Listen 8080/' /etc/apache2/ports.conf \
    && sed -i 's/<VirtualHost \*:80>/<VirtualHost *:8080>/' \
        /etc/apache2/sites-available/000-default.conf

# The php8.3-apache base image ships with both mpm_event and mpm_prefork
# enabled, but Apache requires exactly one active MPM or it refuses to start
# with "AH00534: More than one MPM loaded." Disable the extras and ensure
# mpm_prefork (required by mod_php) is the sole active MPM.
RUN rm -f /etc/apache2/mods-enabled/mpm_event.load /etc/apache2/mods-enabled/mpm_event.conf \
          /etc/apache2/mods-enabled/mpm_worker.load /etc/apache2/mods-enabled/mpm_worker.conf \
    && ln -sf /etc/apache2/mods-available/mpm_prefork.load /etc/apache2/mods-enabled/mpm_prefork.load \
    && ln -sf /etc/apache2/mods-available/mpm_prefork.conf /etc/apache2/mods-enabled/mpm_prefork.conf

EXPOSE 8080
