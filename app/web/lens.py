import os
import requests
from serpapi import GoogleSearch
from datetime import datetime

class GoogleLensSearch:
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
        
    def _upload_to_catbox(self, image_path):
        with open(image_path, "rb") as file:
            url = "https://catbox.moe/user/api.php"
            payload = {
                "reqtype": "fileupload",
            }
            files = {
                "fileToUpload": file
            }
            res = requests.post(url, data=payload, files=files)
            if res.status_code == 200:
                return res.text, "Success"
            return None, f"Upload failed: {res.text}"

    def search(self, image_source):
        if not self.api_key:
            return None, "SERPAPI_KEY not found in environment"

        image_url = image_source
        if os.path.exists(image_source):
            # It's a local file
            url, status = self._upload_to_catbox(image_source)
            if not url:
                return None, status
            image_url = url
            
        params = {
            "engine": "google_lens",
            "url": image_url,
            "api_key": self.api_key
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # extract visual matches
            visual_matches = results.get("visual_matches", [])
            
            parsed_results = []
            for match in visual_matches:
                parsed_results.append({
                    "provider": "google_lens",
                    "result_type": "visual_match",
                    "url": match.get("link"),
                    "title": match.get("title"),
                    "image_url": match.get("thumbnail"),
                    "source": match.get("source"),
                    "retrieved_at": datetime.utcnow().isoformat()
                })
                
            # save raw output
            import json
            os.makedirs("evidence", exist_ok=True)
            with open("evidence/raw_search.json", "w") as f:
                json.dump(results, f, indent=2)
                
            return parsed_results, "Success"
            
        except Exception as e:
            return None, str(e)
