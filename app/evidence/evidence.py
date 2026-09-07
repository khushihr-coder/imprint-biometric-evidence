"""
IMPRINT — Evidence Construction, Canonicalization, and SHA-256 Fingerprinting
==============================================================================
Module:  app/evidence/evidence.py
Author:  Disha (Evidence + Blockchain layer)
Branch:  disha-blockchain

Design principles
-----------------
* Fully independent of biometric and web implementation internals.
  Consumers pass plain Python dicts/lists; no FAISS or SerpApi calls here.
* No secrets, raw face images, or face embeddings stored in evidence.
* Deterministic: identical logical data -> identical canonical JSON -> identical hash.
* Standard-library only (json, hashlib, os, copy).
* Do NOT add nondeterministic fields automatically (no auto-timestamps).
"""

import copy
import hashlib
import json
import os

# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

SCHEMA = "imprint.task3.evidence"
SCHEMA_VERSION = 1

# Fields that BiometricSearch returns and that we preserve in evidence.
_BIOMETRIC_CANDIDATE_FIELDS = (
    "rank",
    "identity",
    "template_id",
    "similarity",
    "source_image",
)

# Fields that search_web() returns per-candidate and that we preserve.
_WEB_CANDIDATE_FIELDS = (
    "provider",
    "result_type",
    "url",
    "title",
    "image_url",
    "source",
    "retrieved_at",
    "domain",
    "is_social",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pick_fields(record, fields):
    """
    Return a new dict containing only the keys present in *fields* that also
    exist in *record*.  Unknown extra keys from the source are dropped so that
    we never accidentally persist internal implementation details.
    """
    return {k: record[k] for k in fields if k in record}


def _normalise_biometric_candidates(candidates):
    """
    Strip each biometric candidate down to the evidence schema fields.
    Ordering is preserved (rank order from BiometricSearch is semantically
    meaningful and must not be changed here).
    """
    return [_pick_fields(c, _BIOMETRIC_CANDIDATE_FIELDS) for c in candidates]


def _normalise_web_candidates(candidates):
    """
    Strip each web candidate down to the evidence schema fields.
    Ordering is preserved (social-domain priority ordering from
    CandidateProcessor is semantically meaningful).
    """
    return [_pick_fields(c, _WEB_CANDIDATE_FIELDS) for c in candidates]


# ---------------------------------------------------------------------------
# Public: file fingerprinting
# ---------------------------------------------------------------------------

def sha256_file(path):
    """
    Compute the SHA-256 digest of a file using chunked reading.

    Parameters
    ----------
    path : str
        Absolute or relative path to the file.

    Returns
    -------
    str
        Lowercase 64-character hexadecimal digest.

    Raises
    ------
    FileNotFoundError
        If the file does not exist at *path*.
    """
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"[evidence] sha256_file: file not found: {repr(path)}"
        )

    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Public: canonicalization
# ---------------------------------------------------------------------------

def canonicalize_evidence(evidence):
    """
    Produce a canonical, deterministic JSON string from an evidence dict.

    Rules
    -----
    * Dictionary keys are sorted at every level of nesting (json sort_keys).
    * No indentation or extra whitespace (compact separators).
    * UTF-8 compatible (ensure_ascii=False preserves non-ASCII as-is).
    * The caller's object is never mutated (deep-copy before serialisation).
    * No nondeterministic fields are added automatically.

    Parameters
    ----------
    evidence : dict
        A plain Python dict (typically produced by build_evidence).

    Returns
    -------
    str
        Canonical JSON string.
    """
    # Deep-copy so we never mutate the caller's structure.
    snapshot = copy.deepcopy(evidence)
    return json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Public: hashing
# ---------------------------------------------------------------------------

