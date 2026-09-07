"""
IMPRINT — Blockchain Layer
==========================
Disha's Base Sepolia anchoring module.

Public API
----------
    connect()                               -> Web3
    get_chain_id()                          -> int
    get_wallet_address()                    -> str
    get_balance_eth()                       -> str
    encode_evidence_payload(hash)           -> bytes
    decode_evidence_payload(data)           -> str
    anchor_evidence_hash(hash)              -> dict
    verify_on_chain(tx_hash, expected)      -> dict
"""

from .base_sepolia import (
    connect,
    get_chain_id,
    get_wallet_address,
    get_balance_eth,
    encode_evidence_payload,
    decode_evidence_payload,
    anchor_evidence_hash,
    verify_on_chain,
    CHAIN_ID,
    PAYLOAD_MAGIC,
)

__all__ = [
    "connect",
    "get_chain_id",
    "get_wallet_address",
    "get_balance_eth",
    "encode_evidence_payload",
    "decode_evidence_payload",
    "anchor_evidence_hash",
    "verify_on_chain",
    "CHAIN_ID",
    "PAYLOAD_MAGIC",
]
