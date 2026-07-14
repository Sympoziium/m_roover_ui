import cv2
import numpy as np


class cnn_utils:

    def __init__(self, cnn_model=None):
        self.cnn_model = cnn_model

    def extract_frame_from_state(self, state):
        """Retourne une image si l'objet d'etat expose un attribut compatible."""
        if state is None:
            return None

        for attr in ["frame", "camera_frame", "image", "latest_frame", "raw_frame"]:
            if hasattr(state, attr):
                frame = getattr(state, attr)
                if frame is not None:
                    return frame
        return None

    def preprocess_frame(self, frame, input_shape):
        """Convertit une image OpenCV en entree CNN TFLite."""
        height = int(input_shape[1])
        width = int(input_shape[2])

        frame = cv2.resize(frame, (width, height))

        if frame.ndim == 3 and frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        frame = frame.astype(np.float32) / 255.0
        frame = np.expand_dims(frame, axis=0)

        return frame
