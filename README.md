# IMPRINT — Hacker House Goa 2026 Task 3

IMPRINT is a multi-team pipeline that accepts a face image as input and produces a
cryptographically fingerprinted, blockchain-anchored evidence record.  It combines
biometric 1:N retrieval, live reverse-image web discovery, deterministic evidence
construction, and on-chain integrity verification — with no smart contracts.

---

## Architecture

Both the local presentation UI and the command-line runner sit directly above the existing pipeline and invoke the identical `execute_pipeline()` core function:

```
Local UI / CLI
       ↓
same execute_pipeline()
       ↓
Biometric → Web → Media → Evidence → SHA-256 → Base Sepolia → Readback
```

### End-to-End Pipeline Architecture

```
Local Demo UI (dashboard.py)         CLI Runner (run_pipeline.py)
              │                                    │
              └─────────────────┬──────────────────┘
                                │
                                ▼
                     same execute_pipeline()
                                │
                                ▼
                       Input face image
                                │
                                ▼
                      ┌───────────────────┐
                      │ YuNet face detect │  quality gate: exactly 1 face, min 30×30 px
                      └───────────────────┘
                                │
                                ▼
                      ┌───────────────────┐
                      │  SFace embedding  │  128-dim face descriptor via OpenCV DNN
                      └───────────────────┘
                                │
                                ▼
                      ┌───────────────────┐
                      │ FAISS 1:N search  │  FAISS inner-product search over L2-normalized SFace
                      └───────────────────┘  embeddings (with content-aware self-match exclusion)
                                │ biometric candidates (rank, identity, score, template)
                                │
                                ├──────────────────────────────────────────────────┐
                                │                                                  │
                                ▼                                                  ▼
                      ┌───────────────────┐                    ┌──────────────────────────┐
                      │  Google Lens /    │                    │  Candidate media         │
                      │  SerpApi live     │──► web candidates ─►  download + SHA-256      │
                      │  reverse-image    │                    └──────────────────────────┘
                      │  search           │                              │
                      └───────────────────┘                             │ candidate_media_sha256
                                │                                           │
                                └──────────────────┬────────────────────────┘
                                                   │
                                                   ▼
                                      ┌────────────────────────┐
                                      │  Evidence JSON         │  schema, version, input SHA-256,
                                      │  (build_evidence)      │  biometric candidates, web candidates,
                                      │                        │  verification state, provenance,
                                      │                        │  candidate_media_sha256
                                      └────────────────────────┘
                                                   │
                                                   ▼
                                      ┌────────────────────────┐
                                      │  Canonical JSON        │  sorted keys, compact separators,
                                      │  (canonicalize)        │  deterministic, UTF-8
                                      └────────────────────────┘
                                                   │
                                                   ▼
                                      ┌────────────────────────┐
                                      │  Evidence SHA-256      │  SHA-256(UTF-8(canonical JSON))
                                      └────────────────────────┘
                                                   │
                                                   ▼
                                      ┌────────────────────────┐
                                      │  Base Sepolia tx       │  EIP-1559, value = 0 ETH
                                      │  data = b"IMPRINT1"   │  40-byte payload:
                                      │        + 32-byte hash │  8-byte marker + 32-byte digest
                                      └────────────────────────┘
                                                   │
                                                   ▼
                                      ┌────────────────────────┐
                                      │  Transaction readback  │  fetch tx, decode payload,
                                      │  + hash comparison     │  compare local vs on-chain hash
                                      └────────────────────────┘
                                                   │
                                                   ▼
                                           EVIDENCE VERIFIED
```

The blockchain does not identify the person. It anchors the exact evidence record produced by the pipeline. If the evidence changes after anchoring, its SHA-256 changes and no longer matches the on-chain fingerprint.

> **Important — what "EVIDENCE VERIFIED" means:**
> The pipeline has produced a biometric 1:N candidate, independent live web
> evidence, a cryptographically fingerprinted evidence record, and confirmed that
> the on-chain hash matches the locally computed hash.  It does **not** perform
> separate 1:1 face verification and does **not** claim absolute proof of identity.

---

## Project Structure

