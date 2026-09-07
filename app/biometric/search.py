import cv2
import os

from .detector import FaceDetector
from .embedder import FaceEmbedder
from .index import BiometricIndex


class BiometricSearch:
    def __init__(self, index_dir="data/index"):
        self.detector = FaceDetector()
        self.embedder = FaceEmbedder()
        self.biometric_index = BiometricIndex(index_dir=index_dir)

    def search(self, img, top_k=10):
        original_path = None

        if isinstance(img, str):
            original_path = os.path.abspath(img)
            img = cv2.imread(img)

            if img is None:
                return None, "Invalid image path"

        faces, status = self.detector.detect(img)

        if status != "Success" or len(faces) != 1:
            return None, "Invalid face or no face detected (or multiple faces)"

        face = faces[0]
        x, y, w, h = face[:4]

        if w < 30 or h < 30:
            return None, "Face too small/low quality"

        embedding = self.embedder.align_and_extract(img, face)

        results = self.biometric_index.search(
            embedding,
            top_k=top_k,
            exclude_source=original_path
        )

        identity_scores = {}

        for res in results:
            identity = res["meta"]["identity"]
            score = res["similarity"]

            if (
                identity not in identity_scores
                or score > identity_scores[identity]["best_score"]
            ):
                identity_scores[identity] = {
                    "best_score": score,
                    "best_template": res["meta"]["template_id"],
                    "source_image": res["meta"]["source_image"]
                }

        ranked_identities = sorted(
            identity_scores.items(),
            key=lambda x: x[1]["best_score"],
            reverse=True
        )

        formatted_results = []

        for rank, (identity, data) in enumerate(ranked_identities):
            formatted_results.append({
                "rank": rank + 1,
                "identity": identity,
                "template_id": data["best_template"],
                "similarity": data["best_score"],
                "source_image": data["source_image"]
            })

        return formatted_results, "Success"