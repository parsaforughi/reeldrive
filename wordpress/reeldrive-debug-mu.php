<?php
/**
 * TEMPORARY diagnostic must-use plugin. WP_HOME/WP_SITEURL are correctly
 * defined in wp-config.php (confirmed in deploy logs) but requests to "/"
 * are still 301-redirected to http://127.0.0.1/ -- meaning something is NOT
 * building that URL from home_url()/get_option('home') (which WP_HOME would
 * have overridden), but from something else entirely (likely
 * $_SERVER['SERVER_NAME'], which Apache resolves to just the hostname
 * without port when UseCanonicalName is Off -- matching exactly what we see).
 *
 * This hooks WordPress core's `wp_redirect` filter (fired inside every
 * wp_redirect() call, from core OR any plugin) and logs the target URL plus
 * a call-stack summary to PHP's error log, which lands in Apache's stderr
 * and therefore in Railway's Deploy Logs. This will show us exactly which
 * function/plugin is issuing the redirect so we can fix the real source
 * instead of guessing. Remove this file once the real cause is found.
 */

add_filter('wp_redirect', function ($location, $status) {
    error_log('REELDRIVE_DEBUG wp_redirect -> ' . $location . ' (status ' . $status . ')');
    if (function_exists('wp_debug_backtrace_summary')) {
        error_log('REELDRIVE_DEBUG backtrace: ' . wp_debug_backtrace_summary());
    }
    return $location;
}, 1, 2);
