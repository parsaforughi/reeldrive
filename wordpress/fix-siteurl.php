<?php
/**
 * Force WP_HOME / WP_SITEURL to the real public Railway domain, overriding
 * whatever is stored in the database. Fixes a stale siteurl value (left
 * over from initial setup, or from a previous Railway service/domain) that
 * makes WordPress redirect everything to a host nothing listens on.
 *
 * Self-healing: if a previous run already injected this block for a
 * DIFFERENT (now-wrong) domain -- e.g. the Railway service was deleted and
 * recreated with a new generated domain -- this removes the stale block
 * and re-injects it with the current $domain, instead of silently skipping
 * because "a block already exists". Safe to run on every container start.
 */

$domain = 'reeldrive-production.up.railway.app';
$configFile = '/var/www/html/wp-config.php';
$markerStart = '/* REELDRIVE_WP_HOME_FIX';
$markerEnd = '/* REELDRIVE_WP_HOME_FIX_END */';

if (!file_exists($configFile)) {
    fwrite(STDERR, "fix-siteurl.php: wp-config.php not found at $configFile, skipping\n");
    exit(0);
}

$content = file_get_contents($configFile);

// Strip any previously-injected block (regardless of which domain it had),
// so we never end up with a stale copy fighting the current one.
$startPos = strpos($content, $markerStart);
if ($startPos !== false) {
    $endPos = strpos($content, $markerEnd, $startPos);
    if ($endPos !== false) {
        $endPos += strlen($markerEnd);
        $content = substr($content, 0, $startPos) . substr($content, $endPos);
    }
}

$inject = <<<PHP

{$markerStart} — keep siteurl/home pinned to the real public domain
 * regardless of what's stored in the database, and trust Railway's
 * TLS-terminating proxy so WordPress knows the outward-facing request is
 * HTTPS. Re-generated on every container start by fix-siteurl.php -- do
 * not hand-edit, it will be replaced. */
if (!defined('WP_HOME')) {
    define('WP_HOME', 'https://{$domain}');
}
if (!defined('WP_SITEURL')) {
    define('WP_SITEURL', 'https://{$domain}');
}
if (isset(\$_SERVER['HTTP_X_FORWARDED_PROTO']) && \$_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https') {
    \$_SERVER['HTTPS'] = 'on';
}
{$markerEnd}

PHP;

$stopMarker = "/* That's all, stop editing!";
if (strpos($content, $stopMarker) !== false) {
    $content = str_replace($stopMarker, $inject . $stopMarker, $content);
} else {
    $content .= $inject;
}

file_put_contents($configFile, $content);
echo "fix-siteurl.php: patched wp-config.php with WP_HOME/WP_SITEURL={$domain}\n";
