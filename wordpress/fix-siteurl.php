<?php
/**
 * Force WP_HOME / WP_SITEURL to the real public Railway domain, overriding
 * whatever is stored in the database. Fixes a stale siteurl value (left
 * over from initial setup, or from a previous Railway service/domain) that
 * makes WordPress redirect everything to a host nothing listens on.
 *
 * Self-healing: strips ANY previously-injected copy of this block --
 * regardless of exact format/marker version from earlier script revisions
 * -- and re-injects fresh with the current $domain on every run. This
 * matters because PHP's define() is a no-op if the constant is already
 * defined: a leftover old block (e.g. from a previous Railway domain that
 * no longer exists) would silently win over a freshly-appended correct one
 * if it weren't fully removed first.
 */

$domain = 'reeldrive-production.up.railway.app';
$configFile = '/var/www/html/wp-config.php';
$needle = 'REELDRIVE_WP_HOME_FIX';
$stopMarker = "/* That's all, stop editing!";

if (!file_exists($configFile)) {
    fwrite(STDERR, "fix-siteurl.php: wp-config.php not found at $configFile, skipping\n");
    exit(0);
}

$content = file_get_contents($configFile);

// Strip every previous occurrence of our injected block, however it was
// formatted. Each occurrence starts at the nearest preceding "/*" before
// the needle, and runs up to the next "stop editing" marker (that's always
// where we inject, in any script version).
while (($needlePos = strpos($content, $needle)) !== false) {
    $blockStart = strrpos(substr($content, 0, $needlePos), '/*');
    if ($blockStart === false) {
        $blockStart = $needlePos;
    }
    $stopPos = strpos($content, $stopMarker, $needlePos);
    if ($stopPos === false) {
        // No stop-editing marker after this point -- bail rather than risk
        // deleting the rest of the file.
        break;
    }
    $content = substr($content, 0, $blockStart) . substr($content, $stopPos);
}

$inject = <<<PHP

/* {$needle} — keep siteurl/home pinned to the real public domain
 * regardless of what's stored in the database, and trust Railway's
 * TLS-terminating proxy so WordPress knows the outward-facing request is
 * HTTPS. Re-generated on every container start by fix-siteurl.php -- do
 * not hand-edit, it will be replaced. */
define('WP_HOME', 'https://{$domain}');
define('WP_SITEURL', 'https://{$domain}');
if (isset(\$_SERVER['HTTP_X_FORWARDED_PROTO']) && \$_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https') {
    \$_SERVER['HTTPS'] = 'on';
}

PHP;

if (strpos($content, $stopMarker) !== false) {
    $content = str_replace($stopMarker, $inject . $stopMarker, $content);
} else {
    $content .= $inject;
}

file_put_contents($configFile, $content);
echo "fix-siteurl.php: patched wp-config.php with WP_HOME/WP_SITEURL={$domain}\n";