```
imprint-biometric-evidence/
│
├── app/
│   ├── biometric/
│   │   ├── detector.py       # YuNet face detection wrapper
│   │   ├── embedder.py       # SFace embedding extraction
│   │   ├── enrollment.py     # Dataset → FAISS index builder
│   │   ├── index.py          # FAISS index read/write
│   │   └── search.py         # 1:N biometric search (BiometricSearch)
│   │
│   ├── web/
│   │   ├── __init__.py       # search_web() integration interface
│   │   ├── lens.py           # GoogleLensSearch via SerpApi
│   │   └── candidates.py     # CandidateProcessor (normalize, filter, download)
│   │
│   ├── evidence/
│   │   ├── __init__.py
│   │   └── evidence.py       # build_evidence, canonicalize, hash_evidence, sha256_file
│   │
│   ├── blockchain/
│   │   ├── __init__.py
│   │   └── base_sepolia.py   # anchor_evidence_hash, verify_on_chain
│   │
│   └── ui/
│       ├── __init__.py       # ImprintDashboard export
│       └── dashboard.py      # Tkinter/ttk local desktop presentation dashboard
│
├── models/
│   ├── yunet/                # YuNet face detection ONNX model
│   └── sface/                # SFace embedding ONNX model
│
├── scripts/
│   ├── test_search.py              # standalone biometric search test
│   ├── test_lens.py                # standalone Google Lens / web discovery test
│   ├── test_evidence.py            # evidence construction + hashing unit tests
│   ├── test_blockchain.py          # blockchain connection + payload + tx tests
│   ├── test_biometric_exclusion.py # biometric self-match exclusion regression test
│   ├── run_pipeline.py             # core pipeline & CLI runner (execute_pipeline)
│   └── run_ui.py                   # local desktop demo UI runner
│
├── data/
│   └── index/                # generated FAISS index (git-ignored)
│       ├── faiss.index
│       └── meta.json
│
├── artifacts/                # generated run output (git-ignored)
│   ├── web/candidates/       # downloaded candidate media
│   └── runs/                 # per-run evidence artifacts
│       └── run_<timestamp>/
│           ├── evidence.json
│           ├── evidence.canonical.json
│           ├── evidence.sha256
│           └── pipeline_result.json
│
├── .env.example              # template — copy to .env and fill in secrets
├── requirements.txt
└── README.md
```

---

## Local Demo UI

The project includes a local Tkinter/ttk desktop presentation UI designed for interactive demonstration and judging.

It is launched with:

```powershell
python scripts\run_ui.py
```

### Presentation Layer Over Existing Pipeline
- **Presentation layer only:** The UI is a presentation layer over the existing Python pipeline and directly invokes `execute_pipeline()`.
- **No duplicate logic:** It does not duplicate biometric, web, evidence, or blockchain logic.
- **Local-only:** The UI is local-only and runs completely on the local workstation using Python standard-library `tkinter` and `ttk`. No hosted website, web server, Node.js, npm, or frontend build tool is required.
- **Clean startup state:** The UI launches in a clean state (no preloaded image, all stage indicators `PENDING`, final status `READY TO VERIFY`, execution buttons disabled until an image is selected).

### UI Capabilities
- **Face image selection:** Interactive file picker with path normalization.
- **Input preview:** Scaled, aspect-ratio-preserving preview of the selected probe face.
- **Staged pipeline progress:** Real-time visual progress pills (`[1] INPUT` through `[6] READBACK`) updating live as each pipeline step executes.
- **Biometric candidate display:** Shows top retrieved candidate identity, similarity score, template ID, and rank.
- **Live web discovery result display:** Shows search provider, total results count, selected domain, and full candidate URL.
- **Candidate media fingerprint:** Confirms download status and displays the computed `candidate_media_sha256`.
- **Evidence SHA-256:** Displays the local cryptographic SHA-256 hash of the canonical evidence record.
- **Base Sepolia transaction details:** Displays transaction hash, confirmed block number, and gas consumed.
- **On-chain hash readback:** Displays the 32-byte hash recovered from on-chain transaction data.
- **Final EVIDENCE VERIFIED status:** Prominent visual banner confirming that local and on-chain hashes match byte-for-byte.
- **View Evidence:** Modal dialog to view the full formatted canonical evidence JSON artifact.
- **Open Source Result:** Button to open the discovered web source URL directly in the default web browser.

---

## Requirements

