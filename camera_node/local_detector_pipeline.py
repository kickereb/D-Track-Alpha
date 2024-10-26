from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import time

@dataclass
class BoundingBox:
    """Represents a detection bounding box"""
    x1: float
    y1: float
    x2: float
    y2: float

@dataclass
class WorldCoordinates:
    """Represents a point in 3D world space"""
    x: float
    y: float
    z: float

@dataclass
class PersonDetection:
    """Represents a single person detection"""
    bbox: BoundingBox
    confidence: float
    tracking_id: int
    world_pos: Optional[WorldCoordinates] = None

class ImageCaptureInterface(ABC):
    """Abstract base class for image capture devices"""
    
    @abstractmethod
    def initialise(self) -> None:
        """Initialise the camera system"""
        pass
    
    @abstractmethod
    def capture(self) -> np.ndarray:
        """Capture a single frame
        
        Returns:
            np.ndarray: Captured image array
        """
        pass
    
    @abstractmethod
    def release(self) -> None:
        """Cleanup and release camera resources"""
        pass

class PersonDetectorInterface(ABC):
    """Abstract base class for person detection algorithms"""
    
    @abstractmethod
    def initialise(self) -> None:
        """initialise the detection model"""
        pass
    
    @abstractmethod
    def detect(self, image: np.ndarray) -> List[Tuple[BoundingBox, float]]:
        """Detect persons in image
        
        Args:
            image: Input image array
            
        Returns:
            List of tuples containing (bounding_box, confidence)
        """
        pass
    
    @abstractmethod
    def release(self) -> None:
        """Cleanup and release model resources"""
        pass

class CoordinateTransformerInterface(ABC):
    """Abstract base class for coordinate transformation systems"""
    
    @abstractmethod
    def initialise(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray) -> None:
        """initialise with camera calibration parameters"""
        pass
    
    @abstractmethod
    def transform(self, bbox: BoundingBox, frame_size: Tuple[int, int]) -> WorldCoordinates:
        """Transform image coordinates to world coordinates
        
        Args:
            bbox: Bounding box in image coordinates
            frame_size: Image dimensions (width, height)
            
        Returns:
            WorldCoordinates: 3D position in world space
        """
        pass

# Concrete implementations
from picamera2 import Picamera2

class PiCamera2Capture(ImageCaptureInterface):
    """PiCamera2 implementation of image capture"""
    
    def initialise(self) -> None:
        self.camera = Picamera2()
        config = self.camera.create_still_configuration(main={"size": (1280, 720)})
        self.camera.configure(config)
        self.camera.start()
        time.sleep(2)  # Warm-up time
    
    def capture(self) -> np.ndarray:
        return self.camera.capture_array()
    
    def release(self) -> None:
        self.camera.stop()

from ultralytics import YOLO

class YOLOv8PersonDetector(PersonDetectorInterface):
    """YOLOv8 implementation of person detection"""
    
    def initialise(self) -> None:
        self.model = YOLO('yolov8n.pt')
    
    def detect(self, image: np.ndarray) -> List[Tuple[BoundingBox, float]]:
        results = self.model(image, classes=[0])  # class 0 is person
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                bbox = BoundingBox(float(x1), float(y1), float(x2), float(y2))
                detections.append((bbox, confidence))
        
        return detections
    
    def release(self) -> None:
        # YOLO doesn't need explicit cleanup
        pass

import cv2

class OpenCVCoordinateTransformer(CoordinateTransformerInterface):
    """OpenCV-based coordinate transformation"""
    
    def initialise(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray) -> None:
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
    
    def transform(self, bbox: BoundingBox, frame_size: Tuple[int, int]) -> WorldCoordinates:
        # Get bottom center of bounding box as reference point
        image_point = np.array([
            [(bbox.x1 + bbox.x2) / 2, bbox.y2]
        ], dtype=np.float32)
        
        # Assume the person is standing on a flat ground plane
        # This is a simplified transformation - you'll need to adjust based on your setup
        world_point = cv2.undistortPoints(
            image_point,
            self.camera_matrix,
            self.dist_coeffs
        )
        
        # Convert to world coordinates (this is a simplified example)
        # You'll need to implement your specific transformation logic
        x = float(world_point[0][0][0])
        z = float(world_point[0][0][1])
        y = 0.0  # Assuming flat ground
        
        return WorldCoordinates(x, y, z)

class DetectionManager:
    """Manages the complete detection pipeline"""
    
    def __init__(
        self,
        image_capture: ImageCaptureInterface,
        person_detector: PersonDetectorInterface,
        coordinate_transformer: CoordinateTransformerInterface
    ):
        self.image_capture = image_capture
        self.person_detector = person_detector
        self.coordinate_transformer = coordinate_transformer
        
    def initialise(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray) -> None:
        """initialise all components"""
        self.image_capture.initialise()
        self.person_detector.initialise()
        self.coordinate_transformer.initialise(camera_matrix, dist_coeffs)
    
    def detect_people(self, tracking_id_start: int) -> List[PersonDetection]:
        """Run complete detection pipeline
        
        Args:
            tracking_id_start: Starting ID for this frame's detections
            
        Returns:
            List of person detections with world coordinates
        """
        # Capture image
        frame = self.image_capture.capture()
        
        # Detect people
        detections = self.person_detector.detect(frame)
        
        # Transform coordinates and create final detections
        results = []
        for i, (bbox, confidence) in enumerate(detections):
            world_pos = self.coordinate_transformer.transform(bbox, frame.shape[:2])
            
            detection = PersonDetection(
                bbox=bbox,
                confidence=confidence * 100,  # Convert to percentage
                tracking_id=tracking_id_start * 1000 + i,
                world_pos=world_pos
            )
            results.append(detection)
        
        return results
    
    def release(self) -> None:
        """Cleanup all components"""
        self.image_capture.release()
        self.person_detector.release()