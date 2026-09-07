import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.biometric.search import BiometricSearch


def run_test():
    if len(sys.argv) < 2:
        print("Usage: python scripts\\test_search.py <image_path>")
        return

    probe_img = sys.argv[1]

    searcher = BiometricSearch(index_dir="data/index")

    print(f"Running search for probe: {probe_img}")

    results, status = searcher.search(probe_img, top_k=5)

    if status != "Success":
        print(f"Search failed: {status}")
        return

    print("\nTop-K Candidates:")
    for res in results:
        print(f"Rank {res['rank']}: {res['identity']} (Score: {res['similarity']:.4f})")
        print(f"  Template: {res['template_id']}")
        print(f"  Source: {res['source_image']}")


if __name__ == "__main__":
    run_test()