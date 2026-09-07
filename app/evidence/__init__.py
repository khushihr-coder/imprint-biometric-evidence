"""
IMPRINT — Evidence Layer
========================
Disha's evidence construction, canonicalization, and SHA-256 fingerprinting.

Public API
----------
    build_evidence(...)          -> dict
    canonicalize_evidence(ev)    -> str
    hash_evidence(ev)            -> str   (64-char hex)
    sha256_file(path)            -> str   (64-char hex)
"""

from .evidence import (
    build_evidence,
    canonicalize_evidence,
    hash_evidence,
    sha256_file,
)

__all__ = [
    "build_evidence",
    "canonicalize_evidence",
    "hash_evidence",
    "sha256_file",
]
