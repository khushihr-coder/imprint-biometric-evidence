"""
IMPRINT — Base Sepolia Blockchain Anchoring Module
===================================================
Module:  app/blockchain/base_sepolia.py
Author:  Disha (Evidence + Blockchain layer)
Branch:  disha-blockchain

Responsibility
--------------
Take a SHA-256 evidence fingerprint produced by app.evidence and anchor
it into a real Base Sepolia transaction.  The transaction carries ONLY:

    b"IMPRINT1" + <32 raw SHA-256 bytes>   (40 bytes total)

No raw images, embeddings, API keys, private keys, or full evidence JSON
are ever written to chain.

Web3.py 8.0.0 API is used throughout.  EIP-1559 fee model is assumed
(Base Sepolia supports it).

Public API
----------
    connect()                                   -> Web3
    get_chain_id()                              -> int
    get_wallet_address()                        -> str  (checksum)
    get_balance_eth()                           -> str  (human-readable)
    encode_evidence_payload(evidence_hash)      -> bytes
    decode_evidence_payload(data)               -> str  (64-char hex)
    anchor_evidence_hash(evidence_hash)         -> dict
    verify_on_chain(tx_hash, expected_hash)     -> dict
"""

import os
from decimal import Decimal

from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import TransactionNotFound

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHAIN_ID = 84532                 # Base Sepolia
PAYLOAD_MAGIC = b"IMPRINT1"     # 8-byte schema marker
PAYLOAD_VERSION = 1              # encoded in the magic string above
PAYLOAD_TOTAL_LEN = 40           # 8 magic + 32 hash bytes

# Gas headroom multiplier applied to the estimate
_GAS_MULTIPLIER = 1.3

# EIP-1559 tip cap (in wei) — modest, enough for Base Sepolia
_DEFAULT_TIP_WEI = 1_000_000     # 0.001 Gwei

# Receipt poll timeout (seconds)
_RECEIPT_TIMEOUT = 180

# ---------------------------------------------------------------------------
# Internal: load and validate configuration once
# ---------------------------------------------------------------------------

def _load_config():
    """
    Load .env and return validated configuration dict.
    Raises EnvironmentError with a clear message on any misconfiguration.
    Never prints or returns the private key.
    """
    load_dotenv()

    rpc_url    = os.getenv("BASE_SEPOLIA_RPC_URL", "").strip()
    wallet_addr = os.getenv("WALLET_ADDRESS", "").strip()
    private_key = os.getenv("WALLET_PRIVATE_KEY", "").strip()

    if not rpc_url:
        raise EnvironmentError(
            "[blockchain] BASE_SEPOLIA_RPC_URL is not set in .env"
        )
    if not wallet_addr:
        raise EnvironmentError(
            "[blockchain] WALLET_ADDRESS is not set in .env"
        )
    if not private_key:
        raise EnvironmentError(
            "[blockchain] WALLET_PRIVATE_KEY is not set in .env"
        )

    return {
        "rpc_url": rpc_url,
        "wallet_addr": wallet_addr,
        "private_key": private_key,
    }


# ---------------------------------------------------------------------------
# Internal: validate hex hash string
# ---------------------------------------------------------------------------

def _validate_hash(evidence_hash: str):
    """
    Raise ValueError if evidence_hash is not a 64-character lowercase hex string.
    """
    if not isinstance(evidence_hash, str):
        raise ValueError(
            f"[blockchain] evidence_hash must be a str, got {type(evidence_hash).__name__!r}"
        )
    if len(evidence_hash) != 64:
        raise ValueError(
            f"[blockchain] evidence_hash must be exactly 64 hex characters, "
            f"got {len(evidence_hash)}"
        )
    if not all(c in "0123456789abcdef" for c in evidence_hash.lower()):
        raise ValueError(
            "[blockchain] evidence_hash contains non-hexadecimal characters"
        )


# ---------------------------------------------------------------------------
# Public: connect
# ---------------------------------------------------------------------------

def connect() -> Web3:
    """
    Load .env, create a Web3 HTTPProvider, and validate the connection.

    Validates:
    - RPC reachability
    - Chain ID == 84532 (Base Sepolia)
    - WALLET_ADDRESS is a valid checksum address
    - Derived address from WALLET_PRIVATE_KEY matches WALLET_ADDRESS

    Returns
    -------
    Web3
        A connected and validated Web3 instance.

    Raises
    ------
    EnvironmentError
        On misconfiguration or connection failure.
    """
    cfg = _load_config()
    w3 = Web3(Web3.HTTPProvider(cfg["rpc_url"]))

    if not w3.is_connected():
        raise EnvironmentError(
            f"[blockchain] Cannot connect to RPC: {cfg['rpc_url']!r}"
        )

    chain_id = w3.eth.chain_id
    if chain_id != CHAIN_ID:
        raise EnvironmentError(
            f"[blockchain] Wrong chain: expected {CHAIN_ID} (Base Sepolia), "
            f"got {chain_id}"
        )

    # Validate configured wallet address
    try:
        checksum_addr = w3.to_checksum_address(cfg["wallet_addr"])
    except Exception as exc:
        raise EnvironmentError(
            f"[blockchain] WALLET_ADDRESS is not a valid Ethereum address: {exc}"
        ) from exc

    # Derive address from private key and compare
    try:
        acct = w3.eth.account.from_key(cfg["private_key"])
    except Exception as exc:
        raise EnvironmentError(
            "[blockchain] WALLET_PRIVATE_KEY is invalid (could not derive account)"
        ) from exc

    derived = acct.address
    if derived.lower() != checksum_addr.lower():
        raise EnvironmentError(
            f"[blockchain] WALLET_PRIVATE_KEY does not correspond to "
            f"WALLET_ADDRESS.  Derived: {derived}"
        )

    return w3


