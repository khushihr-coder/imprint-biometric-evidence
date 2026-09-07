"""
scripts/test_evidence.py
========================
IMPRINT — Evidence Layer Integration Tests
Branch: disha-blockchain

Tests
-----
1.  Canonicalize a fixed evidence object and print canonical JSON.
2.  Hash the same evidence twice — assert identical results.
3.  Assert SHA-256 result is exactly 64 hexadecimal characters.
4.  Change ONE evidence field — assert hash changes.
5.  Change dict insertion order — assert canonical JSON/hash stays identical.
6.  Write a temp file, run sha256_file twice, assert identical results.
7.  Test invalid/missing inputs — assert clear ValueError is raised.

Run from project root:
    python scripts/test_evidence.py
"""

import sys
import os
import tempfile
import copy

# ---------------------------------------------------------------------------
# Make the project root importable from scripts/
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.evidence import (
    build_evidence,
    canonicalize_evidence,
    hash_evidence,
    sha256_file,
)

# ---------------------------------------------------------------------------
# Shared fixture data — fixed, no secrets, no real images
# ---------------------------------------------------------------------------

SAMPLE_IMAGE_SHA256 = "a" * 64   # deterministic stand-in (64 hex chars)

SAMPLE_BIOMETRIC_CANDIDATES = [
    {
        "rank": 1,
        "identity": "George_W_Bush",
        "template_id": "George_W_Bush_0521.jpg",
        "similarity": 0.8492,
        "source_image": "data/faces/George_W_Bush/George_W_Bush_0521.jpg",
    },
    {
        "rank": 2,
        "identity": "Arnold_Schwarzenegger",
        "template_id": "Arnold_Schwarzenegger_0012.jpg",
        "similarity": 0.7211,
        "source_image": "data/faces/Arnold_Schwarzenegger/Arnold_Schwarzenegger_0012.jpg",
    },
]

SAMPLE_WEB_CANDIDATES = [
    {
        "provider": "serpapi_google_lens",
        "result_type": "visual_match",
        "url": "https://www.example.com/article",
        "title": "Example Article",
        "image_url": "https://www.example.com/photo.jpg",
        "source": "example.com",
        "retrieved_at": "2026-09-07T10:00:00Z",
        "domain": "www.example.com",
        "is_social": False,
    },
    {
        "provider": "serpapi_google_lens",
        "result_type": "visual_match",
        "url": "https://www.instagram.com/p/abc123/",
        "title": "Instagram post",
        "image_url": "https://cdn.instagram.com/abc123.jpg",
        "source": "instagram.com",
        "retrieved_at": "2026-09-07T10:00:05Z",
        "domain": "www.instagram.com",
        "is_social": True,
    },
]

SAMPLE_VERIFICATION = {
    "status": "SUPPORTED_MATCH",
    "details": {
        "biometric_top_identity": "George_W_Bush",
        "biometric_top_score": 0.8492,
    },
}

SAMPLE_PROVENANCE = {
    "provider": "serpapi_google_lens",
    "retrieved_at": "2026-09-07T10:00:00Z",
}

# ---------------------------------------------------------------------------
# Test runner helpers
# ---------------------------------------------------------------------------

_results = {}


def _pass(name):
    _results[name] = "PASS"
    print(f"  [PASS] {name}")


def _fail(name, reason):
    _results[name] = "FAIL"
    print(f"  [FAIL] {name}: {reason}")


