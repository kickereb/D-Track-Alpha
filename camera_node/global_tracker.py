from sklearn.cluster import DBSCAN
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple
import time
import sys
from datetime import datetime
import requests

def log(message):
    timestamp = datetime.now().strftime('%H:%M:%S.%f')
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()

@dataclass
class GlobalTracker:
    """
    Maintains global tracking information across frames using DBSCAN clustering
    
    Attributes:
        next_global_id: Counter for generating unique global IDs
        last_positions: Dictionary mapping global IDs to their last known positions
        inactive_timeout: Number of frames after which to remove inactive tracks
        last_seen: Dictionary tracking when each global ID was last seen
        current_frame: Current frame number being processed
        eps: Maximum distance (meters) between points to be considered same track
    """
    next_global_id: int = 1
    last_positions: Dict[int, np.ndarray] = field(default_factory=dict)
    inactive_timeout: int = 10  # frames
    last_seen: Dict[int, int] = field(default_factory=dict)
    current_frame: int = 0
    eps: float = 0.5  # meters
    
    def process_frame(self, frame) -> None:
        """
        Process all detections in a frame to update global tracks
        
        Args:
            frame: FrameData object containing detections from all nodes
        """
        self.current_frame = frame.frame_number

        print(frame)
        
        # Collect world positions and detections
        positions_and_detections = self._collect_positions(frame)
        if not positions_and_detections:
            log("No valid world positions found in frame")
            return
            
        world_positions, detection_mapping = zip(*positions_and_detections)
        positions_array = np.array(world_positions)
        
        # Run clustering
        clusters = self._cluster_positions(positions_array)
        cluster_to_global_id = self._match_clusters_to_tracks(positions_array, clusters)
        
        # Update detections and tracker state
        self._update_tracks(positions_array, detection_mapping, clusters, cluster_to_global_id)
        
        # Cleanup and log summary
        self._cleanup_inactive_tracks()
        self._log_tracking_summary()
    
    def _collect_positions(self, frame):
        """Collect world positions and their corresponding detections"""
        positions_and_detections = []
        
        for node_id, detections in frame.detections.items():
            for detection in detections:
                if detection.world_position:
                    pos = np.array([
                        detection.world_position.x,
                        detection.world_position.y,
                        detection.world_position.z
                    ])
                    positions_and_detections.append((pos, (node_id, detection)))
        
        return positions_and_detections
    
    def _cluster_positions(self, positions: np.ndarray) -> np.ndarray:
        """Cluster positions using DBSCAN"""
        dbscan = DBSCAN(eps=self.eps, min_samples=1)
        return dbscan.fit_predict(positions)
    
    def _match_clusters_to_tracks(self, positions: np.ndarray, clusters: np.ndarray) -> Dict[int, int]:
        """Match clusters to existing tracks based on proximity"""
        unique_clusters = set(clusters)
        cluster_to_global_id = {}
        used_global_ids = set()
        
        for cluster_id in unique_clusters:
            if cluster_id == -1:
                continue
                
            cluster_mask = clusters == cluster_id
            cluster_mean = positions[cluster_mask].mean(axis=0)
            
            # Find closest existing track
            best_match = None
            best_distance = float('inf')
            
            for global_id, last_pos in self.last_positions.items():
                if global_id in used_global_ids:
                    continue
                
                distance = np.linalg.norm(cluster_mean - last_pos)
                if distance < self.eps and distance < best_distance:
                    best_distance = distance
                    best_match = global_id
            
            if best_match is not None:
                cluster_to_global_id[cluster_id] = best_match
                used_global_ids.add(best_match)
                log(f"Matched cluster {cluster_id} to existing track {best_match}")
            else:
                new_id = self.next_global_id
                self.next_global_id = self.next_global_id + 1
                cluster_to_global_id[cluster_id] = new_id
                log(f"Created new track {new_id} for cluster {cluster_id}")
        
        return cluster_to_global_id
    
    def _update_tracks(self, positions: np.ndarray, detection_mapping, 
                      clusters: np.ndarray, cluster_to_global_id: Dict[int, int]) -> None:
        """Update detections with global IDs and update tracker state"""
        tracks_updated = set()
        
        for i, (pos, (node_id, detection)) in enumerate(zip(positions, detection_mapping)):
            cluster_id = clusters[i]
            if cluster_id == -1:
                global_id = self.next_global_id
                self.next_global_id += 1
                log(f"Created new track {global_id} for noise point")
            else:
                global_id = cluster_to_global_id[cluster_id]
                tracks_updated.add(global_id)
            
            detection.id = f"global_{global_id}"
            self.last_positions[global_id] = pos
            self.last_seen[global_id] = self.current_frame
            
            self._send_to_backend({cluster_id+"",len(self.last_positions(global_id)),pos[0]+"",pos[2]+""})
            
            log(f"Node {node_id} detection: {detection} (Track {global_id})")
    
    def _cleanup_inactive_tracks(self) -> None:
        """Remove tracks that haven't been seen recently"""
        inactive_ids = [
            gid for gid, last_frame in self.last_seen.items()
            if (self.current_frame - last_frame) > self.inactive_timeout
        ]
        
        for gid in inactive_ids:
            self.last_positions.pop(gid, None)
            self.last_seen.pop(gid, None)
            
        if inactive_ids:
            log(f"Cleaned up inactive tracks: {inactive_ids}")
    
    def _log_tracking_summary(self) -> None:
        """Log summary of current tracking state"""
        log(f"\nTracking Summary:")
        log(f"- Active tracks: {len(self.last_positions)}")
        log(f"- Next available ID: {self.next_global_id}")
    
    def _send_to_backend(self, data) -> None:
        """Send world coordinates to app backend web api"""
        server_addr = "http://10.0.0.169:3000"
        requests.post(url=server_addr, data=data)
        