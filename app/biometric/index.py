import faiss
import numpy as np
import json
import os
import hashlib


def sha256_file(filepath):
    """Compute SHA-256 hex digest of a file in binary chunks."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def should_exclude_candidate(probe_path, candidate_source, probe_hash=None, hash_cache=None):
    """
    Determine if candidate_source should be excluded as a self-match against probe_path.

    Exclusion criteria:
    1. Fast path: probe_path equals candidate_source (normalized absolute paths).
    2. Content check: probe SHA-256 equals candidate source-image SHA-256.
       - Only candidate files that exist locally are hashed.
       - Caches computed hashes if hash_cache dict is provided.
       - Falls back gracefully to False if candidate source does not exist locally.
    """
    if not probe_path or not candidate_source:
        return False

    # 1. Fast path: normalized absolute path equality
    probe_abs = os.path.normcase(os.path.abspath(probe_path))
    cand_abs = os.path.normcase(os.path.abspath(candidate_source))
    if probe_abs == cand_abs:
        return True

    # 2. Content check: probe file must exist on disk
    if not os.path.isfile(probe_path):
        return False

    if probe_hash is None:
        try:
            probe_hash = sha256_file(probe_path)
        except Exception:
            return False

    # Resolve candidate file path locally
    cand_path = candidate_source
    if not os.path.isfile(cand_path):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        alt_path = os.path.join(repo_root, candidate_source)
        if os.path.isfile(alt_path):
            cand_path = alt_path
        elif not os.path.isabs(cand_path):
            cand_path = os.path.abspath(cand_path)

    if not os.path.isfile(cand_path):
        # Candidate file does not exist locally; fall back to path-based check (already False)
        return False

    # Retrieve or compute candidate hash
    cand_hash = None
    if hash_cache is not None and cand_path in hash_cache:
        cand_hash = hash_cache[cand_path]
    else:
        try:
            cand_hash = sha256_file(cand_path)
            if hash_cache is not None:
                hash_cache[cand_path] = cand_hash
        except Exception:
            return False

    return cand_hash == probe_hash


class BiometricIndex:
    def __init__(self, index_dir="data/index", dim=128):
        self.index_dir = index_dir
        self.dim = dim

        self.index_path = os.path.join(index_dir, "faiss.index")
        self.meta_path = os.path.join(index_dir, "meta.json")

        self.index = faiss.IndexFlatIP(dim)
        self.metadata = []

        os.makedirs(index_dir, exist_ok=True)
        self.load()

    def add(self, embedding, meta):
        embedding = np.asarray(embedding, dtype=np.float32).reshape(-1)

        norm = np.linalg.norm(embedding)

        if norm > 0:
            embedding = embedding / norm

        if embedding.shape != (self.dim,):
            raise ValueError(
                f"Invalid embedding dimension: expected {self.dim}, "
                f"got {embedding.shape}"
            )

        self.index.add(np.array([embedding], dtype=np.float32))
        self.metadata.append(meta)

    def search(self, query_embedding, top_k=10, exclude_source=None):
        query_embedding = np.asarray(
            query_embedding, dtype=np.float32
        ).reshape(-1)

        norm = np.linalg.norm(query_embedding)

        if norm > 0:
            query_embedding = query_embedding / norm

        if query_embedding.shape != (self.dim,):
            raise ValueError(
                f"Invalid query dimension: expected {self.dim}, "
                f"got {query_embedding.shape}"
            )

        if self.index.ntotal == 0:
            return []

        search_k = min(top_k + 20, self.index.ntotal)

        similarities, indices = self.index.search(
            np.array([query_embedding], dtype=np.float32),
            search_k
        )

        probe_hash = None
        hash_cache = {}

        if exclude_source is not None and isinstance(exclude_source, str) and os.path.isfile(exclude_source):
            try:
                probe_hash = sha256_file(exclude_source)
            except Exception:
                probe_hash = None

        results = []

        for sim, idx in zip(similarities[0], indices[0]):

            if idx == -1 or idx >= len(self.metadata):
                continue

            meta = self.metadata[idx]
            indexed_source = meta.get("source_image")

            if exclude_source and indexed_source:
                if should_exclude_candidate(
                    exclude_source,
                    indexed_source,
                    probe_hash=probe_hash,
                    hash_cache=hash_cache
                ):
                    continue

            results.append({
                "similarity": float(sim),
                "meta": meta
            })

            if len(results) >= top_k:
                break

        return results


    def save(self):
        faiss.write_index(self.index, self.index_path)

        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

    def load(self):
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            self.index = faiss.read_index(self.index_path)

            with open(self.meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)