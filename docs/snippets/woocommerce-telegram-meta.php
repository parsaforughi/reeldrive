<?php
/**
 * Reeldrive Pro — capture telegram_id/days from the checkout URL and store
 * them as WooCommerce order meta, so the Reeldrive dashboard webhook
 * (/api/webhook/woocommerce) can read them and activate Pro for the right
 * Telegram user.
 *
 * Install: paste this whole file's contents into the "Code Snippets" plugin
 * (Add New -> PHP snippet -> paste -> Save and Activate), or into your child
 * theme's functions.php. Do not edit a parent/non-child theme's functions.php
 * directly - it gets wiped on theme updates.
 *
 * Expects checkout links shaped like:
 *   https://your-shop.example.com/checkout/?add-to-cart=123&quantity=1&telegram_id=456&days=30
 * (this is exactly what bot/services/pricing.py's woocommerce_checkout_url()
 * builds).
 */

if (!defined('ABSPATH')) {
    exit; // no direct access
}

// 1) Stash telegram_id/days from the URL into the WC session as soon as we
//    see them, so they survive the redirect/POST through checkout.
add_action('wp_loaded', function () {
    if (!function_exists('WC') || !WC()->session) {
        return;
    }
    if (isset($_GET['telegram_id'])) {
        WC()->session->set(
            'reeldrive_telegram_id',
            sanitize_text_field(wp_unslash($_GET['telegram_id']))
        );
    }
    if (isset($_GET['days'])) {
        WC()->session->set(
            'reeldrive_days',
            sanitize_text_field(wp_unslash($_GET['days']))
        );
    }
});

// 2) When the order is created at checkout, copy the session values onto it
//    as public order meta (no leading underscore, so it's visible in the
//    REST API / webhook payload's meta_data array).
add_action('woocommerce_checkout_create_order', function ($order, $data) {
    if (!function_exists('WC') || !WC()->session) {
        return;
    }
    $telegram_id = WC()->session->get('reeldrive_telegram_id');
    $days = WC()->session->get('reeldrive_days');
    if ($telegram_id) {
        $order->update_meta_data('telegram_id', $telegram_id);
    }
    if ($days) {
        $order->update_meta_data('days', $days);
    }
}, 10, 2);

// 3) Belt-and-suspenders: also cover orders created via other flows
//    (payment blocks, REST checkout, etc.) that might skip hook #2.
add_action('woocommerce_new_order', function ($order_id) {
    if (!function_exists('WC') || !WC()->session) {
        return;
    }
    $order = wc_get_order($order_id);
    if (!$order) {
        return;
    }
    $changed = false;
    if (!$order->get_meta('telegram_id')) {
        $telegram_id = WC()->session->get('reeldrive_telegram_id');
        if ($telegram_id) {
            $order->update_meta_data('telegram_id', $telegram_id);
            $changed = true;
        }
    }
    if (!$order->get_meta('days')) {
        $days = WC()->session->get('reeldrive_days');
        if ($days) {
            $order->update_meta_data('days', $days);
            $changed = true;
        }
    }
    if ($changed) {
        $order->save();
    }
});
