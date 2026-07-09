<?php
/**
 * Plugin Name:  Hebrew Calendar Widget (Fixed / Secure Reference)
 * Description:  Same feature set as hebrew-calendar-vuln-fixture.php (Gregorian <-> Hebrew date
 *               conversion shortcode + AJAX lookup with a DB cache), patched: parameterized
 *               queries, output escaping, strict input validation, and nonce-checked AJAX.
 *               Intended to run side-by-side with the vulnerable fixture so a scanner/classifier
 *               can be validated on both a known-bad and a known-good sample of the same feature.
 * Version:      0.1.0-fixed
 * Author:       HAMIVTZAR security testing
 *
 * All function/hook/table names are suffixed `_fixed` and distinct from the vulnerable fixture's,
 * so both plugins can be active at once on the same isolated test install without collisions.
 */

defined( 'ABSPATH' ) || exit;

define( 'HAMIVTZAR_HC_FIXED_TABLE_VERSION', '1.0' );
define( 'HAMIVTZAR_HC_FIXED_NONCE_ACTION', 'hamivtzar_hc_fixed_lookup' );

/**
 * Creates the plugin's cache table on activation.
 */
function hamivtzar_hc_fixed_activate() {
	global $wpdb;
	$table_name      = $wpdb->prefix . 'hamivtzar_hebrew_cache_fixed';
	$charset_collate = $wpdb->get_charset_collate();

	require_once ABSPATH . 'wp-admin/includes/upgrade.php';
	dbDelta(
		"CREATE TABLE {$table_name} (
			id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
			greg_date VARCHAR(32) NOT NULL,
			hebrew_date VARCHAR(64) NOT NULL,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY  (id),
			UNIQUE KEY greg_date (greg_date)
		) {$charset_collate};"
	);
	add_option( 'hamivtzar_hc_fixed_table_version', HAMIVTZAR_HC_FIXED_TABLE_VERSION );
}
register_activation_hook( __FILE__, 'hamivtzar_hc_fixed_activate' );

/**
 * FIX: strict allowlist validation instead of trusting the raw input.
 *
 * Accepts only a real Y-m-d calendar date. Anything else (SQLi payloads,
 * markup, garbage) is rejected outright rather than being sanitized/escaped
 * after the fact -- reject-by-default is more robust than trying to strip
 * dangerous characters.
 *
 * @param mixed $date Candidate date value.
 * @return string|false The validated Y-m-d date, or false if invalid.
 */
function hamivtzar_hc_fixed_validate_date( $date ) {
	if ( ! is_string( $date ) || ! preg_match( '/^(\d{4})-(\d{2})-(\d{2})$/', $date, $m ) ) {
		return false;
	}

	$year  = (int) $m[1];
	$month = (int) $m[2];
	$day   = (int) $m[3];

	if ( ! checkdate( $month, $day, $year ) ) {
		return false;
	}

	return sprintf( '%04d-%02d-%02d', $year, $month, $day );
}

/**
 * Converts a validated Y-m-d Gregorian date string to a Hebrew calendar date string.
 *
 * @param string $greg_date Already-validated Gregorian date, format Y-m-d.
 * @return string Hebrew date, e.g. "15 Nisan 5785", or a fallback string.
 */
function hamivtzar_convert_to_hebrew_fixed( $greg_date ) {
	if ( ! function_exists( 'GregorianToJD' ) || ! function_exists( 'jdtojewish' ) ) {
		return 'ext-calendar-not-available';
	}

	list( $year, $month, $day ) = array_map( 'intval', explode( '-', $greg_date ) );

	$julian_day  = GregorianToJD( $month, $day, $year );
	$hebrew_full = jdtojewish( $julian_day, true, CAL_JEWISH_ADD_ALAFIM_GERESH | CAL_JEWISH_ADD_GERESHAYIM );

	return $hebrew_full;
}

/**
 * [hebrew_calendar_fixed date="2024-10-15"] shortcode.
 */