# ---------------------------------------------------------------------------
# Public: informational helpers
# ---------------------------------------------------------------------------

def get_chain_id() -> int:
    """Return the chain ID of the connected network (must be 84532)."""
    w3 = connect()
    return w3.eth.chain_id


def get_wallet_address() -> str:
    """Return the checksum wallet address from .env."""
    cfg = _load_config()
    w3 = Web3()
    return w3.to_checksum_address(cfg["wallet_addr"])


def get_balance_eth() -> str:
    """
    Return the wallet balance as a human-readable string in ETH.
    Example: "0.0001"
    """
    cfg = _load_config()
    w3 = connect()
    addr = w3.to_checksum_address(cfg["wallet_addr"])
    wei = w3.eth.get_balance(addr)
    eth_val = Web3.from_wei(wei, "ether")
    return str(eth_val)


# ---------------------------------------------------------------------------
# Public: payload encoding / decoding
# ---------------------------------------------------------------------------

def encode_evidence_payload(evidence_hash: str) -> bytes:
    """
    Encode an evidence hash as a compact 40-byte binary payload.

    Layout
    ------
    Bytes 0–7  : b"IMPRINT1"  (schema magic + version marker)
    Bytes 8–39 : raw 32-byte SHA-256 digest

    Parameters
    ----------
    evidence_hash : str
        Lowercase 64-character hex SHA-256 digest.

    Returns
    -------
    bytes
        40-byte payload ready to embed in a transaction data field.

    Raises
    ------
    ValueError
        If evidence_hash is not a valid 64-character hex string.
    """
    _validate_hash(evidence_hash)
    raw_hash = bytes.fromhex(evidence_hash)          # 32 bytes
    return PAYLOAD_MAGIC + raw_hash                  # 40 bytes


