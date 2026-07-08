<?php
/**
 * Force WP_HOME / WP_SITEURL to the real public Railway domain, overriding
 * whatever is stored in the database. Fixes a stale "siteurl=http://127.0.0.1"
 * value (left over from initial setup) that was making WordPress 301-redirect
 * every request to http://127.0.0.1/ — a host nothing listens on from outside
 * the container, which is why Railway's healthcheck could never get a real
 * response.
 *
 * Safe to run on every container start: it's a no-op once the constants are
 * already present.
 */

$domain = 'shopreeldrive.up.railway.app';
$configFile = '/var/www/html/wp-config.php';
$marker = 'REELDRIVE_WP_HOME_FIX';

if (!file_exists($configFile)) {
    fwrite(STDERR, "fix-siteurl.php: wp-config.php not found at $configFile, skipping\n");
    exit(0);
}

$content = file_get_contents($configFile);

if (strpos($content, $marker) !== false) {
    echo "fix-siteurl.php: already patched, skipping\n";
    exit(0);
}

$inject = <<<PHP

/* {$marker} — keep siteurl/home pinned to the real public domain regardless
 * of what's stored in the database, and trust Railway's TLS-terminating
 * proxy so WordPress knows the outward-facing request is HTTPS. */
if (!defined('WP_HOME')) {
    define('WP_HOME', 'https://{$domain}');
}
if (!defined('WP_SITEURL')) {
    define('WP_SITEURL', 'https://{$domain}');
}
if (isset(\$_SERVER['HTTP_X_FORWARDED_PROTO']) && \$_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https') {
    \$_SERVER['HTTPS'] = 'on';
}

PHP;

$stopMarker = "/* That's all, stop editing!";
if (strpos($content, $stopMarker) !== false) {
    $content = str_replace($stopMarker, $inject . $stopMarker, $content);
} else {
    $content .= $inject;
}

file_put_contents($configFile, $content);
echo "fix-siteurl.php: patched wp-config.php with WP_HOME/WP_SITEURL={$domain}\n";
