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

# Force exactly one MPM enabled. Something in this Railway environment
# (leftover from an earlier manual fix, or the persistent volume) ends up
# with both mpm_prefork and mpm_event loaded, which Apache refuses to start
# with ("AH00534: More than one MPM loaded"). mod_php requires prefork, so
# explicitly disable the others and enable prefork at build time — this is
# baked into the image layer, independent of anything on the volume.
RUN a2dismod mpm_event 2>/dev/null; \
    a2dismod mpm_worker 2>/dev/null; \
    a2enmod mpm_prefork; \
    apache2ctl -M 2>&1 | grep -i mpm

EXPOSE 8080

# The build-time a2dismod above is not enough: something between image build
# and container start (likely the persistent /var/www/html volume or a Railway
# layer) re-enables mpm_event at runtime. This wrapper removes the conflicting
# MPM symlinks and re-asserts mpm_prefork at the exact moment before Apache
# starts, guaranteeing only one MPM is ever loaded.
COPY docker-entrypoint-wrapper.sh /usr/local/bin/docker-entrypoint-wrapper.sh
RUN chmod +x /usr/local/bin/docker-entrypoint-wrapper.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-wrapper.sh"]