function hamivtzar_hc_fixed_shortcode( $atts ) {
	$atts = shortcode_atts(
		array(
			'date' => gmdate( 'Y-m-d' ),
		),
		$atts,
		'hebrew_calendar_fixed'
	);

	$date = hamivtzar_hc_fixed_validate_date( $atts['date'] );
	if ( false === $date ) {
		return '<div class="hamivtzar-hebrew-date-error">'
			. esc_html__( 'Invalid date. Expected format: YYYY-MM-DD.' )
			. '</div>';
	}

	global $wpdb;
	$table = $wpdb->prefix . 'hamivtzar_hebrew_cache_fixed';

	// FIX: parameterized query via $wpdb->prepare() -- no string concatenation
	// of request-influenced data into SQL.
	$row = $wpdb->get_row(
		$wpdb->prepare( "SELECT hebrew_date FROM {$table} WHERE greg_date = %s", $date )
	);

	if ( $row ) {
		$hebrew = $row->hebrew_date;
	} else {
		$hebrew = hamivtzar_convert_to_hebrew_fixed( $date );

		// FIX: parameterized INSERT.
		$wpdb->query(
			$wpdb->prepare(
				"INSERT INTO {$table} (greg_date, hebrew_date) VALUES (%s, %s)",
				$date,
				$hebrew
			)
		);
	}

	// FIX: escape all dynamic output.
	return sprintf(
		'<div class="hamivtzar-hebrew-date" data-nonce="%s">%s &rarr; %s</div>',
		esc_attr( wp_create_nonce( HAMIVTZAR_HC_FIXED_NONCE_ACTION ) ),
		esc_html( $date ),
		esc_html( $hebrew )
	);
}
add_shortcode( 'hebrew_calendar_fixed', 'hamivtzar_hc_fixed_shortcode' );

/**
 * AJAX endpoint for looking up cached conversions by date prefix.
 *
 * Left reachable to both logged-in and logged-out users (read-only lookup
 * of already-cached, non-sensitive data is the intended public feature),
 * but every other control from the vulnerable fixture is patched: a nonce
 * is required, input is strictly validated, the query is parameterized,
 * and the response is structured JSON rather than raw echoed HTML.
 */
function hamivtzar_hc_fixed_ajax_lookup() {
	// FIX: require a valid nonce tied to this specific action, so the
	// endpoint can't be driven cross-site or by a generic scripted client
	// that never rendered the shortcode.
	check_ajax_referer( HAMIVTZAR_HC_FIXED_NONCE_ACTION, 'nonce' );

	$raw_date = isset( $_REQUEST['date'] ) ? wp_unslash( $_REQUEST['date'] ) : '';

	// FIX: strict allowlist on the prefix filter -- digits and dashes only,
	// capped to the length of a Y-m-d date. Anything else is rejected
	// instead of being concatenated into a query.
	if ( ! is_string( $raw_date ) || ! preg_match( '/^[0-9\-]{0,10}$/', $raw_date ) ) {
		wp_send_json_error( array( 'message' => __( 'Invalid date filter.' ) ), 400 );
	}

	global $wpdb;
	$table = $wpdb->prefix . 'hamivtzar_hebrew_cache_fixed';

	// FIX: escape LIKE wildcards in the (already-validated) input, then pass
	// the whole pattern through $wpdb->prepare() as a single %s placeholder.
	$like_pattern = $wpdb->esc_like( $raw_date ) . '%';
	$results      = $wpdb->get_results(
		$wpdb->prepare( "SELECT greg_date, hebrew_date FROM {$table} WHERE greg_date LIKE %s", $like_pattern )
	);

	// FIX: return structured, escaped JSON instead of an unescaped print_r()
	// HTML dump -- wp_send_json() sets the correct content type and encodes
	// values safely; esc_html() here additionally guards the cached string
	// fields themselves.
	$safe_results = array_map(
		static function ( $row ) {
			return array(
				'greg_date'   => esc_html( $row->greg_date ),
				'hebrew_date' => esc_html( $row->hebrew_date ),
			);
		},
		$results
	);

	wp_send_json_success( $safe_results );
}
add_action( 'wp_ajax_hamivtzar_hebrew_lookup_fixed', 'hamivtzar_hc_fixed_ajax_lookup' );
add_action( 'wp_ajax_nopriv_hamivtzar_hebrew_lookup_fixed', 'hamivtzar_hc_fixed_ajax_lookup' );
