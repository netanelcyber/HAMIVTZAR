"""Tests for the defensive malicious-code classifier.

Fully offline. Never executes analyzed source (only ``ast.parse``), never
touches real or live malicious code — only small inline Python snippets and
hand-authored synthetic feature vectors.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security_classifier.dataset import BENIGN, MALICIOUS, build_dataset
from security_classifier.features import FEATURE_NAMES, extract_features

BENIGN_SNIPPET = '''
def add(a, b):
    """Add two numbers."""
    return a + b

def greet(name):
    return f"hello {name}"
'''

SUSPICIOUS_SNIPPET = '''
import os, base64, socket

def run(payload_b64, host, port):
    payload = base64.b64decode(payload_b64)
    s = socket.socket()
    s.connect((host, port))
    os.system(payload.decode())
'''


class FeatureExtractionTests(unittest.TestCase):
    def test_benign_snippet_has_low_signal(self):
        f = extract_features(BENIGN_SNIPPET)
        self.assertEqual(f.has_eval_exec, 0)
        self.assertEqual(f.has_os_system, 0)
        self.assertEqual(f.suspicious_import_count, 0)
        self.assertEqual(f.num_functions, 2)

    def test_suspicious_snippet_trips_indicators(self):
        f = extract_features(SUSPICIOUS_SNIPPET)
        self.assertGreaterEqual(f.suspicious_import_count, 2)
        self.assertEqual(f.has_os_system, 1)
        self.assertEqual(f.has_base64_decode, 1)
        self.assertEqual(f.has_network_connect, 1)

    def test_invalid_syntax_does_not_raise(self):
        f = extract_features("def broken(:\n    pass")
        self.assertEqual(f.num_functions, 0)

    def test_re_compile_is_not_flagged_as_eval_exec(self):
        # re.compile(...) is an unrelated, harmless regex call -- it must not
        # trip the eval/exec/compile indicator just because the attribute
        # name happens to be "compile".
        f = extract_features("import re\nPATTERN = re.compile(r'[a-z]+')\n")
        self.assertEqual(f.has_eval_exec, 0)

    def test_bare_compile_call_is_flagged(self):
        f = extract_features("code = compile('1+1', '<string>', 'eval')\n")
        self.assertEqual(f.has_eval_exec, 1)

    def test_never_executes_source(self):
        # If this were executed, it would raise SystemExit / crash the test run.
        f = extract_features("import sys\nsys.exit(1)\n")
        self.assertEqual(f.num_functions, 0)  # just confirms we got past parsing safely

    def test_feature_vector_length_matches_names(self):
        f = extract_features(BENIGN_SNIPPET)
        self.assertEqual(len(f.to_vector()), len(FEATURE_NAMES))

    def test_to_dict_roundtrip(self):
        f = extract_features(SUSPICIOUS_SNIPPET)
        d = f.to_dict()
        self.assertEqual(set(d.keys()), set(FEATURE_NAMES))


class DatasetTests(unittest.TestCase):
    def test_synthetic_dataset_has_both_classes(self):
        xs, ys = build_dataset()
        self.assertGreater(len(xs), 0)
        self.assertIn(BENIGN, ys)
        self.assertIn(MALICIOUS, ys)
        self.assertEqual(len(xs), len(ys))
        self.assertTrue(all(len(x) == len(FEATURE_NAMES) for x in xs))

    def test_real_benign_directory_is_used_when_given(self):
        # Stand-in for a real, legitimately-benign Python source tree (this
        # repo's own package) so the test needs no network / external clone.
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        benign_dir = os.path.join(repo_root, "linux_docs_llm")
        xs, ys = build_dataset(benign_dir=benign_dir)
        self.assertIn(BENIGN, ys)
        self.assertGreater(ys.count(BENIGN), 3)  # several real modules in that package

    def test_empty_directory_yields_no_samples_for_that_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            xs, ys = build_dataset(benign_dir=tmp)
        self.assertNotIn(BENIGN, ys)
        self.assertIn(MALICIOUS, ys)  # malicious side still falls back to synthetic


class TrainingPipelineTests(unittest.TestCase):
    def test_train_runs_end_to_end_on_synthetic_data(self):
        try:
            import joblib  # noqa: F401
            import sklearn  # noqa: F401
        except ImportError:
            self.skipTest("scikit-learn/joblib not installed")

        from security_classifier.train import train

        with tempfile.TemporaryDirectory() as tmp:
            model_path = os.path.join(tmp, "model.joblib")
            train(benign_dir=None, malicious_dir=None, model_path=model_path)
            self.assertTrue(os.path.exists(model_path))

    def test_classify_scores_a_real_file(self):
        try:
            import joblib
            import sklearn  # noqa: F401
        except ImportError:
            self.skipTest("scikit-learn/joblib not installed")

        from security_classifier.train import train

        with tempfile.TemporaryDirectory() as tmp:
            model_path = os.path.join(tmp, "model.joblib")
            train(benign_dir=None, malicious_dir=None, model_path=model_path)

            clf = joblib.load(model_path)
            vector = extract_features(SUSPICIOUS_SNIPPET).to_vector()
            proba = clf.predict_proba([vector])[0]
            self.assertEqual(len(proba), 2)


class AnalyticsTests(unittest.TestCase):
    def test_analyze_runs_on_synthetic_data(self):
        try:
            import sklearn  # noqa: F401
        except ImportError:
            self.skipTest("scikit-learn not installed")

        import io
        from contextlib import redirect_stdout

        from security_classifier.analyze import analyze

        buf = io.StringIO()
        with redirect_stdout(buf):
            analyze(benign_dir=None, malicious_dir=None)
        output = buf.getvalue()

        self.assertIn("Cross-validated accuracy", output)
        self.assertIn("Feature importances", output)
        self.assertIn("Score statistics", output)

    def test_analyze_requires_at_least_two_samples_per_class(self):
        try:
            import sklearn  # noqa: F401
        except ImportError:
            self.skipTest("scikit-learn not installed")

        from security_classifier.analyze import analyze

        with tempfile.TemporaryDirectory() as empty_dir:
            with self.assertRaises(SystemExit):
                analyze(benign_dir=empty_dir, malicious_dir=None)


class ExplainTests(unittest.TestCase):
    """The natural-language summary layer. Forcing backend='template' keeps
    these fully offline and deterministic -- no LLM, no network required."""

    def test_template_backend_summarizes_benign_finding(self):
        from security_classifier.explain import summarize
        from security_classifier.features import extract_features

        f = extract_features(BENIGN_SNIPPET)
        summary = summarize("greet.py", f, score=0.1, backend="template")
        self.assertIn("benign", summary)
        self.assertIn("greet.py", summary)

    def test_template_backend_summarizes_malicious_finding(self):
        from security_classifier.explain import summarize
        from security_classifier.features import extract_features

        f = extract_features(SUSPICIOUS_SNIPPET)
        summary = summarize("loader.py", f, score=0.9, backend="template")
        self.assertIn("malicious", summary)
        # cites at least one concrete triggered indicator, not just the verdict
        self.assertTrue(
            any(word in summary for word in ("shell", "base64", "network", "decoding"))
        )

    def test_template_never_calls_a_model(self):
        # backend='template' must never try Ollama/llama.cpp/Claude, so this
        # must succeed even with no network and no local daemon.
        from security_classifier.explain import summarize
        from security_classifier.features import extract_features

        f = extract_features(BENIGN_SNIPPET)
        summary = summarize("x.py", f, score=0.2, backend="template", on_text=None)
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)

    def test_auto_falls_back_to_template_when_no_local_llm(self):
        from security_classifier.explain import summarize
        from security_classifier.features import extract_features

        f = extract_features(BENIGN_SNIPPET)
        # No Ollama daemon / GGUF model configured in the test environment,
        # so auto must land on the same offline template path.
        summary = summarize("x.py", f, score=0.1, backend="auto")
        self.assertIn("benign", summary)


class DynamicFeaturesTests(unittest.TestCase):
    """The dynamic-analysis trace parser. Only ever parses pre-collected JSON
    events -- nothing here executes anything, so these tests are as offline
    and safe as every other test in this suite."""

    def test_extract_dynamic_features_counts_events(self):
        from security_classifier.dynamic_features import extract_dynamic_features

        events = [
            {"type": "network_connect", "host": "10.0.0.1", "port": 4444},
            {"type": "network_connect", "host": "10.0.0.1", "port": 4444},
            {"type": "network_connect", "host": "10.0.0.2", "port": 80},
            {"type": "dns_lookup", "domain": "example.com"},
            {"type": "file_write", "path": "/tmp/scratch/out.txt"},
            {"type": "file_write", "path": "/home/user/.bashrc"},
            {"type": "subprocess", "cmd": "/bin/ls"},
        ]
        f = extract_dynamic_features(events)
        self.assertEqual(f.num_network_connections, 3)
        self.assertEqual(f.unique_remote_hosts, 2)
        self.assertEqual(f.num_dns_lookups, 1)
        self.assertEqual(f.num_files_written, 2)
        self.assertEqual(f.num_persistence_writes, 1)  # only the .bashrc write
        self.assertEqual(f.num_subprocess_spawned, 1)

    def test_empty_trace_yields_zeroed_features(self):
        from security_classifier.dynamic_features import extract_dynamic_features

        f = extract_dynamic_features([])
        self.assertEqual(f.to_vector(), [0.0] * len(f.to_vector()))

    def test_unrecognized_event_types_are_ignored(self):
        from security_classifier.dynamic_features import extract_dynamic_features

        f = extract_dynamic_features([{"type": "some_future_event", "foo": "bar"}])
        self.assertEqual(sum(f.to_vector()), 0.0)

    def test_load_trace_skips_blank_and_malformed_lines(self):
        from security_classifier.dynamic_features import load_trace

        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write('{"type": "dns_lookup", "domain": "a.com"}\n')
            fh.write("\n")
            fh.write("not json at all\n")
            fh.write('{"type": "subprocess", "cmd": "id"}\n')
            path = fh.name
        try:
            events = load_trace(path)
            self.assertEqual(len(events), 2)
        finally:
            os.unlink(path)

    def test_explain_incorporates_dynamic_trace(self):
        from security_classifier.dynamic_features import DynamicFeatures
        from security_classifier.explain import summarize
        from security_classifier.features import extract_features

        f = extract_features(BENIGN_SNIPPET)  # weak/no static signal
        dynamic = DynamicFeatures(
            num_network_connections=1,
            unique_remote_hosts=1,
            num_persistence_writes=1,
        )
        summary = summarize("x.py", f, score=0.2, dynamic=dynamic, backend="template")
        self.assertIn("sandboxed trace", summary)
        self.assertIn("persistence", summary)

    def test_explain_notes_absence_of_trace(self):
        from security_classifier.explain import summarize
        from security_classifier.features import extract_features

        f = extract_features(BENIGN_SNIPPET)
        summary = summarize("x.py", f, score=0.2, dynamic=None, backend="template")
        self.assertIn("No sandboxed dynamic trace", summary)


if __name__ == "__main__":
    unittest.main()
