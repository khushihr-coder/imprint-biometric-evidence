"""
scripts/test_blockchain.py
==========================
IMPRINT — Blockchain Layer Integration Tests
Branch: disha-blockchain

Tests
-----
1.  Environment / configuration validation
2.  Base Sepolia RPC connection
3.  Chain ID == 84532
4.  Wallet / private-key address match
5.  Payload encode / decode round-trip
6.  Invalid hash rejection
7.  REAL testnet transaction (anchor_evidence_hash)
8.  On-chain readback (decode payload from tx)
9.  Hash verification (verify_on_chain -> VERIFIED)
10. Tamper detection (wrong hash -> TAMPER_DETECTED)

Run from project root:
    python scripts/test_blockchain.py

IMPORTANT: one real Base Sepolia transaction is sent.
Never prints private key or .env contents.
"""

import sys
import os
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()

from app.blockchain import (
    connect,
    get_chain_id,
    get_wallet_address,
    get_balance_eth,
    encode_evidence_payload,
    decode_evidence_payload,
    anchor_evidence_hash,
    verify_on_chain,
    CHAIN_ID,
)

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
# Deterministic test evidence hash
# (built from a fixed string — NOT a real image — for reproducibility)
# ---------------------------------------------------------------------------

_TEST_EVIDENCE_HASH = hashlib.sha256(
    b"IMPRINT-test-evidence-payload-disha-blockchain"
).hexdigest()

# ---------------------------------------------------------------------------
# Known confirmed transaction from the initial test run.
# Reused by tests 7-10 so no new on-chain transaction is needed when
# re-running the test suite after the first successful anchor.
# Set to None to force a fresh anchor transaction instead.
# ---------------------------------------------------------------------------
_KNOWN_TX_HASH = "0x22c933741512936928728c657ab669d676d9f284fb0187bbaf2c4df614050373"

# ---------------------------------------------------------------------------
# TEST 1 — Environment: all three vars must be set
# ---------------------------------------------------------------------------
def test_configuration():
    name = "Configuration"
    try:
        rpc  = os.getenv("BASE_SEPOLIA_RPC_URL", "")
        addr = os.getenv("WALLET_ADDRESS", "")
        pk   = os.getenv("WALLET_PRIVATE_KEY", "")
        assert rpc,  "BASE_SEPOLIA_RPC_URL not set"
        assert addr, "WALLET_ADDRESS not set"
        assert pk,   "WALLET_PRIVATE_KEY not set"
        # Length sanity: address 42 chars (0x + 40 hex), pk 64 hex chars
        assert len(addr) == 42, f"WALLET_ADDRESS unexpected length: {len(addr)}"
        assert len(pk)   == 64, f"WALLET_PRIVATE_KEY unexpected length: {len(pk)}"
        # Never print the key — just confirm it is hex
        assert all(c in "0123456789abcdefABCDEF" for c in pk), \
            "WALLET_PRIVATE_KEY contains non-hex characters"
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 2 — Base Sepolia RPC connection
# ---------------------------------------------------------------------------
def test_connection():
    name = "Base Sepolia connection"
    try:
        w3 = connect()
        assert w3.is_connected(), "w3.is_connected() returned False"
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 3 — Chain ID
# ---------------------------------------------------------------------------
def test_chain_id():
    name = "Chain ID"
    try:
        cid = get_chain_id()
        assert cid == CHAIN_ID, f"Expected {CHAIN_ID}, got {cid}"
        print(f"    Chain ID confirmed: {cid}")
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 4 — Wallet / private-key address match
# ---------------------------------------------------------------------------
def test_wallet_key_match():
    name = "Wallet/private-key match"
    try:
        from web3 import Web3
        w3  = connect()
        pk  = os.getenv("WALLET_PRIVATE_KEY")
        cfg_addr = w3.to_checksum_address(os.getenv("WALLET_ADDRESS"))
        derived  = w3.eth.account.from_key(pk).address
        assert derived.lower() == cfg_addr.lower(), \
            f"Derived {derived} != configured {cfg_addr}"
        print(f"    Wallet: {cfg_addr}")
        bal = get_balance_eth()
        print(f"    Balance: {bal} ETH")
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 5 — Payload encode / decode round-trip
# ---------------------------------------------------------------------------
def test_payload_encode_decode():
    name = "Payload encode/decode"
    try:
        h = _TEST_EVIDENCE_HASH
        payload = encode_evidence_payload(h)

        # Check magic prefix
        assert payload[:8] == b"IMPRINT1", \
            f"Wrong magic: {payload[:8]!r}"
        # Total length
        assert len(payload) == 40, \
            f"Expected 40 bytes, got {len(payload)}"

        # Decode
        recovered = decode_evidence_payload(payload)
        assert recovered == h, \
            f"Round-trip mismatch:\n  encoded: {h}\n  decoded: {recovered}"

        # Also confirm HexBytes input (Web3 returns HexBytes from tx.input)
        from hexbytes import HexBytes
        recovered_hb = decode_evidence_payload(HexBytes(payload))
        assert recovered_hb == h, "HexBytes decode failed"

        print(f"    Payload: 0x{payload.hex()}")
        print(f"    Recovered hash: {recovered}")
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 6 — Invalid hash rejection
# ---------------------------------------------------------------------------
def test_invalid_hash_validation():
    name = "Invalid hash validation"
    errors = []

    # 6a — wrong length (63 chars)
    try:
        encode_evidence_payload("a" * 63)
        errors.append("Should have raised ValueError for 63-char hash")
    except ValueError:
        pass

    # 6b — wrong length (65 chars)
    try:
        encode_evidence_payload("a" * 65)
        errors.append("Should have raised ValueError for 65-char hash")
    except ValueError:
        pass

    # 6c — non-hex characters
    try:
        encode_evidence_payload("g" * 64)
        errors.append("Should have raised ValueError for non-hex hash")
    except ValueError:
        pass

    # 6d — None
    try:
        encode_evidence_payload(None)
        errors.append("Should have raised ValueError for None hash")
    except (ValueError, TypeError, AttributeError):
        pass  # any of these is acceptable

    # 6e — empty string
    try:
        encode_evidence_payload("")
        errors.append("Should have raised ValueError for empty hash")
    except ValueError:
        pass

    # 6f — malformed payload decode (too short)
    try:
        decode_evidence_payload(b"SHORT")
        errors.append("Should have raised ValueError for short payload")
    except ValueError:
        pass

    # 6g — wrong magic bytes
    try:
        bad = b"WRONGMAG" + bytes(32)
        decode_evidence_payload(bad)
        errors.append("Should have raised ValueError for wrong magic")
    except ValueError:
        pass

    # 6h — payload exactly 41 bytes (one byte too long) must be rejected
    try:
        over_long = b"IMPRINT1" + bytes(33)   # 8 magic + 33 hash bytes = 41
        decode_evidence_payload(over_long)
        errors.append("Should have raised ValueError for 41-byte (over-length) payload")
    except ValueError:
        pass

    if errors:
        _fail(name, " | ".join(errors))
    else:
        _pass(name)


