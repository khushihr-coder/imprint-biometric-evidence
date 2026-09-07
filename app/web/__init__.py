from .lens import GoogleLensSearch
from .candidates import CandidateProcessor

def search_web(image_path: str):
    """
    Complete Web Discovery integration interface.
    1. Search Google Lens
    2. Process and normalize candidates
    3. Return a structured dictionary for the orchestrator
    """
    searcher = GoogleLensSearch()
    raw_candidates, search_status = searcher.search(image_path)
    
    if raw_candidates is None:
        return {
            "status": "ERROR",
            "message": search_status,
            "provider": "serpapi_google_lens",
            "result_count": 0,
            "candidates": []
        }
        
    processor = CandidateProcessor()
    filtered_candidates = processor.filter_social_candidates(raw_candidates)
    
    return {
        "status": "SUCCESS",
        "provider": "serpapi_google_lens",
        "result_count": len(filtered_candidates),
        "candidates": filtered_candidates
    }
