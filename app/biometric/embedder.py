import cv2
import numpy as np
import os

class FaceEmbedder:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "sface", "face_recognition_sface_2021dec.onnx")
        
        self.recognizer = cv2.FaceRecognizerSF.create(model_path, "")
    
    def align_and_extract(self, img, face):
        aligned_face = self.recognizer.alignCrop(img, face)
        embedding = self.recognizer.feature(aligned_face)
        # SFace returns a 1x128 feature vector, we can return it as 1D array
        return embedding[0]