- Python **3.10 or later** (tested on 3.10–3.12)
- Windows PowerShell or compatible shell
- A funded Base Sepolia wallet (testnet ETH only)
- A valid [SerpApi](https://serpapi.com/) API key
- A Base Sepolia RPC URL — a public Base Sepolia RPC such as `https://sepolia.base.org` is given as the straightforward default (with services like [Alchemy](https://www.alchemy.com/) or [Infura](https://infura.io/) as optional alternatives)
- The LFW deep-funneled dataset (downloaded separately — not in Git)

---

## Installation

```powershell
# 1. Create virtual environment
python -m venv .venv

# 2. Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your real values:

```
SERPAPI_KEY=your_serpapi_key_here
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
WALLET_PRIVATE_KEY=your_64_hex_char_private_key
WALLET_ADDRESS=0xYourChecksumAddress
```

> ⚠️ **Security warnings:**
> - **Never commit `.env`** — it is listed in `.gitignore`.
> - **Never commit `WALLET_PRIVATE_KEY`** in any file or comment.
> - **Never put secrets in source code.**
> - **Never write secrets into evidence JSON or blockchain transactions.**
> - The pipeline writes zero secrets to on-chain data or artifact files.

---

## Dataset Setup

The [LFW (Labeled Faces in the Wild) deep-funneled dataset](http://vis-www.cs.umass.edu/lfw/)
is used for enrollment.  It is **not committed to Git** (listed in `.gitignore`).

Download and extract it so the directory structure is:

```
lfw-deepfunneled/
└── lfw-deepfunneled/
    ├── George_W_Bush/
    │   ├── George_W_Bush_0001.jpg
    │   └── ...
    ├── Arnold_Schwarzenegger/
    └── ...
```

### Build the FAISS Index

Run enrollment from the project root.  This processes every image in the dataset,
applies the YuNet quality gate (exactly 1 face, minimum 30×30 px), extracts SFace
embeddings, and saves a FAISS flat index:

```powershell
python -c "from app.biometric.enrollment import enroll_dataset; enroll_dataset('lfw-deepfunneled', 'data\index')"
```

The index files are written to `data/index/` (git-ignored):

```
data/index/faiss.index   # FAISS binary index
data/index/meta.json     # template metadata (identity, template_id, source_image)
```

Enrollment across the full LFW dataset (~13 000 images) takes a few minutes and
typically enrolls ~12 000–12 500 templates after the quality gate.

---

## Biometric Self-Match Protection

To ensure integrity during testing and live demonstrations, the biometric 1:N retrieval engine incorporates content-aware candidate exclusion.

The biometric search automatically excludes:
- Candidates at the **exact same normalized file path** as the probe.
- Candidates whose source file has the **exact same SHA-256 content** as the probe.

### Why Content-Aware Exclusion is Necessary
A simple file-path comparison only excludes an enrolled template if the probe is loaded from the exact same disk path. If an enrolled image is copied to a different folder or test path (for example, copying `George_W_Bush_0002.jpg` outside `lfw-deepfunneled/`), path-only comparison fails to recognize it as the same physical image. Without content-aware exclusion, the pipeline would retrieve its own enrolled template and report an artificial, trivial `1.0000` similarity self-match.

Excluding candidates with identical SHA-256 content ensures that exact duplicates at different paths are excluded, forcing FAISS to return true cross-image biometric matches (such as a different photograph of the same subject).

### Efficient Shortlist Hashing
Computing SHA-256 hashes across an entire database of ~13 000 images on every search query would introduce substantial delay. To prevent this:
1. FAISS performs fast vector retrieval first over L2-normalized embeddings.
2. SHA-256 content comparison is applied **only to the returned FAISS shortlist candidates**, rather than hashing the complete database on every search. This keeps search overhead negligible.

### Regression Testing
A dedicated standalone test validates the exclusion logic:

```powershell
python scripts\test_biometric_exclusion.py
```

The test covers:
- **Identical path exclusion:** Candidates at the identical filesystem path are excluded.
- **Identical-content copy at another path:** An identical image copied to an arbitrary path is excluded via SHA-256 match.
- **Different image with similar filename remains eligible:** Distinct images from the same subject are retained as valid candidates.
- **Missing candidate file handling:** Gracefully handles missing or deleted candidate files without raising exceptions.

---

## Web Discovery

Google Lens is queried **live** via [SerpApi](https://serpapi.com/) on every pipeline
run. There are no hardcoded URLs or cached results.

**How it works:**

1. The local probe image is transmitted to Catbox to obtain a public URL required
   by the current SerpApi workflow. This sends the probe image to a third-party
   service and should be avoided for sensitive images.
2. SerpApi submits the URL to the Google Lens engine and returns visual-match
   candidates.
3. Candidates are deduplicated by URL and image URL, and classified by domain.
4. Candidates matching the configured social-domain list (`instagram.com`,
   `facebook.com`, `x.com`, `twitter.com`, `linkedin.com`, `youtube.com`) are
   ranked above general web results. Note that YouTube is included in the current
   social-domain list.
5. The pipeline selects the first social/web candidate deterministically, or the
   first available candidate if no candidate matching the social-domain list is
   present.
6. The selected candidate's image is downloaded locally via
   `CandidateProcessor.download_image()`, which validates content-type and
   enforces a 5 MB size limit.
7. A SHA-256 fingerprint of the downloaded media is computed and included in the
   evidence provenance.

---

## Evidence

The evidence layer (`app/evidence/`) is independent of the biometric and web
internals.  It consumes plain Python dictionaries and produces a deterministic,
tamper-evident record.

**Evidence schema (`imprint.task3.evidence` v1):**

```json
{
  "schema":  "imprint.task3.evidence",
  "version": 1,
  "input":   { "image_sha256": "<64-hex>" },
  "biometric": {
    "candidates": [
      { "rank": 1, "identity": "...", "template_id": "...",
        "similarity": 0.8493, "source_image": "..." }
    ]
  },
  "web": {
    "provider": "serpapi_google_lens",
    "candidates": [ { "url": "...", "is_social": true, ... } ]
  },
  "verification": {
    "status": "SUPPORTED_MATCH",
    "biometric_top_identity": "...",
    "biometric_top_score": 0.8493,
    "web_candidate_available": true
  },
  "provenance": {
    "provider": "...",
    "source_url": "...",
    "source_domain": "...",
    "retrieved_at": "...",
    "candidate_media_sha256": "<64-hex>"
  }
}
```

**Canonicalization** uses `json.dumps` with `sort_keys=True`,
`separators=(",", ":")`, and `ensure_ascii=False` — fully deterministic across
Python versions and insertion orders.

**Evidence SHA-256** = `SHA-256(UTF-8(canonical JSON))` — any change to any field
produces a different hash.

---

## Blockchain

The blockchain layer (`app/blockchain/`) anchors evidence fingerprints on
**Base Sepolia** (chain ID `84532`) using standard EOA-to-EOA transactions.
No smart contract is deployed.

**Transaction payload (40 bytes, written to `data` field):**

```
Bytes 0–7  : b"IMPRINT1"       ← schema marker (ASCII)
Bytes 8–39 : <32 raw bytes>    ← SHA-256 digest (binary, not ASCII hex)
```

Only the fingerprint is stored on-chain.  Raw images, embeddings, API keys, private
keys, and full evidence JSON are **never** written to the blockchain.

**Transaction properties:**
- Type: EIP-1559 (type 2)
- From / To: same wallet address (self-transaction)
- Value: 0 ETH
- Gas: ~22 600 units (estimated per run)
- Network: Base Sepolia (testnet)

**Readback and verification:**
After the transaction is confirmed, the pipeline fetches it, decodes the 40-byte
payload, recovers the 32-byte hash, converts it to 64-character hex, and compares
it byte-for-byte with the locally computed evidence hash.  Only an exact match
produces `EVIDENCE VERIFIED`.

---

## Running Individual Tests

All scripts run from the **project root**.

### Biometric search

```powershell
python scripts\test_search.py "<path\to\probe.jpg>"
```

Requires the FAISS index (`data/index/`) to be built first.

### Biometric self-match exclusion test

```powershell
python scripts\test_biometric_exclusion.py
```

No network or external API keys required. Verifies that identical paths and identical-content copies at different paths are excluded from candidate results, distinct images remain eligible, and missing candidate files are handled gracefully.

### Web discovery (Google Lens)

```powershell
python scripts\test_lens.py "<path\to\probe.jpg>"
```

Requires `SERPAPI_KEY` in `.env`.

### Evidence unit tests

```powershell
python scripts\test_evidence.py
```

No network access required.  Tests canonicalization, determinism, mutation
detection, insertion-order independence, file SHA-256, and validation.

### Blockchain tests

```powershell
python scripts\test_blockchain.py
```

Requires `BASE_SEPOLIA_RPC_URL`, `WALLET_ADDRESS`, and `WALLET_PRIVATE_KEY` in
`.env`.

> ⚠️ `test_blockchain.py` **reuses a previously confirmed transaction** embedded
> as `_KNOWN_TX_HASH` in the script.  It does **not** send a new transaction on
> normal re-runs.  To force a fresh anchor, set `_KNOWN_TX_HASH = None` in the
> script.

---

## End-to-End Pipeline

```powershell
python scripts\run_pipeline.py "<path\to\probe.jpg>"
```

**Stages executed on each run:**

| Stage | Description |
|-------|-------------|
| `[1] INPUT` | Validate file exists, compute input image SHA-256 |
| `[2] BIOMETRIC 1:N` | YuNet detect → SFace embed → FAISS search (top-5) |
| `[3] WEB DISCOVERY` | Live Google Lens via SerpApi, candidate selection |
| `[3A] CANDIDATE MEDIA` | Download selected candidate image, compute SHA-256 |
| `[4] EVIDENCE` | build_evidence → canonicalize → SHA-256 |
| `[5] BLOCKCHAIN` | anchor_evidence_hash → one new Base Sepolia tx |
| `[6] READBACK` | verify_on_chain → local hash vs on-chain hash |

> ⚠️ **Each successful end-to-end run sends exactly one real Base Sepolia
> transaction.**  Do not run the pipeline in a loop; testnet ETH is consumed.

All stages must succeed for the final status `EVIDENCE VERIFIED` to be printed.
Any failure aborts cleanly with a descriptive message and a non-zero exit code.

---

## Final Demonstration Flow

The recommended sequence for evaluating or demonstrating the complete end-to-end system:

```
Select Face Image
       ↓
Run Pipeline
       ↓
Biometric 1:N
       ↓
Live Google Lens
       ↓
Candidate Media
       ↓
Evidence
       ↓
Base Sepolia
       ↓
Readback
       ↓
EVIDENCE VERIFIED
```

### Demonstration Steps:
1. **Launch Interface:** Run `python scripts\run_ui.py` for the desktop dashboard (or run headless via `python scripts\run_pipeline.py "<path\to\probe.jpg>"`).
2. **Select Face Image:** Click **Select Face Image** to select an input face image (e.g., `George_W_Bush_0002.jpg`). The preview renders and the Run button activates.
3. **Run Pipeline:** Click **Run Pipeline** to execute `execute_pipeline()`.
4. **Biometric 1:N:** YuNet validates single-face quality, SFace extracts the 128-d descriptor, and FAISS returns the top candidate ranking with content-aware self-match exclusion active.
5. **Live Google Lens:** SerpApi queries Google Lens live with the probe, discovering visual matches across web and social platforms without hardcoded responses.
6. **Candidate Media Fingerprint:** The top candidate image is downloaded, verified, and hashed to produce `candidate_media_sha256`.
7. **Canonical Evidence Construction:** The structured record (`imprint.task3.evidence` v1) is assembled, canonicalized, and hashed to produce the `evidence_sha256` digest.
8. **Base Sepolia Anchoring:** An EIP-1559 0-ETH transaction is broadcast to Base Sepolia carrying the 40-byte payload (`b"IMPRINT1"` marker + 32-byte binary digest).
9. **On-Chain Readback:** The mined transaction is retrieved from Base Sepolia, the input payload is decoded, and the recovered 32-byte digest is verified against the local hash.
10. **EVIDENCE VERIFIED:** Both hashes match exactly, confirming end-to-end cryptographic integrity. Click **View Evidence** to inspect the record or **Open Source Result** to inspect the live web candidate.

---

## Artifacts

All generated output is written to `artifacts/` (git-ignored):

```
artifacts/
├── web/candidates/           # downloaded candidate media (jpg)
│   └── <uuid>.jpg
└── runs/
    └── run_<YYYYMMDDTHHMMSSz>/
        ├── evidence.json             # full evidence record (pretty-printed)
        ├── evidence.canonical.json   # compact deterministic JSON used for hashing
        ├── evidence.sha256           # plain-text 64-char SHA-256 digest
        └── pipeline_result.json      # pipeline metadata + blockchain reference
```

**Secrets are never stored in artifact files.**  `pipeline_result.json` contains
only public metadata: tx hash, block number, chain ID, gas used, evidence hash, and
candidate media SHA-256.

---

## Security

- `.env` is git-ignored and must never be committed.
- `WALLET_PRIVATE_KEY` is read from the environment at runtime only and is never
  logged, printed, or written to any file.
- No raw biometric data (face images, embeddings) is stored on-chain.
- No API keys are stored on-chain or in evidence JSON.
- Candidate media download enforces a content-type check (`image/*`) and a 5 MB
  size limit.
- The local probe image is transmitted to Catbox to obtain a public URL required
  by the current SerpApi workflow. This sends the probe image to a third-party
  service and should be avoided for sensitive images.
- The blockchain payload is exactly 40 bytes — only the evidence fingerprint.

---

## Limitations

1. **FAISS 1:N is retrieval, not identity proof.**  The biometric component performs
   FAISS inner-product search over L2-normalized SFace embeddings, equivalent to
   cosine similarity.  A high score indicates a plausible candidate, not a
   verified identity.

2. **No 1:1 face verification.**  The current implementation does not compare the
   probe face against a known reference face for the retrieved identity.  Adding
   1:1 verification is a planned future step.

3. **Web evidence depends on external availability.**  Google Lens results vary with
   image content, SerpApi quota, and web availability at query time.  A different
   run of the same image may return different candidates.

4. **Third-party public upload.**  The local probe image is transmitted to Catbox
   to obtain a public URL required by the current SerpApi workflow. This sends the
   probe image to a third-party service and should be avoided for sensitive
   images.

5. **Dataset and index not in Git.**  The LFW dataset and generated FAISS index
   (`data/index/`) must be set up locally.  Results depend on which identities
   were enrolled.

6. **Candidate media availability may vary.**  Web images may become unavailable
   or change after indexing.

7. **Blockchain proves fingerprint integrity, not factual truth.**  The on-chain
   record proves that the evidence hash has not been altered since it was anchored.
   It does not independently verify the accuracy of the biometric result or the
   web candidate.

8. **Testnet only.**  Base Sepolia is a public test network.  Transactions use
   testnet ETH only and have no real monetary value.

---

## Reproducibility

To reproduce a pipeline run you need:

- Identical Python environment and `requirements.txt` dependencies
- Identical ONNX model files in `models/`
- Identical FAISS index built from the same dataset and enrollment parameters
- A funded Base Sepolia wallet
- A valid SerpApi API key
- A live internet connection (Google Lens results are fetched at runtime)

The evidence SHA-256 will differ between runs because the live Google Lens
response, candidate selection, and downloaded media content are not static.

---

## Demonstrated Run (Historical Example)

The following values are from a verified working run and are shown for
illustrative purposes only.  They are **not hardcoded** in any implementation file.

```
Input image:    George_W_Bush_0002.jpg
Input SHA-256:  6ff1a77e676637ae94117f1a67755fae126b0891f5d13e3cf675b8757e930a94

[2] BIOMETRIC 1:N
    Top candidate:   George_W_Bush
    Similarity:      0.8493
    Template:        George_W_Bush_George_W_Bush_0521.jpg

[3] WEB DISCOVERY
    Provider:        Google Lens / SerpApi
    Result count:    59
    Selected source: YouTube
    Selected URL:    https://www.youtube.com/watch?v=YaSy2Yoex3E
    Is social:       True

[3A] CANDIDATE MEDIA
    Download:        SUCCESS
    Media SHA-256:   fa0fb20567c5b879f27ec579df8ab8f0fb8b136e36b3e2b5a74b6f984bf7d116

[4] EVIDENCE
    Evidence SHA-256: aea2aa3f2383006aef1eb5b509f6c5f87d5df47c88fde80362e8b5e0de258d66

[5] BLOCKCHAIN  (Base Sepolia)
    Transaction:  0x68b7de51b866b229576c762e038277cd21f2699ba50bf659be14338c8ab64536
    Block:        46514904
    Gas Used:     22570 gas units

[6] READBACK
    Hash match:   TRUE

FINAL STATUS: EVIDENCE VERIFIED
```

---

## Team

| Module | Contributor |
|--------|-------------|
| Biometric core (YuNet + SFace + FAISS) | Khushi |
| Web discovery (Google Lens + SerpApi + CandidateProcessor) | Samidha |
| Evidence + Blockchain (evidence.py + base_sepolia.py + pipeline) | Disha |

---

*IMPRINT — Hacker House Goa 2026 Task 3 — branch: disha-blockchain*
