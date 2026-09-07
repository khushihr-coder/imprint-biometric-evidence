"""
scripts/run_pipeline.py
=======================
IMPRINT — End-to-End Pipeline Runner
Branch: disha-blockchain

Stages
------
1.  Validate input image exists
2.  SHA-256 fingerprint of input image
3.  Biometric 1:N search (BiometricSearch, FAISS index)
4.  Live web discovery (Google Lens / SerpApi)
5.  Evidence construction (build_evidence)
6.  Canonical JSON + SHA-256 fingerprint
7.  Artifact persistence (artifacts/runs/<run_id>/)
8.  ONE new Base Sepolia transaction  (anchor_evidence_hash)
9.  Transaction readback + hash verification (verify_on_chain)
10. Final status

Usage
-----
    python scripts/run_pipeline.py "<image_path>"

Security
--------
- Never prints WALLET_PRIVATE_KEY
- Never prints SERPAPI_KEY
- Never writes .env contents to any artifact
"""

import sys
import os
import json
import datetime

# ---------------------------------------------------------------------------
# Make project root importable when run from any CWD
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()

from app.evidence import (
    build_evidence,
    canonicalize_evidence,
    hash_evidence,
    sha256_file,
)
from app.biometric.search import BiometricSearch
from app.web import search_web
from app.web.candidates import CandidateProcessor
from app.blockchain import anchor_evidence_hash, verify_on_chain


# ---------------------------------------------------------------------------
# Pipeline exit codes
# ---------------------------------------------------------------------------
EXIT_OK           = 0
EXIT_BAD_INPUT    = 1
EXIT_BIO_FAIL     = 2
EXIT_WEB_FAIL     = 3
EXIT_MEDIA_FAIL   = 7   # candidate media retrieval failed
EXIT_EVIDENCE_FAIL = 4
EXIT_CHAIN_FAIL   = 5
EXIT_TAMPER       = 6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section(n, title):
    print(f"\n[{n}] {title}")
    print("    " + "-" * 36)


def _line(label, value):
    print(f"    {label:<24} {value}")


def _abort(reason, code=EXIT_BAD_INPUT):
    print(f"\n  [ABORT] {reason}")
    print("\n========================================")
    print(f"  FINAL STATUS: FAILED — {reason}")
    print("========================================\n")
    sys.exit(code)


def _select_web_candidate(candidates):
    """
    Deterministic selection:
    - prefer first candidate where is_social == True
    - otherwise use candidates[0]
    - returns None if list is empty
    """
    if not candidates:
        return None
    for c in candidates:
        if c.get("is_social"):
            return c
    return candidates[0]