# ---------------------------------------------------------------------------
# TEST 7 — Real testnet transaction
#
# If _KNOWN_TX_HASH is set (from a previous confirmed run), the test fetches
# that transaction and reconstructs _anchor_result without sending a new tx.
# Set _KNOWN_TX_HASH = None above to force a fresh anchor transaction.
# ---------------------------------------------------------------------------
_anchor_result = None

def test_real_transaction():
    global _anchor_result
    name = "Real transaction"
    try:
        if _KNOWN_TX_HASH:
            # Reuse the previously confirmed transaction — no new tx sent.
            print(f"\n    Reusing confirmed tx: {_KNOWN_TX_HASH}")
            w3 = connect()
            receipt = w3.eth.get_transaction_receipt(_KNOWN_TX_HASH)
            assert receipt is not None, \
                f"Known tx not found on chain: {_KNOWN_TX_HASH}"
            assert receipt["status"] == 1, \
                f"Known tx reverted on chain: {_KNOWN_TX_HASH}"
            _anchor_result = {
                "status":        "SUCCESS",
                "tx_hash":       _KNOWN_TX_HASH,
                "chain_id":      CHAIN_ID,
                "block_number":  receipt["blockNumber"],
                "gas_used":      receipt["gasUsed"],
                "evidence_hash": _TEST_EVIDENCE_HASH,
            }
        else:
            print(f"\n    Anchoring hash: {_TEST_EVIDENCE_HASH}")
            print("    Sending transaction to Base Sepolia (may take ~15s)...")
            result = anchor_evidence_hash(_TEST_EVIDENCE_HASH)
            assert result["status"] == "SUCCESS", \
                f"Expected SUCCESS, got: {result['status']}"
            assert result["chain_id"] == CHAIN_ID, \
                f"Wrong chain_id in result: {result['chain_id']}"
            assert result["evidence_hash"] == _TEST_EVIDENCE_HASH, \
                "evidence_hash in result does not match submitted hash"
            assert result["tx_hash"].startswith("0x"), \
                f"tx_hash malformed: {result['tx_hash']}"
            assert isinstance(result["block_number"], int) and result["block_number"] > 0, \
                f"Invalid block_number: {result['block_number']}"
            _anchor_result = result

        print(f"\n    TX Hash:      {_anchor_result['tx_hash']}")
        print(f"    Block Number: {_anchor_result['block_number']}")
        print(f"    Chain ID:     {_anchor_result['chain_id']}")
        print(f"    Gas Used:     {_anchor_result['gas_used']} gas units")
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 8 — On-chain readback: decode payload from confirmed tx
# ---------------------------------------------------------------------------
def test_onchain_readback():
    name = "On-chain readback"
    if _anchor_result is None:
        _fail(name, "Skipped: real transaction did not succeed")
        return
    try:
        from web3 import Web3
        w3 = connect()
        tx = w3.eth.get_transaction(_anchor_result["tx_hash"])

        raw_data = bytes(tx["input"])
        recovered = decode_evidence_payload(raw_data)

        assert recovered == _TEST_EVIDENCE_HASH, (
            f"Readback mismatch:\n"
            f"  expected:  {_TEST_EVIDENCE_HASH}\n"
            f"  recovered: {recovered}"
        )
        print(f"\n    On-chain hash: {recovered}")
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 9 — Hash verification: verify_on_chain -> VERIFIED
# ---------------------------------------------------------------------------
def test_hash_verification():
    name = "Hash verification"
    if _anchor_result is None:
        _fail(name, "Skipped: real transaction did not succeed")
        return
    try:
        result = verify_on_chain(
            _anchor_result["tx_hash"],
            _TEST_EVIDENCE_HASH,
        )

        assert result["status"] == "VERIFIED", \
            f"Expected VERIFIED, got {result['status']!r}. Full result: {result}"
        assert result["match"] is True, \
            f"match should be True, got {result['match']}"
        assert result["local_hash"] == _TEST_EVIDENCE_HASH, \
            "local_hash mismatch"
        assert result["on_chain_hash"] == _TEST_EVIDENCE_HASH, \
            "on_chain_hash mismatch"

        print(f"\n    Verification status: {result['status']}")
        print(f"    Local hash:          {result['local_hash']}")
        print(f"    On-chain hash:       {result['on_chain_hash']}")
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# TEST 10 — Tamper detection: wrong hash -> TAMPER_DETECTED
# ---------------------------------------------------------------------------
def test_tamper_detection():
    name = "Tamper detection"
    if _anchor_result is None:
        _fail(name, "Skipped: real transaction did not succeed")
        return
    try:
        # Provide a deliberately different local hash (flip one nibble)
        tampered_hash = "b" * 64

        result = verify_on_chain(
            _anchor_result["tx_hash"],
            tampered_hash,
        )

        assert result["status"] == "TAMPER_DETECTED", \
            f"Expected TAMPER_DETECTED, got {result['status']!r}"
        assert result["match"] is False, \
            f"match should be False, got {result['match']}"
        assert result["local_hash"] == tampered_hash, \
            "local_hash should reflect the (wrong) submitted hash"
        assert result["on_chain_hash"] != tampered_hash, \
            "on_chain_hash should differ from the tampered hash"

        print(f"\n    Tamper status:    {result['status']}")
        print(f"    match:            {result['match']}")
        print(f"    local (tampered): {result['local_hash']}")
        print(f"    on-chain:         {result['on_chain_hash']}")
        _pass(name)
    except Exception as e:
        _fail(name, str(e))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n========================================")
    print("  IMPRINT - BLOCKCHAIN TEST")
    print("========================================\n")

    test_configuration()
    test_connection()
    test_chain_id()
    test_wallet_key_match()
    test_payload_encode_decode()
    test_invalid_hash_validation()
    test_real_transaction()
    test_onchain_readback()
    test_hash_verification()
    test_tamper_detection()

    print("\n========================================")
    print("  RESULTS SUMMARY")
    print("========================================")

    ordered_labels = [
        "Configuration",
        "Base Sepolia connection",
        "Chain ID",
        "Wallet/private-key match",
        "Payload encode/decode",
        "Invalid hash validation",
        "Real transaction",
        "On-chain readback",
        "Hash verification",
        "Tamper detection",
    ]

    all_passed = True
    for label in ordered_labels:
        result = _results.get(label, "NOT RUN")
        print(f"  {label:<30} {result}")
        if result != "PASS":
            all_passed = False

    # Print safe transaction metadata if available
    if _anchor_result:
        print("\n----------------------------------------")
        print("  TRANSACTION METADATA (safe to share)")
        print("----------------------------------------")
        print(f"  TX Hash:       {_anchor_result['tx_hash']}")
        print(f"  Block Number:  {_anchor_result['block_number']}")
        print(f"  Chain ID:      {_anchor_result['chain_id']}")
        print(f"  Gas Used:      {_anchor_result['gas_used']} gas units")
        print(f"  Local Hash:    {_anchor_result['evidence_hash']}")
        print("----------------------------------------")

    print("\n========================================")
    if all_passed:
        print("  ALL BLOCKCHAIN TESTS PASSED")
    else:
        print("  SOME TESTS FAILED - review output above")
    print("========================================\n")

    sys.exit(0 if all_passed else 1)
