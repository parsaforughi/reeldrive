<?php
/**
 * Standalone healthcheck endpoint for Railway. Deliberately does NOT load
 * WordPress at all -- it's a plain file that exists on disk, so
 * WordPress's .htaccess rewrite rule (which only routes to index.php when
 * the requested file/directory does NOT exist) never touches it. Apache
 * serves this directly. That means nothing inside WordPress -- redirects,
 * caching plugins, database issues, plugin bugs -- can ever affect the
 * healthcheck again.
 */
http_response_code(200);
header('Content-Type: text/plain');
echo 'ok';