def _save_artifacts(run_dir, evidence, canonical_json, evidence_hash,
                    pipeline_result):
    """Persist run artifacts. Never writes secrets."""
    os.makedirs(run_dir, exist_ok=True)

    # 1. Full evidence JSON (pretty-printed for readability)
    with open(os.path.join(run_dir, "evidence.json"), "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)

    # 2. Canonical (compact, deterministic) JSON used for hashing
    with open(os.path.join(run_dir, "evidence.canonical.json"), "w",
              encoding="utf-8") as f:
        f.write(canonical_json)

    # 3. Plain text SHA-256 digest
    with open(os.path.join(run_dir, "evidence.sha256"), "w",
              encoding="utf-8") as f:
        f.write(evidence_hash + "\n")

    # 4. Full pipeline result (blockchain metadata etc.)
    with open(os.path.join(run_dir, "pipeline_result.json"), "w",
              encoding="utf-8") as f:
        json.dump(pipeline_result, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(image_path):
    print("\n========================================")
    print("  IMPRINT - END-TO-END PIPELINE")
    print("========================================")

    # Generate a unique run ID from UTC timestamp
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    run_dir = os.path.join("artifacts", "runs", run_id)

    # ------------------------------------------------------------------ #
    # [1] INPUT VALIDATION                                                 #
    # ------------------------------------------------------------------ #
    _section(1, "INPUT")

    abs_path = os.path.abspath(image_path)
    if not os.path.isfile(abs_path):
        _line("Image", abs_path)
        _abort(f"Input file not found: {abs_path!r}", EXIT_BAD_INPUT)

    _line("Image", abs_path)

    try:
        image_hash = sha256_file(abs_path)
    except Exception as exc:
        _abort(f"Cannot hash input image: {exc}", EXIT_BAD_INPUT)

    _line("Input SHA-256", image_hash)

    # ------------------------------------------------------------------ #
    # [2] BIOMETRIC 1:N SEARCH                                             #
    # ------------------------------------------------------------------ #
    _section(2, "BIOMETRIC 1:N")

    try:
        searcher = BiometricSearch(index_dir="data/index")
        biometric_results, bio_status = searcher.search(abs_path, top_k=5)
    except Exception as exc:
        _line("Status", f"ERROR — {exc}")
        _abort(f"Biometric search raised exception: {exc}", EXIT_BIO_FAIL)

    if not biometric_results:
        _line("Status", f"FAILED — {bio_status}")
        _abort(f"Biometric search returned no candidates: {bio_status}",
               EXIT_BIO_FAIL)

    top_bio = biometric_results[0]
    _line("Status", bio_status)
    _line("Top candidate", top_bio["identity"])
    _line("Score", f"{top_bio['similarity']:.4f}")
    _line("Template", top_bio["template_id"])
    _line("Top-K count", str(len(biometric_results)))

    # ------------------------------------------------------------------ #
    # [3] LIVE WEB DISCOVERY                                               #
    # ------------------------------------------------------------------ #
    _section(3, "WEB DISCOVERY")
    _line("Provider", "Google Lens / SerpApi")

    try:
        web_result = search_web(abs_path)
    except Exception as exc:
        _line("Status", f"ERROR — {exc}")
        _abort(f"Web search raised exception: {exc}", EXIT_WEB_FAIL)

    if web_result["status"] != "SUCCESS":
        _line("Status", f"FAILED — {web_result.get('message', 'unknown error')}")
        _abort("Web search returned non-SUCCESS status. "
               "Not falling back to hardcoded URL.", EXIT_WEB_FAIL)

    web_candidates = web_result["candidates"]
    web_provider   = web_result["provider"]
    _line("Status", web_result["status"])
    _line("Result count", str(web_result["result_count"]))

    selected_web = _select_web_candidate(web_candidates)

    if selected_web is None:
        _line("Selected source", "NONE")
        _abort("Web search succeeded but returned no usable candidates "
               "(WEB_EVIDENCE_UNAVAILABLE)", EXIT_WEB_FAIL)

    _line("Selected source", selected_web.get("source", "—"))
    _line("Selected URL", selected_web.get("url", "—"))
    _line("Is social", str(selected_web.get("is_social", False)))

    # ------------------------------------------------------------------ #
    # [3A] CANDIDATE MEDIA RETRIEVAL + FINGERPRINTING                      #
    # ------------------------------------------------------------------ #
    _section("3A", "CANDIDATE MEDIA")

    image_url = selected_web.get("image_url")
    if not image_url:
        _line("Download", "FAILED — no image_url on selected candidate")
        _abort("Selected web candidate has no image_url "
               "(WEB_MEDIA_RETRIEVAL_FAILED)", EXIT_MEDIA_FAIL)

    try:
        processor = CandidateProcessor()
        media_path, media_msg = processor.download_image(image_url)
    except Exception as exc:
        _line("Download", f"ERROR — {exc}")
        _abort(f"Candidate media download raised exception: {exc}",
               EXIT_MEDIA_FAIL)

    if media_path is None:
        _line("Download", f"FAILED — {media_msg}")
        _abort(f"Candidate media download failed: {media_msg} "
               "(WEB_MEDIA_RETRIEVAL_FAILED)", EXIT_MEDIA_FAIL)

    # Compute a relative artifact path for safe logging (no absolute machine path
    # in canonical evidence — only the SHA-256 fingerprint enters evidence).
    try:
        media_rel_path = os.path.relpath(media_path)
    except ValueError:
        # relpath can fail across Windows drives; fall back to basename only
        media_rel_path = os.path.basename(media_path)

    try:
        candidate_media_sha256 = sha256_file(media_path)
    except Exception as exc:
        _line("Download", "SUCCESS")
        _line("Saved", media_rel_path)
        _abort(f"Candidate media hashing failed: {exc}", EXIT_MEDIA_FAIL)

    _line("Download", "SUCCESS")
    _line("Saved", media_rel_path)
    _line("Media SHA-256", candidate_media_sha256)

    # ------------------------------------------------------------------ #
    # [4] EVIDENCE CONSTRUCTION                                            #
    # ------------------------------------------------------------------ #
    _section(4, "EVIDENCE")

    # Verification decision: accurate reflection of current architecture.
    # 1:N biometric retrieval + independent web evidence — NOT a 1:1 match.
    verification = {
        "status": "SUPPORTED_MATCH",
        "biometric_top_identity": top_bio["identity"],
        "biometric_top_score": top_bio["similarity"],
        "web_candidate_available": True,
    }

    # Provenance from the selected web candidate (no secrets).
    # candidate_media_sha256 is included so it becomes part of the canonical
    # evidence hash anchored on-chain.  The absolute local path is intentionally
    # omitted from canonical evidence to keep hashes machine-independent.
    provenance = {
        "provider":              selected_web.get("provider", web_provider),
        "source_url":            selected_web.get("url"),
        "source_domain":         selected_web.get("domain"),
        "retrieved_at":          selected_web.get("retrieved_at"),
        "candidate_media_sha256": candidate_media_sha256,
    }

    try:
        evidence = build_evidence(
            input_image_sha256=image_hash,
            biometric_candidates=biometric_results,
            web_provider=web_provider,
            web_candidates=web_candidates,
            verification=verification,
            provenance=provenance,
        )
    except Exception as exc:
        _abort(f"Evidence construction failed: {exc}", EXIT_EVIDENCE_FAIL)

    try:
        canonical_json = canonicalize_evidence(evidence)
        evidence_hash  = hash_evidence(evidence)
    except Exception as exc:
        _abort(f"Evidence hashing failed: {exc}", EXIT_EVIDENCE_FAIL)

    _line("Canonical evidence", "PASS")
    _line("Evidence SHA-256", evidence_hash)

    # ------------------------------------------------------------------ #
    # [5] BLOCKCHAIN ANCHOR                                                #
    # ------------------------------------------------------------------ #
    _section(5, "BLOCKCHAIN")
    _line("Network", "Base Sepolia")
    _line("Chain ID", "84532")
    print("    Anchoring evidence hash — sending transaction...")

    try:
        blockchain_result = anchor_evidence_hash(evidence_hash)
    except Exception as exc:
        _abort(f"Blockchain anchor failed: {exc}", EXIT_CHAIN_FAIL)

    if blockchain_result["status"] != "SUCCESS":
        _abort(f"Anchor returned non-SUCCESS: {blockchain_result}",
               EXIT_CHAIN_FAIL)

    tx_hash = blockchain_result["tx_hash"]
    _line("Transaction", tx_hash)
    _line("Block", str(blockchain_result["block_number"]))
    _line("Gas Used", f"{blockchain_result['gas_used']} gas units")

    # ------------------------------------------------------------------ #
    # [6] READBACK VERIFICATION                                            #
    # ------------------------------------------------------------------ #
    _section(6, "READBACK")

    try:
        verification_result = verify_on_chain(tx_hash, evidence_hash)
    except Exception as exc:
        _abort(f"Transaction readback failed: {exc}", EXIT_CHAIN_FAIL)

    readback_status  = verification_result["status"]
    readback_match   = verification_result.get("match", False)
    local_hash       = verification_result.get("local_hash", evidence_hash)
    on_chain_hash    = verification_result.get("on_chain_hash", "—")

    _line("Local hash", local_hash)
    _line("On-chain hash", on_chain_hash)
    _line("Hash match", "TRUE" if readback_match else "FALSE")

    # ------------------------------------------------------------------ #
    # [7] ARTIFACT PERSISTENCE                                             #
    # ------------------------------------------------------------------ #
    pipeline_result = {
        "run_id":           run_id,
        "image_path":       abs_path,
        "image_sha256":     image_hash,
        "biometric": {
            "status":       bio_status,
            "top_identity": top_bio["identity"],
            "top_score":    top_bio["similarity"],
            "top_template": top_bio["template_id"],
            "candidate_count": len(biometric_results),
        },
        "web": {
            "status":           web_result["status"],
            "provider":         web_provider,
            "result_count":     web_result["result_count"],
            "selected_url":     selected_web.get("url"),
            "selected_source":  selected_web.get("source"),
            "is_social":        selected_web.get("is_social", False),
        },
        "candidate_media": {
            "local_path":  media_rel_path,
            "sha256":      candidate_media_sha256,
            "image_url":   image_url,
        },
        "evidence": {
            "sha256": evidence_hash,
        },
        "blockchain": {
            "tx_hash":      tx_hash,
            "block_number": blockchain_result["block_number"],
            "chain_id":     blockchain_result["chain_id"],
            "gas_used":     blockchain_result["gas_used"],
        },
        "readback": {
            "status":        readback_status,
            "match":         readback_match,
            "local_hash":    local_hash,
            "on_chain_hash": on_chain_hash,
        },
        "final_status": (
            "EVIDENCE VERIFIED"
            if readback_status == "VERIFIED" and readback_match
            else f"FAILED — {readback_status}"
        ),
    }

    try:
        _save_artifacts(run_dir, evidence, canonical_json,
                        evidence_hash, pipeline_result)
    except Exception as exc:
        # Non-fatal: log and continue
        print(f"\n  [WARN] Artifact save failed: {exc}")

    # ------------------------------------------------------------------ #
    # FINAL STATUS                                                         #
    # ------------------------------------------------------------------ #
    print("\n========================================")

    if readback_status == "VERIFIED" and readback_match:
        print("  FINAL STATUS: EVIDENCE VERIFIED")
        print(f"\n  Artifacts saved to: {run_dir}")
        print("========================================\n")
        sys.exit(EXIT_OK)
    elif readback_status == "TAMPER_DETECTED":
        print("  FINAL STATUS: FAILED — TAMPER DETECTED")
        print("  Local hash and on-chain hash do not match.")
        print("========================================\n")
        sys.exit(EXIT_TAMPER)
    else:
        print(f"  FINAL STATUS: FAILED — {readback_status}")
        print("========================================\n")
        sys.exit(EXIT_CHAIN_FAIL)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_pipeline.py <image_path>")
        sys.exit(EXIT_BAD_INPUT)

    run_pipeline(sys.argv[1])