def _hash_bytes(data):
    """Return the lowercase SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def hash_evidence(evidence):
    """
    Compute the SHA-256 fingerprint of an evidence dict.

    Steps
    -----
    1. Canonicalize the evidence dict to a deterministic JSON string.
    2. Encode the string as UTF-8 bytes.
    3. Compute SHA-256.
    4. Return the lowercase 64-character hexadecimal digest.

    Parameters
    ----------
    evidence : dict
        A plain Python dict (typically produced by build_evidence).

    Returns
    -------
    str
        Lowercase 64-character hex digest.
    """
    canonical = canonicalize_evidence(evidence)
    encoded = canonical.encode("utf-8")
    return _hash_bytes(encoded)


# ---------------------------------------------------------------------------
# Public: evidence builder
# ---------------------------------------------------------------------------

def build_evidence(
    input_image_sha256,
    biometric_candidates,
    web_provider,
    web_candidates,
    verification,
    provenance=None,
):
    """
    Construct a validated, schema-conforming evidence dict.

    Parameters
    ----------
    input_image_sha256 : str
        SHA-256 hex digest of the probe/input image (compute with sha256_file).
        Only a fingerprint - the raw image bytes are never stored here.
    biometric_candidates : list[dict]
        List of candidate dicts returned by BiometricSearch.search().
        Expected fields per item: rank, identity, template_id, similarity,
        source_image.
    web_provider : str
        Name of the web search provider (e.g. "serpapi_google_lens").
    web_candidates : list[dict]
        List of candidate dicts returned by search_web().
        Expected fields per item: provider, result_type, url, title,
        image_url, source, retrieved_at, domain, is_social.
    verification : dict
        Verification outcome. At minimum {"status": "<STATUS_STRING>"}.
        Additional detail keys are preserved as-is.
    provenance : dict, optional
        Optional provenance information (source_url, provider, retrieved_at,
        session metadata, etc.). If omitted an empty dict is stored.
        Do not put secrets here.

    Returns
    -------
    dict
        A plain Python dict conforming to the imprint.task3.evidence schema.

    Raises
    ------
    ValueError
        If any required argument is missing or obviously invalid.
    """
    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    if not input_image_sha256 or not isinstance(input_image_sha256, str):
        raise ValueError(
            "[evidence] build_evidence: 'input_image_sha256' must be a "
            "non-empty string. Use sha256_file(path) to compute it."
        )

    if not isinstance(biometric_candidates, list):
        raise ValueError(
            "[evidence] build_evidence: 'biometric_candidates' must be a list "
            "(got {!r}).".format(type(biometric_candidates).__name__)
        )

    if not isinstance(web_candidates, list):
        raise ValueError(
            "[evidence] build_evidence: 'web_candidates' must be a list "
            "(got {!r}).".format(type(web_candidates).__name__)
        )

    if not web_provider or not isinstance(web_provider, str):
        raise ValueError(
            "[evidence] build_evidence: 'web_provider' must be a non-empty string."
        )

    if not verification or not isinstance(verification, dict):
        raise ValueError(
            "[evidence] build_evidence: 'verification' must be a non-empty dict "
            "with at least a 'status' key."
        )

    if "status" not in verification:
        raise ValueError(
            "[evidence] build_evidence: 'verification' dict must contain a 'status' key."
        )

    # ------------------------------------------------------------------
    # Normalise candidates (field-whitelist; preserve list order)
    # ------------------------------------------------------------------
    norm_bio = _normalise_biometric_candidates(biometric_candidates)
    norm_web = _normalise_web_candidates(web_candidates)

    # Deep-copy verification so the caller's dict is not retained by reference.
    norm_verification = copy.deepcopy(verification)

    # Provenance: accept caller-supplied dict or default to empty.
    norm_provenance = copy.deepcopy(provenance) if isinstance(provenance, dict) else {}

    # ------------------------------------------------------------------
    # Assemble evidence object
    # ------------------------------------------------------------------
    evidence = {
        "schema": SCHEMA,
        "version": SCHEMA_VERSION,
        "input": {
            "image_sha256": input_image_sha256,
        },
        "biometric": {
            "candidates": norm_bio,
        },
        "web": {
            "provider": web_provider,
            "candidates": norm_web,
        },
        "verification": norm_verification,
        "provenance": norm_provenance,
    }

    return evidence
