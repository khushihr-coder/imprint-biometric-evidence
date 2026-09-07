import os
import cv2
from .detector import FaceDetector
from .embedder import FaceEmbedder
from .index import BiometricIndex

def enroll_dataset(dataset_dir, index_dir="data/index"):
    detector = FaceDetector()
    embedder = FaceEmbedder()
    biometric_index = BiometricIndex(index_dir=index_dir)
    
    total_images = 0
    enrolled_templates = 0
    
    # Check if dataset dir is the outer one or inner one
    if os.path.isdir(os.path.join(dataset_dir, "lfw-deepfunneled")):
        dataset_dir = os.path.join(dataset_dir, "lfw-deepfunneled")
        
    identities = os.listdir(dataset_dir)
    for identity in identities:
        identity_path = os.path.join(dataset_dir, identity)
        if not os.path.isdir(identity_path):
            continue
            
        for img_name in os.listdir(identity_path):
            img_path = os.path.join(identity_path, img_name)
            if not img_path.endswith('.jpg'):
                continue
                
            total_images += 1
            img = cv2.imread(img_path)
            if img is None:
                continue
                
            faces, status = detector.detect(img)
            if status != "Success" or len(faces) != 1:
                # quality gate: exactly 1 face allowed
                continue
                
            face = faces[0]
            x, y, w, h = face[:4]
            if w < 30 or h < 30:
                continue
                
            embedding = embedder.align_and_extract(img, face)
            
            meta = {
                "identity": identity,
                "template_id": f"{identity}_{img_name}",
                "source_image": img_path
            }
            biometric_index.add(embedding, meta)
            enrolled_templates += 1
            
            if total_images % 500 == 0:
                print(f"Processed {total_images} images, enrolled {enrolled_templates} templates.")
                
    biometric_index.save()
    print(f"Enrollment complete. Total images: {total_images}, Enrolled templates: {enrolled_templates}")

if __name__ == "__main__":
    dataset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "lfw-deepfunneled")
    index_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "index")
    enroll_dataset(dataset_dir, index_dir)
