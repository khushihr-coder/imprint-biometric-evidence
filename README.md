# IMPRINT — Hacker House Goa 2026 Task 3

## Project Overview

IMPRINT is a pipeline for biometric identification, cross-referencing web evidence via Google Lens, and anchoring the results onto a blockchain (Base Sepolia) for immutable verification.

## Web Discovery Module

The Web Discovery module performs a genuine reverse-image search using Google Lens via SerpApi. Its purpose is to independently find web and social media candidates matching the probe image. This serves as an independent evidence source that will be combined with the biometric results to establish a candidate identity.

**Important Note**: The Web Discovery module only discovers "candidates". It does not claim that an identity is "verified".

### Environment Variable Setup

The module requires a real SerpApi API key.
Copy `.env.example` to `.env` and configure your API key:
```
SERPAPI_KEY=your_serpapi_key_here
```
**Never commit the `.env` file or your API keys.**

### Running the Test

To test the Web Discovery module independently:

```bash
python scripts/test_lens.py "lfw-deepfunneled/lfw-deepfunneled/George_W_Bush/George_W_Bush_0002.jpg"
```

### Expected Output

The test script will:
1. Temporarily host the local image.
2. Call the real SerpApi Google Lens engine.
3. Save the raw response to `artifacts/web/lens_raw.json`.
4. Parse and normalize the candidates, filtering duplicates and identifying social media links.
5. Rank social domain candidates higher.
6. Attempt to securely download the top candidate image, validating the content-type and size.
7. Print a formatted summary to the console.

### Integration Interface

For final integration with the orchestrator, use:
```python
from app.web import search_web
result = search_web(image_path)
```
This returns a structured dictionary containing `status`, `result_count`, and a `candidates` list.
