"""Tests for the logistic-regression risk indicator over audit results.

Feature extraction and the synthetic dataset are pure Python and always
tested. Model fitting/scoring needs scikit-learn and is skipped if it isn't
installed, matching the pattern in test_security_classifier.py.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pacs_iso27799_audit.audit import run_audit
from pacs_iso27799_audit.risk_model import (
    FEATURE_NAMES,
    RISK_DOMAINS,
    build_dataset,
    domain_risk,
    features_from_results,
)

try:
    import sklearn  # noqa: F401
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class FeatureExtractionTests(unittest.TestCase):
    def test_risk_domains_only_include_domains_with_automated_controls(self):
        # Domain 5 (policies) and domain 8 (asset mgmt) have only manual
        # controls, so they must not appear.
        self.assertNotIn(5, RISK_DOMAINS)
        self.assertNotIn(8, RISK_DOMAINS)
        self.assertIn(9, RISK_DOMAINS)  # access control has automated controls

    def test_feature_names_match_risk_domains(self):
        self.assertEqual(len(FEATURE_NAMES), len(RISK_DOMAINS))

    def test_all_passing_config_yields_zero_risk(self):
        passing_config = {
            "access_control": {
                "admin_accounts_segregated": True,
                "shared_accounts_allowed": False,
                "rbac_enabled": True,
                "mfa_required_for_remote": True,
                "session_idle_timeout_minutes": 5,
                "password_min_length": 16,
                "instant_access_rate_limited": True,
                "instant_access_lockout_threshold": 3,
            },
            "human_resources": {"training_completion_rate_pct": 100},
            "cryptography": {"dicom_tls_enabled": True, "storage_encryption_at_rest": True},
            "operations": {
                "access_logging_enabled": True,
                "endpoint_protection_enabled": True,
                "os_patch_days_behind": 0,
                "instant_access_attempts_logged": True,
            },
            "communications": {"network_segmented": True},
            "acquisition": {"vendor_patch_sla_days": 1, "vendor_remote_access_time_limited": True},
            "business_continuity": {"backup_restore_tested_days_ago": 1},
            "compliance": {"last_risk_assessment_days_ago": 1},
        }
        results = run_audit(passing_config)
        features = features_from_results(results)
        self.assertTrue(all(f == 0.0 for f in features))

    def test_missing_data_counts_as_partial_risk(self):
        results = run_audit({})  # every automated control is missing_data
        for d in RISK_DOMAINS:
            self.assertEqual(domain_risk(results, d), 0.5)


class DatasetTests(unittest.TestCase):
    def test_synthetic_dataset_has_both_classes_and_matching_dimensions(self):
        xs, ys = build_dataset()
        self.assertEqual(set(ys), {0, 1})
        for x in xs:
            self.assertEqual(len(x), len(FEATURE_NAMES))


@unittest.skipUnless(HAS_SKLEARN, "scikit-learn not installed")
class ModelTests(unittest.TestCase):
    def test_score_returns_probability_in_range(self):
        from pacs_iso27799_audit.risk_model import score

        results = run_audit({})
        proba, model = score(results)
        self.assertGreaterEqual(proba, 0.0)
        self.assertLessEqual(proba, 1.0)
        self.assertEqual(len(model.coef_[0]), len(FEATURE_NAMES))

    def test_high_risk_synthetic_pattern_scores_higher_than_low_risk(self):
        from pacs_iso27799_audit.risk_model import score

        all_fail_config = {}  # everything missing -> partial risk everywhere
        low_results = run_audit({
            "access_control": {"rbac_enabled": True, "shared_accounts_allowed": False,
                                "mfa_required_for_remote": True, "admin_accounts_segregated": True,
                                "session_idle_timeout_minutes": 5, "password_min_length": 16,
                                "instant_access_rate_limited": True, "instant_access_lockout_threshold": 3},
            "cryptography": {"dicom_tls_enabled": True, "storage_encryption_at_rest": True},
        })
        high_proba, _ = score(run_audit(all_fail_config))
        low_proba, _ = score(low_results)
        self.assertGreaterEqual(high_proba, low_proba)


if __name__ == "__main__":
    unittest.main()
