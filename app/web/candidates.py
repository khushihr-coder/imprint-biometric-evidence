import os
import requests
import uuid
import cv2
from urllib.parse import urlparse

class CandidateProcessor:
    def __init__(self, download_dir="data/candidates"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        
    def filter_social_candidates(self, results):
        social_domains = ['facebook.com', 'instagram.com', 'x.com', 'twitter.com', 'linkedin.com', 'youtube.com', 'wikipedia.org', 'imdb.com']
        candidates = []
        for res in results:
            domain = urlparse(res['url']).netloc.lower()
            res['domain'] = domain
            
            # Prioritize known domains if possible, or just accept if it has an image_url
            is_social = any(sd in domain for sd in social_domains)
            res['is_social'] = is_social
            
            if res.get('image_url'):
                candidates.append(res)
                
        # sort by social first
        candidates.sort(key=lambda x: x['is_social'], reverse=True)
        return candidates

    def download_image(self, url):
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                ext = "jpg" 
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(self.download_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(res.content)
                
                img = cv2.imread(filepath)
                if img is None:
                    os.remove(filepath)
                    return None, "Downloaded file is not a valid image"
                    
                return filepath, "Success"
            return None, f"HTTP {res.status_code}"
        except Exception as e:
            return None, str(e)
