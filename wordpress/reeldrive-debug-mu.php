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
 * Writes to BOTH PHP's normal error_log() (Apache stderr -> Railway deploy
 * logs, when that reaches it) AND a plain file on the volume
 * (/var/www/html/reeldrive-debug.log), in case error_log()'s destination
 * isn't actually stderr in this image. The entrypoint script cats that file
 * out after the diagnostic curl, so we get the info even if the live log
 * stream drops or reroutes it. Remove this file once the real cause is found.
 */

add_filter('wp_redirect', function ($location, $status) {
    $line = sprintf(
        "[%s] wp_redirect -> %s (status %d)\n",
        date('Y-m-d H:i:s'),
        $location,
        $status
    );
    if (function_exists('wp_debug_backtrace_summary')) {
        $line .= 'backtrace: ' . wp_debug_backtrace_summary() . "\n";
    }

    error_log('REELDRIVE_DEBUG ' . trim($line));
    @file_put_contents('/var/www/html/reeldrive-debug.log', $line, FILE_APPEND);

    return $location;
}, 1, 2);
