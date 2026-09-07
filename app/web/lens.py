import os
import requests
import json
from serpapi import GoogleSearch
from datetime import datetime

class GoogleLensSearch:
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")

    def _upload_to_catbox(self, image_path):
        """Upload local image to catbox.moe for a temporary public URL."""
        if not os.path.exists(image_path):
            return None, f"Local image not found: {image_path}"

        try:
            with open(image_path, "rb") as file:
                url = "https://catbox.moe/user/api.php"
                payload = {"reqtype": "fileupload"}
                files = {"fileToUpload": file}
                res = requests.post(url, data=payload, files=files, timeout=30)
                if res.status_code == 200:
                    return res.text, "Success"
                return None, f"Upload failed: HTTP {res.status_code} - {res.text}"
        except requests.exceptions.Timeout:
            return None, "Upload timed out."
        except requests.exceptions.RequestException as e:
            return None, f"Upload request error: {str(e)}"
        except Exception as e:
            return None, f"Unexpected upload error: {str(e)}"

    def search(self, image_source):
        """Search Google Lens using SerpApi."""
        if not self.api_key:
            return None, "SERPAPI_KEY not found in environment variables."

        image_url = image_source
        if os.path.exists(image_source):
            url, status = self._upload_to_catbox(image_source)
            if not url:
                return None, f"Image upload failed: {status}"
            image_url = url
        elif not image_source.startswith("http"):
            return None, "Invalid image source. Must be a local path or an HTTP URL."

        params = {
            "engine": "google_lens",
            "url": image_url,
            "api_key": self.api_key
        }

        try:
            search = GoogleSearch(params)
            # Add timeout handling for serpapi if possible, but python client handles its own requests
            results = search.get_dict()

            if "error" in results:
                return None, f"SerpApi Error: {results['error']}"

            visual_matches = results.get("visual_matches", [])

            parsed_results = []
            for match in visual_matches:
                parsed_results.append({
                    "provider": "serpapi_google_lens",
                    "result_type": "visual_match",
                    "url": match.get("link", ""),
                    "title": match.get("title", ""),
                    "image_url": match.get("thumbnail", ""),
                    "source": match.get("source", ""),
                    "retrieved_at": datetime.utcnow().isoformat()
                })

            # Save raw output
            artifacts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "artifacts", "web")
            os.makedirs(artifacts_dir, exist_ok=True)
            with open(os.path.join(artifacts_dir, "lens_raw.json"), "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)

            return parsed_results, "Success"

        except Exception as e:
            return None, f"SerpApi request failed: {str(e)}"