# ---------------------------------------------------------------------------
# TEST 1 — Canonicalize a fixed evidence object and print canonical JSON
# ---------------------------------------------------------------------------
def test_canonicalization():
    name = "Canonicalization"
    try:
        ev = build_evidence(
            input_image_sha256=SAMPLE_IMAGE_SHA256,
            biometric_candidates=SAMPLE_BIOMETRIC_CANDIDATES,
            web_provider="serpapi_google_lens",
            web_candidates=SAMPLE_WEB_CANDIDATES,
            verification=SAMPLE_VERIFICATION,
            provenance=SAMPLE_PROVENANCE,
        )
        canonical = canonicalize_evidence(ev)
        assert isinstance(canonical, str), "Canonical output must be a string"
        assert len(canonical) > 0, "Canonical output must not be empty"
        # Verify it is valid JSON
        import json
        parsed = json.loads(canonical)
        assert isinstance(parsed, dict), "Canonical JSON must parse to a dict"
        print(f"\n  Canonical JSON (first 200 chars):\n  {canonical[:200]}...")
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 2 — Hash the same evidence twice — assert identical results
# ---------------------------------------------------------------------------
def test_deterministic_hash():
    name = "Deterministic hash"
    try:
        ev = build_evidence(
            input_image_sha256=SAMPLE_IMAGE_SHA256,
            biometric_candidates=SAMPLE_BIOMETRIC_CANDIDATES,
            web_provider="serpapi_google_lens",
            web_candidates=SAMPLE_WEB_CANDIDATES,
            verification=SAMPLE_VERIFICATION,
            provenance=SAMPLE_PROVENANCE,
        )
        h1 = hash_evidence(ev)
        h2 = hash_evidence(ev)
        assert h1 == h2, f"Hashes differ: {h1} != {h2}"
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 3 — Assert SHA-256 result is exactly 64 hex characters
# ---------------------------------------------------------------------------
def test_hash_length_and_format():
    name = "Hash length and hex format"
    try:
        ev = build_evidence(
            input_image_sha256=SAMPLE_IMAGE_SHA256,
            biometric_candidates=SAMPLE_BIOMETRIC_CANDIDATES,
            web_provider="serpapi_google_lens",
            web_candidates=SAMPLE_WEB_CANDIDATES,
            verification=SAMPLE_VERIFICATION,
        )
        h = hash_evidence(ev)
        assert len(h) == 64, f"Expected 64 chars, got {len(h)}"
        assert h == h.lower(), "Hash must be lowercase"
        assert all(c in "0123456789abcdef" for c in h), "Hash must be hex"
        print(f"\n  Hash: {h}")
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 4 — Change ONE evidence field — assert hash changes
# ---------------------------------------------------------------------------
def test_mutation_changes_hash():
    name = "Mutation changes hash"
    try:
        ev_original = build_evidence(
            input_image_sha256=SAMPLE_IMAGE_SHA256,
            biometric_candidates=SAMPLE_BIOMETRIC_CANDIDATES,
            web_provider="serpapi_google_lens",
            web_candidates=SAMPLE_WEB_CANDIDATES,
            verification=SAMPLE_VERIFICATION,
        )
        # Mutate a copy — change the image hash
        ev_mutated = copy.deepcopy(ev_original)
        ev_mutated["input"]["image_sha256"] = "b" * 64

        h_original = hash_evidence(ev_original)
        h_mutated = hash_evidence(ev_mutated)
        assert h_original != h_mutated, "Mutation did NOT change the hash — this is wrong"
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 5 — Change dict insertion order — hash must stay identical
# ---------------------------------------------------------------------------
def test_insertion_order_independence():
    name = "Insertion-order independence"
    try:
        # Build evidence in normal order
        ev_a = build_evidence(
            input_image_sha256=SAMPLE_IMAGE_SHA256,
            biometric_candidates=SAMPLE_BIOMETRIC_CANDIDATES,
            web_provider="serpapi_google_lens",
            web_candidates=SAMPLE_WEB_CANDIDATES,
            verification=SAMPLE_VERIFICATION,
        )

        # Build an identical evidence dict but reassemble keys in reversed order
        ev_b = {k: ev_a[k] for k in reversed(list(ev_a.keys()))}

        canonical_a = canonicalize_evidence(ev_a)
        canonical_b = canonicalize_evidence(ev_b)
        assert canonical_a == canonical_b, (
            "Canonical JSON differs despite same data — sort_keys broken\n"
            f"  A: {canonical_a[:100]}\n  B: {canonical_b[:100]}"
        )

        h_a = hash_evidence(ev_a)
        h_b = hash_evidence(ev_b)
        assert h_a == h_b, f"Hashes differ due to key order: {h_a} != {h_b}"
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 6 — sha256_file: temp file, run twice, assert identical
# ---------------------------------------------------------------------------
def test_file_sha256():
    name = "File SHA-256"
    tmp_path = None
    try:
        # Write a small deterministic temp file
        content = b"IMPRINT evidence test binary payload\x00\x01\x02"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tf:
            tf.write(content)
            tmp_path = tf.name

        h1 = sha256_file(tmp_path)
        h2 = sha256_file(tmp_path)
        assert h1 == h2, f"File hashes differ: {h1} != {h2}"
        assert len(h1) == 64, f"Expected 64 chars, got {len(h1)}"
        assert all(c in "0123456789abcdef" for c in h1), "Not a hex digest"
        print(f"\n  File hash: {h1}")

        # Also verify FileNotFoundError on missing file
        bad_path = tmp_path + ".nonexistent"
        raised = False
        try:
            sha256_file(bad_path)
        except FileNotFoundError:
            raised = True
        assert raised, "sha256_file should raise FileNotFoundError for missing file"

        _pass(name)
    except Exception as e:
        _fail(name, str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


# ---------------------------------------------------------------------------
# TEST 7 — Validation rejects invalid inputs clearly
# ---------------------------------------------------------------------------
def test_validation():
    name = "Validation"
    errors = []

    # 7a — missing image hash
    try:
        build_evidence(
            input_image_sha256="",
            biometric_candidates=[],
            web_provider="serpapi_google_lens",
            web_candidates=[],
            verification={"status": "SUPPORTED_MATCH"},
        )
        errors.append("Should have raised ValueError for empty image_sha256")
    except ValueError:
        pass  # expected

    # 7b — None instead of image hash
    try:
        build_evidence(
            input_image_sha256=None,
            biometric_candidates=[],
            web_provider="serpapi_google_lens",
            web_candidates=[],
            verification={"status": "SUPPORTED_MATCH"},
        )
        errors.append("Should have raised ValueError for None image_sha256")
    except ValueError:
        pass  # expected

    # 7c — biometric_candidates not a list
    try:
        build_evidence(
            input_image_sha256=SAMPLE_IMAGE_SHA256,
            biometric_candidates=None,
            web_provider="serpapi_google_lens",
            web_candidates=[],
            verification={"status": "SUPPORTED_MATCH"},
        )
        errors.append("Should have raised ValueError for None biometric_candidates")
    except ValueError:
        pass  # expected

    # 7d — web_candidates not a list
    try:
        build_evidence(
            input_image_sha256=SAMPLE_IMAGE_SHA256,
            biometric_candidates=[],
            web_provider="serpapi_google_lens",
            web_candidates="not a list",
            verification={"status": "SUPPORTED_MATCH"},
        )
        errors.append("Should have raised ValueError for string web_candidates")
    except ValueError:
        pass  # expected

    # 7e — verification missing status key
    try:
        build_evidence(
            input_image_sha256=SAMPLE_IMAGE_SHA256,
            biometric_candidates=[],
            web_provider="serpapi_google_lens",
            web_candidates=[],
            verification={"no_status_key": True},
        )
        errors.append("Should have raised ValueError for verification missing 'status'")
    except ValueError:
        pass  # expected

    # 7f — verification is None
    try:
        build_evidence(
            input_image_sha256=SAMPLE_IMAGE_SHA256,
            biometric_candidates=[],
            web_provider="serpapi_google_lens",
            web_candidates=[],
            verification=None,
        )
        errors.append("Should have raised ValueError for None verification")
    except ValueError:
        pass  # expected

    # 7g — web_provider is empty string
    try:
        build_evidence(
            input_image_sha256=SAMPLE_IMAGE_SHA256,
            biometric_candidates=[],
            web_provider="",
            web_candidates=[],
            verification={"status": "SUPPORTED_MATCH"},
        )
        errors.append("Should have raised ValueError for empty web_provider")
    except ValueError:
        pass  # expected

    if errors:
        _fail(name, " | ".join(errors))
    else:
        _pass(name)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n========================================")
    print("  IMPRINT - EVIDENCE HASH TEST")
    print("========================================\n")

    test_canonicalization()
    test_deterministic_hash()
    test_hash_length_and_format()
    test_mutation_changes_hash()
    test_insertion_order_independence()
    test_file_sha256()
    test_validation()

    print("\n========================================")
    print("  RESULTS SUMMARY")
    print("========================================")

    label_map = {
        "Canonicalization":              "Canonicalization",
        "Deterministic hash":            "Deterministic hash",
        "Hash length and hex format":    "Hash length and hex format",
        "Mutation changes hash":         "Mutation changes hash",
        "Insertion-order independence":  "Insertion-order independence",
        "File SHA-256":                  "File SHA-256",
        "Validation":                    "Validation",
    }

    all_passed = True
    for label in label_map:
        result = _results.get(label, "NOT RUN")
        print(f"  {label_map[label]:<30} {result}")
        if result != "PASS":
            all_passed = False

    print("\n========================================")
    if all_passed:
        print("  ALL EVIDENCE TESTS PASSED")
    else:
        print("  SOME TESTS FAILED — review output above")
    print("========================================\n")

    sys.exit(0 if all_passed else 1)