def decode_evidence_payload(data: bytes) -> str:
    """
    Recover the evidence hash from a raw transaction data payload.

    Parameters
    ----------
    data : bytes
        Raw bytes read from a transaction's data/input field.

    Returns
    -------
    str
        Lowercase 64-character hex SHA-256 digest.

    Raises
    ------
    ValueError
        If the data is malformed, not exactly 40 bytes, or the magic marker
        is absent.  Both under-length AND over-length payloads are rejected.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        # Web3 may return HexBytes; convert defensively
        data = bytes(data)

    if len(data) != PAYLOAD_TOTAL_LEN:
        raise ValueError(
            f"[blockchain] Payload must be exactly {PAYLOAD_TOTAL_LEN} bytes, "
            f"got {len(data)}"
        )

    magic = data[:len(PAYLOAD_MAGIC)]
    if magic != PAYLOAD_MAGIC:
        raise ValueError(
            f"[blockchain] Invalid payload magic: expected {PAYLOAD_MAGIC!r}, "
            f"got {magic!r}"
        )

    raw_hash = data[len(PAYLOAD_MAGIC): PAYLOAD_TOTAL_LEN]   # bytes 8–39
    return raw_hash.hex()                                      # 64-char hex


# ---------------------------------------------------------------------------
# Internal: EIP-1559 fee estimation
# ---------------------------------------------------------------------------

def _get_eip1559_fees(w3: Web3):
    """
    Return (maxFeePerGas, maxPriorityFeePerGas) in wei for Base Sepolia.
    Uses the latest block baseFeePerGas + a modest tip.
    """
    latest_block = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas", 0)

    # Use the chain's reported max_priority_fee if available, otherwise default
    try:
        tip = w3.eth.max_priority_fee
    except Exception:
        tip = _DEFAULT_TIP_WEI

    tip = max(tip, _DEFAULT_TIP_WEI)

    # maxFeePerGas = 2 * baseFee + tip  (standard EIP-1559 headroom)
    max_fee = 2 * base_fee + tip
    return max_fee, tip


# ---------------------------------------------------------------------------
# Public: anchor
# ---------------------------------------------------------------------------

def anchor_evidence_hash(evidence_hash: str) -> dict:
    """
    Anchor an evidence hash fingerprint on Base Sepolia.

    Sends a self-transaction (from == to == wallet address) carrying only
    the 40-byte IMPRINT payload in the data field.  Value is 0 ETH.

    Parameters
    ----------
    evidence_hash : str
        Lowercase 64-character hex SHA-256 digest from hash_evidence().

    Returns
    -------
    dict
        {
            "status":        "SUCCESS",
            "tx_hash":       "0x...",
            "chain_id":      84532,
            "block_number":  <int>,
            "gas_used":      <int>,
            "evidence_hash": "<64-char hex>",
        }

    Raises
    ------
    ValueError
        If evidence_hash is invalid.
    RuntimeError
        If the transaction fails or the receipt indicates failure.
    """
    _validate_hash(evidence_hash)

    cfg = _load_config()
    w3  = connect()

    addr     = w3.to_checksum_address(cfg["wallet_addr"])
    pk       = cfg["private_key"]
    payload  = encode_evidence_payload(evidence_hash)

    # Nonce (use 'pending' to handle rapid sequential calls)
    nonce = w3.eth.get_transaction_count(addr, "pending")

    # EIP-1559 fees
    max_fee_per_gas, max_priority_fee_per_gas = _get_eip1559_fees(w3)

    # Gas estimate
    tx_for_estimate = {
        "from":  addr,
        "to":    addr,
        "value": 0,
        "data":  payload,
    }
    gas_estimate = w3.eth.estimate_gas(tx_for_estimate)
    gas_limit = int(gas_estimate * _GAS_MULTIPLIER)

    # Build EIP-1559 transaction
    tx = {
        "type":                  2,
        "chainId":               CHAIN_ID,
        "nonce":                 nonce,
        "to":                    addr,
        "value":                 0,
        "data":                  payload,
        "gas":                   gas_limit,
        "maxFeePerGas":          max_fee_per_gas,
        "maxPriorityFeePerGas":  max_priority_fee_per_gas,
    }

    # Sign
    signed = w3.eth.account.sign_transaction(tx, pk)

    # Send
    tx_hash_bytes = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hash_hex   = "0x" + tx_hash_bytes.hex()

    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(
        tx_hash_bytes,
        timeout=_RECEIPT_TIMEOUT,
    )

    if receipt["status"] != 1:
        raise RuntimeError(
            f"[blockchain] Transaction reverted on-chain. "
            f"TX hash: {tx_hash_hex}"
        )

    return {
        "status":        "SUCCESS",
        "tx_hash":       tx_hash_hex,
        "chain_id":      CHAIN_ID,
        "block_number":  receipt["blockNumber"],
        "gas_used":      receipt["gasUsed"],
        "evidence_hash": evidence_hash,
    }


# ---------------------------------------------------------------------------
# Public: verify
# ---------------------------------------------------------------------------

def verify_on_chain(tx_hash: str, expected_hash: str) -> dict:
    """
    Fetch a transaction from Base Sepolia and verify the embedded evidence hash.

    Parameters
    ----------
    tx_hash : str
        Transaction hash returned by anchor_evidence_hash() ("0x...").
    expected_hash : str
        The locally-computed SHA-256 evidence hash to compare against.

    Returns
    -------
    dict
        On success / match:
        {
            "status":        "VERIFIED",
            "match":         True,
            "local_hash":    "<64-char hex>",
            "on_chain_hash": "<64-char hex>",
            "tx_hash":       "0x...",
            "chain_id":      84532,
            "block_number":  <int>,
        }

        On hash mismatch:
        {
            "status":        "TAMPER_DETECTED",
            "match":         False,
            "local_hash":    "<64-char hex>",
            "on_chain_hash": "<64-char hex>",
            "tx_hash":       "0x...",
        }

        On decode failure:
        {
            "status":  "DECODE_ERROR",
            "match":   False,
            "error":   "<message>",
            "tx_hash": "0x...",
        }
    """
    _validate_hash(expected_hash)

    w3 = connect()

    # Fetch transaction
    try:
        tx = w3.eth.get_transaction(tx_hash)
    except TransactionNotFound:
        return {
            "status":  "TX_NOT_FOUND",
            "match":   False,
            "error":   f"Transaction {tx_hash!r} not found on Base Sepolia",
            "tx_hash": tx_hash,
        }

    # Decode payload
    raw_data = bytes(tx["input"])
    try:
        on_chain_hash = decode_evidence_payload(raw_data)
    except ValueError as exc:
        return {
            "status":  "DECODE_ERROR",
            "match":   False,
            "error":   str(exc),
            "tx_hash": tx_hash,
        }

    # Normalise to lowercase for deterministic comparison
    local_norm    = expected_hash.lower()
    on_chain_norm = on_chain_hash.lower()
    match         = local_norm == on_chain_norm

    if match:
        return {
            "status":        "VERIFIED",
            "match":         True,
            "local_hash":    local_norm,
            "on_chain_hash": on_chain_norm,
            "tx_hash":       tx_hash,
            "chain_id":      CHAIN_ID,
            "block_number":  tx.get("blockNumber"),
        }
    else:
        return {
            "status":        "TAMPER_DETECTED",
            "match":         False,
            "local_hash":    local_norm,
            "on_chain_hash": on_chain_norm,
            "tx_hash":       tx_hash,
        }
