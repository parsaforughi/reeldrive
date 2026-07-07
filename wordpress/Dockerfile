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
