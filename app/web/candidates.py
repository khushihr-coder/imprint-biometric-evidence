import os
import requests
import uuid
import cv2
from urllib.parse import urlparse

class CandidateProcessor:
    def __init__(self, download_dir=None):
        if download_dir is None:
            # default to artifacts/web/candidates
            self.download_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "artifacts", "web", "candidates")
        else:
            self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        
    def normalize_candidates(self, results):
        """Normalize candidates and remove duplicates based on URL or Image URL."""
        seen_urls = set()
        seen_image_urls = set()
        normalized = []
        
        for res in results:
            url = res.get('url')
            image_url = res.get('image_url')
            
            # Skip candidates with no useful links
            if not url and not image_url:
                continue
                
            if url in seen_urls and url != "":
                continue
            if image_url in seen_image_urls and image_url != "":
                continue
                
            if url: seen_urls.add(url)
            if image_url: seen_image_urls.add(image_url)
            
            domain = urlparse(url).netloc.lower() if url else ""
            res['domain'] = domain
            
            normalized.append(res)
            
        return normalized

    def filter_social_candidates(self, results):
        """Identify social domain candidates and rank them higher."""
        social_domains = ['instagram.com', 'facebook.com', 'x.com', 'twitter.com', 'linkedin.com', 'youtube.com']
        
        normalized = self.normalize_candidates(results)
        candidates = []
        
        for res in normalized:
            domain = res.get('domain', '')
            
            is_social = any(domain.endswith(sd) for sd in social_domains)
            res['is_social'] = is_social
            
            # Keep if we have an image URL
            if res.get('image_url'):
                candidates.append(res)
                
        # Sort by social first
        candidates.sort(key=lambda x: x['is_social'], reverse=True)
        return candidates

    def download_image(self, url, max_size_bytes=5*1024*1024):
        """Safely download candidate image with timeout and size limits."""
        if not url:
            return None, "No URL provided"
            
        try:
            # Stream the request to check size and content type before fully downloading
            with requests.get(url, stream=True, timeout=10) as res:
                if res.status_code != 200:
                    return None, f"HTTP {res.status_code}"
                
                content_type = res.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    return None, f"Invalid content type: {content_type}"
                    
                content_length = res.headers.get('Content-Length')
                if content_length and int(content_length) > max_size_bytes:
                    return None, f"File too large: {content_length} bytes"
                    
                ext = "jpg" 
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(self.download_dir, filename)
                
                downloaded_size = 0
                with open(filepath, 'wb') as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        if chunk:
                            downloaded_size += len(chunk)
                            if downloaded_size > max_size_bytes:
                                os.remove(filepath)
                                return None, "File exceeded max size during download"
                            f.write(chunk)
                
                # Verify it is actually an image that cv2 can read
                img = cv2.imread(filepath)
                if img is None:
                    os.remove(filepath)
                    return None, "Downloaded file is not a valid image format"
                    
                return filepath, "Success"
                
        except requests.exceptions.Timeout:
            return None, "Download timed out"
        except requests.exceptions.RequestException as e:
            return None, f"Download request error: {str(e)}"
        except Exception as e:
            return None, f"Unexpected download error: {str(e)}"
