<?php
/**
 * Disable WordPress's automatic canonical redirect (redirect_canonical()).
 *
 * Root cause of the persistent 301-to-http://127.0.0.1/ that was breaking
 * Railway's healthcheck: the debug logger (reeldrive-debug-mu.php) caught
 * the exact call stack --
 *   redirect_canonical -> wp_redirect -> apply_filters('wp_redirect')
 * -- fired from wp-includes/template-loader.php on every request to "/".
 *
 * redirect_canonical() builds its comparison/redirect URL using
 * $_SERVER['SERVER_NAME'] (which Apache reports WITHOUT the port when
 * UseCanonicalName is Off, Apache's default) -- not home_url()/WP_HOME.
 * So defining WP_HOME/WP_SITEURL in wp-config.php had no effect: this
 * redirect is independent of those options. It only fires when the
 * request's Host header doesn't exactly match what WordPress expects,
 * which is very likely also what's happening to Railway's own healthcheck
 * prober (it probably hits the container over an internal address, not the
 * public domain), not just our diagnostic curl.
 *
 * redirect_canonical() mainly handles pretty-permalink slug/trailing-slash
 * cleanup, which isn't essential for a WooCommerce/BalePay shop. Disabling
 * it is a standard, well-known workaround for WordPress sites behind
 * reverse proxies or health-checkers with inconsistent Host headers.
 */
remove_filter('template_redirect', 'redirect_canonical');
