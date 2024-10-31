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

    def to_dict(self):
        """Convert BoundingBox to dictionary for serialization"""
        return {
            'x1': self.x1,
            'y1': self.y1,
            'x2': self.x2,
            'y2': self.y2
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create BoundingBox from dictionary"""
        return cls(
            x1=data['x1'],
            y1=data['y1'],
            x2=data['x2'],
            y2=data['y2']
        )

@dataclass
class WorldCoordinates:
    """Represents a point in 3D world space"""
    x: float
    y: float
    z: float
        
    def to_dict(self):
        """Convert WorldCoordinate to dictionary for serialization"""
        return {
            'x': self.x,
            'y': self.y,
            'z': self.z
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create WorldCoordinate from dictionary"""
        return cls(
            x=data['x'],
            y=data['y'],
            z=data['z']
        )

@dataclass
class PersonDetection:
    """Represents a single person detection"""
    bbox: BoundingBox
    confidence: float
    tracking_id: int
    world_position: Optional[WorldCoordinates] = None

    def to_dict(self):
        """Convert PersonDetection to dictionary for serialization"""
        data = {
            'bbox': self.bbox.to_dict(),
            'confidence': self.confidence,
            'tracking_id': self.tracking_id,
            'world_position': self.world_position.to_dict() if self.world_position else None,
        }
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create PersonDetection from dictionary"""
        world_pos_data = data.get('world_position')
        return cls(
            tracking_id=data['tracking_id'],
            confidence=data['confidence'],
            bbox=BoundingBox.from_dict(data['bbox']),
            world_position=WorldCoordinates.from_dict(world_pos_data) if world_pos_data else None,
        )

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
        config = self.camera.create_still_configuration(main={"size": (640, 640)})
        self.camera.configure(config)
        self.camera.start()
        time.sleep(2)  # Warm-up time
    
    def capture(self) -> np.ndarray:
        return self.camera.capture_array()
    
    def release(self) -> None:
        self.camera.stop()

from ultralytics import YOLO

class YOLOv11NCNNPersonDetector(PersonDetectorInterface):
    """YOLOv11 nano ncnn implementation of person detection"""
    
    def initialise(self) -> None:
        self.model = YOLO('./yolo11n_ncnn_model')
    
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
                tracking_id=tracking_id_start * 1000 + i,
                confidence=confidence * 100,  # Convert to percentage
                bbox=bbox,
                world_position=world_pos
            )
            results.append(detection)
        
        return results
    
    def release(self) -> None:
        """Cleanup all components"""
        self.image_capture.release()
        self.person_detector.release()