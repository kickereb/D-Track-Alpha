from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import time
import cv2

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
    def initialise(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray, rvec, tvec) -> None:
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
    
    def initialise(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray, rvec, tvec) -> None:
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

class LennysCustomCoordinateTransformer(CoordinateTransformerInterface):
    def __init__(self):
        self.camera_matrix = None
        self.dist_coeffs = None
        self.rvec = None
        self.tvec = None
        self.view_calibration = None
        self.GRID_SIZE = (1000, 1000)  # Define grid size as class constant, adjust as needed
        
        # Default view calibration settings
        self.DEFAULT_VIEW_CALIBRATION = {
            0: {"start_pixel": (0, 1080), "end_pixel": (1920, 1080), 
                "start_true_coord": (0, 0), "end_true_coord": (320, 150)},
            1: {"start_pixel": (0, 1080), "end_pixel": (1920, 1080), 
                "start_true_coord": (60, 150), "end_true_coord": (360, 60)},
        }
    
    def initialise(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray, rvec, tvec) -> None:
        """Initialize the transformer with camera matrix and distortion coefficients."""
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        self.rvec = rvec
        self.tvec = tvec
    
    def transform(self, bbox: BoundingBox, frame_size: Tuple[int, int]) -> WorldCoordinates:
        """Transform a bounding box to world coordinates."""
        # Extract the bottom center point of the bounding box
        u = (bbox.x1 + bbox.x2) / 2
        v = bbox.y2
        
        # Assuming we have rotation and translation vectors for the camera
        # These should be properly initialized or passed to the method
        world_point = self.image_to_world(u, v, self.camera_matrix, self.dist_coeffs, 
                                        self.rvec, self.tvec, y=0)
        
        return WorldCoordinates(world_point[0], 0, world_point[1])  # y is 0 as we're on ground plane
    
    @staticmethod
    def image_to_world(u: float, v: float, mtx: np.ndarray, dist: np.ndarray, 
                      rvec: np.ndarray, tvec: np.ndarray, y: float = 0) -> np.ndarray:
        """Convert image coordinates to world coordinates."""
        # Extract rotation matrix and its inverse
        R, _ = cv2.Rodrigues(rvec)
        R_inv = R.T
        
        # Compute optimal camera matrix
        ww, hh = (1920, 1080)  # Using standard HD resolution
        optimalMtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (ww, hh), 0, (ww, hh))
        
        # Undistort the pixel coordinates
        uv_1 = np.array([[[u, v]]], dtype=np.float32)
        uv_undistorted = cv2.undistortPoints(uv_1, mtx, dist, None, optimalMtx)
        
        # Create a ray from the camera center through the undistorted point
        ray = np.array([uv_undistorted[0, 0, 0], uv_undistorted[0, 0, 1], 1.0])
        
        # Transform ray to world coordinates
        ray = np.linalg.inv(optimalMtx) @ ray
        ray = ray / np.linalg.norm(ray)
        
        # Calculate the scaling factor to reach the plane at y
        t = (y - tvec[1]) / (R_inv @ ray)[1]
        
        # Calculate the 3D point
        world_point = R_inv @ (t * ray - tvec)
        
        return world_point
    
    def calibrate_views(self, camera_matrices: List[np.ndarray], 
                       dist_coef: List[np.ndarray], 
                       rvec: List[np.ndarray], 
                       tvec: List[np.ndarray], 
                       debug: bool = False) -> Dict:
        """
        Calibrate multiple camera views using predefined calibration points.
        
        Args:
            camera_matrices: List of camera matrices for each view
            dist_coef: List of distortion coefficients for each view
            rvec: List of rotation vectors for each view
            tvec: List of translation vectors for each view
            debug: If True, print debug information
            
        Returns:
            Dictionary containing calibration parameters for each view
        """
        view_calibration = self.DEFAULT_VIEW_CALIBRATION.copy()
        
        for view in range(len(camera_matrices)):
            start_pixel = view_calibration[view]["start_pixel"]
            end_pixel = view_calibration[view]["end_pixel"]
            start_true_coord = np.array(view_calibration[view]["start_true_coord"])
            end_true_coord = np.array(view_calibration[view]["end_true_coord"])

            if debug:
                print(f"View {view} has start pixel at {start_pixel} and end pixel at {end_pixel}")
                print(f"View {view} has start true coord at {start_true_coord} and end true coord at {end_true_coord}")

            projected_start = self.image_to_world(
                start_pixel[0], start_pixel[1],
                camera_matrices[view], dist_coef[view],
                rvec[view], tvec[view], y=0
            )
            projected_end = self.image_to_world(
                end_pixel[0], end_pixel[1],
                camera_matrices[view], dist_coef[view],
                rvec[view], tvec[view], y=0
            )

            if debug:
                print(f"View {view} has projected start at {projected_start} and projected end at {projected_end}")

            # Calculate scaling factors
            scale_x = (end_true_coord[0] - start_true_coord[0]) / (projected_end[0] - projected_start[0])
            scale_z = (end_true_coord[1] - start_true_coord[1]) / (projected_end[1] - projected_start[1])

            # Calculate offsets
            offset_x = start_true_coord[0] - (projected_start[0] * scale_x)
            offset_z = start_true_coord[1] - (projected_start[1] * scale_z)

            view_calibration[view].update({
                "scale_x": scale_x,
                "scale_z": scale_z,
                "offset_x": offset_x,
                "offset_z": offset_z
            })

            if debug:
                print(f"View {view} calibration: scale_x={scale_x}, scale_z={scale_z}, "
                      f"offset_x={offset_x}, offset_z={offset_z}")
        
        self.view_calibration = view_calibration
        return view_calibration
    
    def project_positions_to_grid(self, annotations: List[Dict], 
                                rvec: List[np.ndarray], 
                                tvec: List[np.ndarray], 
                                camera_matrices: List[np.ndarray], 
                                dist_coef: List[np.ndarray]) -> Dict:
        """Project multiple person positions to a grid."""
        projected = {}
        
        # Initialize view calibration if not already done
        if self.view_calibration is None:
            self.view_calibration = self.calibrate_views(camera_matrices, dist_coef, rvec, tvec)
        
        for frame_num, frame in enumerate(annotations):
            for person in frame:
                personID = person['personID']
                if personID not in projected:
                    projected[personID] = {}
                
                valid_world_coords = []
                
                for view in person['views']:
                    viewNum, x1, y1, x2, y2 = view.values()
                    if x1 == -1:  # Skip invalid views
                        continue
                    
                    # Get the foot position of the person
                    uvCoord = np.array([(x1 + x2) / 2, y2, 1])
                    mtx = camera_matrices[viewNum]
                    dist = dist_coef[viewNum]
                    r = np.asarray(rvec[viewNum])
                    t = np.asarray(tvec[viewNum])
                    
                    # Convert to world coordinates
                    worldCoord = self.image_to_world(uvCoord[0], uvCoord[1], mtx, dist, r, t, y=0)
                    
                    # Apply calibration
                    calibrated_x = worldCoord[0] * self.view_calibration[viewNum]["scale_x"] + \
                                 self.view_calibration[viewNum]["offset_x"]
                    calibrated_z = worldCoord[1] * self.view_calibration[viewNum]["scale_z"] + \
                                 self.view_calibration[viewNum]["offset_z"]
                    
                    calibrated_worldCoord = np.array([calibrated_x, calibrated_z])
                    valid_world_coords.append(calibrated_worldCoord)
                
                if valid_world_coords:
                    # Average the world coordinates from all valid views
                    avg_world_coord = np.mean(valid_world_coords, axis=0)
                    projected[personID][frame_num] = avg_world_coord
                else:
                    projected[personID][frame_num] = None
        
        return projected

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