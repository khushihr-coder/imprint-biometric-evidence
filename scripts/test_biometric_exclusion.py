"""
scripts/test_biometric_exclusion.py
===================================
Regression tests for BiometricSearch exclusion logic:
- TEST A: Probe path equals candidate source path -> excluded
- TEST B: Probe copied to different path with identical bytes -> excluded
- TEST C: Different file with different content -> NOT excluded
"""

import os
import sys
import tempfile
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.biometric.search import should_exclude_candidate


def run_tests():
    print("========================================")
    print("  BIOMETRIC EXCLUSION REGRESSION TESTS")
    print("========================================")

    # Use known probe files from dataset
    bush_0002 = os.path.join(ROOT, "lfw-deepfunneled", "lfw-deepfunneled", "George_W_Bush", "George_W_Bush_0002.jpg")
    bush_0001 = os.path.join(ROOT, "lfw-deepfunneled", "lfw-deepfunneled", "George_W_Bush", "George_W_Bush_0001.jpg")

    assert os.path.isfile(bush_0002), f"Missing test file: {bush_0002}"
    assert os.path.isfile(bush_0001), f"Missing test file: {bush_0001}"

    # ------------------------------------------------------------------ #
    # TEST A: Probe path equals candidate source path                    #
    # ------------------------------------------------------------------ #
    print("\n[TEST A] Identical Path Exclusion:")
    excluded_a = should_exclude_candidate(bush_0002, bush_0002)
    print(f"  Probe:     {bush_0002}")
    print(f"  Candidate: {bush_0002}")
    print(f"  Excluded:  {excluded_a} (Expected: True)")
    assert excluded_a is True, "TEST A failed: candidate with identical path must be excluded"
    print("  [PASS] TEST A passed.")

    # ------------------------------------------------------------------ #
    # TEST B: Probe copied to different path with identical bytes        #
    # ------------------------------------------------------------------ #
    print("\n[TEST B] Copied File with Identical Content Exclusion:")
    temp_dir = tempfile.mkdtemp(prefix="imprint_test_")
    try:
        copied_probe = os.path.join(temp_dir, "custom_probe_copy.jpg")
        shutil.copyfile(bush_0002, copied_probe)

        print(f"  Probe:     {copied_probe} (different path)")
        print(f"  Candidate: {bush_0002} (original indexed path)")

        # Paths must be strictly different
        assert os.path.abspath(copied_probe) != os.path.abspath(bush_0002)

        excluded_b = should_exclude_candidate(copied_probe, bush_0002)
        print(f"  Excluded:  {excluded_b} (Expected: True)")
        assert excluded_b is True, "TEST B failed: candidate with identical content must be excluded"
        print("  [PASS] TEST B passed.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------ #
    # TEST C: Different file with different content                      #
    # ------------------------------------------------------------------ #
    print("\n[TEST C] Different File (Similar Name) Retention:")
    print(f"  Probe:     {bush_0002}")
    print(f"  Candidate: {bush_0001}")
    excluded_c = should_exclude_candidate(bush_0002, bush_0001)
    print(f"  Excluded:  {excluded_c} (Expected: False)")
    assert excluded_c is False, "TEST C failed: different image must NOT be excluded"
    print("  [PASS] TEST C passed.")

    # ------------------------------------------------------------------ #
    # Robustness Check: Non-existent candidate path                      #
    # ------------------------------------------------------------------ #
    print("\n[ROBUSTNESS] Missing Candidate File Handling:")
    non_existent = os.path.join(ROOT, "lfw-deepfunneled", "non_existent_file.jpg")
    excluded_rob = should_exclude_candidate(bush_0002, non_existent)
    print(f"  Excluded:  {excluded_rob} (Expected: False, graceful fallback)")
    assert excluded_rob is False, "Robustness check failed: missing file should not crash"
    print("  [PASS] Robustness check passed.")

    print("\n========================================")
    print("  ALL BIOMETRIC EXCLUSION TESTS PASSED")
    print("========================================\n")


if __name__ == "__main__":
    run_tests()
