import os
import urllib.request

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")

YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

def download_file(url, filepath):
    if not os.path.exists(filepath):
        print(f"Downloading {os.path.basename(filepath)}...")
        urllib.request.urlretrieve(url, filepath)
        print("Downloaded.")
    else:
        print(f"{os.path.basename(filepath)} already exists.")

if __name__ == "__main__":
    os.makedirs(os.path.join(MODELS_DIR, "yunet"), exist_ok=True)
    os.makedirs(os.path.join(MODELS_DIR, "sface"), exist_ok=True)
    
    download_file(YUNET_URL, os.path.join(MODELS_DIR, "yunet", "face_detection_yunet_2023mar.onnx"))
    download_file(SFACE_URL, os.path.join(MODELS_DIR, "sface", "face_recognition_sface_2021dec.onnx"))
    print("Models ready.")
