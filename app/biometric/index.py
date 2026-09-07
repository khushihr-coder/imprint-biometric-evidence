import faiss
import numpy as np
import json
import os


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

        exclude_source_abs = None

        if exclude_source is not None:
            exclude_source_abs = os.path.normcase(
                os.path.abspath(exclude_source)
            )

        results = []

        for sim, idx in zip(similarities[0], indices[0]):

            if idx == -1 or idx >= len(self.metadata):
                continue

            meta = self.metadata[idx]
            indexed_source = meta.get("source_image")

            if exclude_source_abs and indexed_source:
                indexed_source_abs = os.path.normcase(
                    os.path.abspath(indexed_source)
                )

                if indexed_source_abs == exclude_source_abs:
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