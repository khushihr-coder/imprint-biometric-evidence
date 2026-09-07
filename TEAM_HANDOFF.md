# IMPRINT — Hacker House Goa 2026 Task 3
## Team Backend Handoff

Team:
- Khushi — Biometric Identification + Integration
- Samidha — Web / Google Lens Discovery
- Disha — Evidence + Blockchain

---

# 1. Current Project Status

The project is implementing a biometric evidence and verification pipeline for Hacker House Goa 2026 Task 3.

Current architecture:

Input Face
    ↓
YuNet Face Detection
    ↓
SFace Face Embedding
    ↓
FAISS 1:N Biometric Search
    ↓
Parallel:
    ├── Web / Google Lens Discovery
    └── Biometric Candidate Retrieval
    ↓
Candidate Fusion
    ↓
SFace 1:1 Verification
    ↓
Canonical Evidence JSON
    ↓
SHA-256
    ↓
Base Sepolia Blockchain
    ↓
On-chain Readback
    ↓
Integrity Verification

---

# 2. KHUSHI — COMPLETED

The biometric identification core has been implemented and tested.

Files:

app/biometric/detector.py
app/biometric/embedder.py
app/biometric/enrollment.py
app/biometric/index.py
app/biometric/search.py

Test:

scripts/test_search.py

Models:

models/sface/face_recognition_sface_2021dec.onnx
models/yunet/face_detection_yunet_2023mar.onnx

---

# 3. Biometric Pipeline

The biometric pipeline performs:

1. Face detection using YuNet.
2. Basic face quality validation.
3. Face alignment.
4. SFace embedding extraction.
5. Embedding normalization.
6. FAISS inner-product search.
7. Identity-level aggregation.
8. Ranking of candidate identities.

The FAISS index contains multiple templates for enrolled identities.

The search excludes the exact probe image during validation so that an identical-image match does not falsely demonstrate recognition.

---

# 4. Verified Result

Probe:

George_W_Bush_0002.jpg

The exact probe image was excluded from the FAISS search.

Result:

Rank 1: George_W_Bush
Score: 0.8492

Matched template:

George_W_Bush_0521.jpg

This demonstrates cross-template 1:N biometric retrieval rather than exact self-image retrieval.

---

# 5. Dataset

The project uses the locally downloaded LFW dataset.

Expected structure:

lfw-deepfunneled/
└── lfw-deepfunneled/
    ├── George_W_Bush/
    ├── ...
    └── other identities/

The dataset is intentionally NOT committed to GitHub.

Each team member must have the dataset locally.

The FAISS enrollment/index was generated from this local dataset.

Do not rerun enrollment unnecessarily because doing so against an existing index may append duplicate templates.

---

# 6. SAMIDHA — WEB DISCOVERY

Samidha owns:

app/web/lens.py
app/web/candidates.py

There is already a SerpApi / Google Lens skeleton.

The current implementation expects:

SERPAPI_KEY

from the local .env file.

Do NOT commit the API key.

Required flow:

Probe image
    ↓
SerpApi Google Lens
    ↓
Real reverse-image results
    ↓
Candidate web pages/images
    ↓
Identify social-media candidate
    ↓
Retrieve/download candidate image
    ↓
Return structured candidate data

The result should contain fields such as:

{
    "title": "...",
    "url": "...",
    "source": "...",
    "image_url": "...",
    "thumbnail_url": "..."
}

The result must be genuine.

Do NOT hardcode a social-media result.

The final system must be able to demonstrate that the web result came from the reverse-image search process.

---

# 7. DISHA — EVIDENCE + BLOCKCHAIN

Disha owns the evidence and blockchain layer.

Required flow:

Biometric result
+
Web candidate
+
Verification result
    ↓
Canonical JSON
    ↓
SHA-256
    ↓
Base Sepolia transaction
    ↓
Transaction hash
    ↓
Read transaction/data back
    ↓
Recompute local hash
    ↓
Compare local hash with on-chain hash

The blockchain should store the cryptographic fingerprint/hash of the evidence rather than unnecessary raw biometric information.

Required verification condition:

LOCAL SHA-256
=
ON-CHAIN SHA-256

If they differ:

VERIFICATION FAILED

If they match:

VERIFICATION PASSED

Private keys must NEVER be committed to GitHub.

---

# 8. FINAL INTEGRATION

After Samidha and Disha finish their independent modules, integrate them with the biometric engine.

Final flow:

INPUT IMAGE
    ↓
YuNet
    ↓
SFace
    ↓
FAISS 1:N
    ↓
Biometric Candidates

                 +
                 
Google Lens / SerpApi
    ↓
Web Candidates

                 ↓

Candidate Fusion
    ↓
Candidate Media Retrieval
    ↓
SFace 1:1 Verification
    ↓
Evidence Record
    ↓
Canonical JSON
    ↓
SHA-256
    ↓
Base Sepolia
    ↓
Readback
    ↓
Final Verification

---

# 9. Important Design Rule

The biometric branch and web branch are independent evidence sources.

The system should not automatically claim identity simply because one source produces a candidate.

The strongest result is:

Biometric candidate
+
Independent web evidence
+
1:1 face verification
+
Immutable evidence hash

If the sources disagree, the system should be able to report an inconclusive/conflict state rather than silently forcing a match.

---

# 10. Running the Biometric Search

From the project root:

python scripts\test_search.py "lfw-deepfunneled\lfw-deepfunneled\George_W_Bush\George_W_Bush_0002.jpg"

Expected type of result:

Rank 1: George_W_Bush
Score: approximately 0.85
Matched template: another George_W_Bush image

The exact score can vary depending on the probe/template.

---

# 11. Security

NEVER commit:

.env
API keys
private blockchain keys
large datasets
virtual environments

Use .env locally.

Example:

SERPAPI_KEY=your_key_here

The actual value must never appear in GitHub.

---

# 12. Current Ownership

KHUSHI:
- YuNet
- SFace
- FAISS
- 1:N biometric search
- biometric testing
- final integration
- final local demonstration

SAMIDHA:
- Google Lens / SerpApi
- reverse-image search
- real web/social candidates
- candidate image retrieval
- web-search testing

DISHA:
- evidence schema
- canonical JSON
- SHA-256
- Base Sepolia
- blockchain readback
- integrity verification
- security/test documentation

---

# 13. Integration Priority

Do not spend time redesigning the biometric engine.

The biometric core is already functional.

Priority now:

1. Make Google Lens / SerpApi work.
2. Make blockchain hashing/write/read work.
3. Connect biometric + web results.
4. Perform 1:1 candidate verification.
5. Generate evidence JSON.
6. Hash evidence.
7. Anchor hash on Base Sepolia.
8. Read it back and verify.
9. Test the complete pipeline.
10. Prepare the screen recording.

---

# 14. Competition Requirement

The final demonstration must show a real end-to-end execution.

No fake:

- social result
- blockchain transaction
- hash
- verification result

The GitHub repository and screen recording should contain the actual implementation and execution evidence.