import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path to allow app module import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.web import search_web
from app.web.candidates import CandidateProcessor

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_lens.py <image_path>")
        sys.exit(1)
        
    image_path = sys.argv[1]
    
    # Load environment variables
    load_dotenv()
    
    if not os.path.exists(image_path):
        print(f"Error: Image {image_path} not found.")
        sys.exit(1)
        
    print("=" * 50)
    print("IMPRINT — WEB DISCOVERY TEST")
    print("=" * 50)
    print(f"\nInput:\n{os.path.basename(image_path)}\n")
    print("Provider:\nGoogle Lens / SerpApi\n")
    
    print("Performing search...")
    result = search_web(image_path)
    
    if result["status"] == "ERROR":
        print(f"Search:\nFAILED - {result.get('message')}")
        sys.exit(1)
        
    print(f"Search:\nSUCCESS\n")
    
    candidates = result.get("candidates", [])
    print(f"Results:\n{result['result_count']}\n")
    
    print("SOCIAL / WEB CANDIDATES")
    print("-" * 50)
    
    for i, c in enumerate(candidates[:5]):
        print(f"[{i+1}]")
        print(f"Title: {c.get('title')}")
        source_type = "Social" if c.get('is_social') else "Web"
        source = c.get('source') or source_type
        print(f"Source: {source}")
        print(f"URL: {c.get('url')}")
        print(f"Image URL: {c.get('image_url')}\n")
        
    print("MEDIA RETRIEVAL")
    print("-" * 50)
    
    if not candidates:
        print("No candidates available for media retrieval.")
    else:
        processor = CandidateProcessor()
        top_candidate = candidates[0]
        print(f"Candidate 1: Attempting download...")
        filepath, msg = processor.download_image(top_candidate.get('image_url'))
        if filepath:
            print(f"Candidate 1: SUCCESS")
            print(f"Saved: {filepath}")
        else:
            print(f"Candidate 1: FAILED - {msg}")
            
    print("\nWEB DISCOVERY COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    main()
