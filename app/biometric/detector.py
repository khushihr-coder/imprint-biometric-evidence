import cv2
import numpy as np
import os

class FaceDetector:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "yunet", "face_detection_yunet_2023mar.onnx")
        
        self.detector = cv2.FaceDetectorYN.create(
            model_path,
            "",
            (320, 320),
            0.9,
            0.3,
            5000
        )
    
    def detect(self, img):
        # img should be BGR numpy array
        if img is None:
            return None, "Invalid image"

        height, width, _ = img.shape
        self.detector.setInputSize((width, height))
        
        _, faces = self.detector.detect(img)
        
        if faces is None:
            return [], "No face detected"
        
        return faces, "Success"

    def align(self, img, face):
        # face is the output from detector
        # align crop using sface or just crop
        pass
