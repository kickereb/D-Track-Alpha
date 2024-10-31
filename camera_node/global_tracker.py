from sklearn.cluster import DBSCAN
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple
import time
import sys
from datetime import datetime
from collections import defaultdict

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

        # Collect world positions and detections
        positions_and_detections = self._collect_positions(frame)
        if not positions_and_detections:
            log("No valid world positions found in frame")
            return
            
        world_positions, detection_mapping = zip(*positions_and_detections)
        positions_array = np.array(world_positions)
        
        # Run clustering
        clusters = self._cluster_positions(positions_array)
        # Log clustering results
        self._log_cluster_stats(positions_array, clusters)
        cluster_to_global_id = self._match_clusters_to_tracks(positions_array, clusters)
        # Log tracking matches
        self._log_tracking_matches(cluster_to_global_id, clusters, positions_array)
        
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
        """Log enhanced summary of current tracking state"""
        try:
            active_tracks = len(self.last_positions)
            inactive_count = sum(1 for _, last_frame in self.last_seen.items() 
                            if (self.current_frame - last_frame) > self.inactive_timeout)
            
            log(f"\nTracking Summary:")
            log(f"- Frame: {self.current_frame}")
            log(f"- Active tracks: {active_tracks}")
            log(f"- Inactive tracks: {inactive_count}")
            log(f"- Next available ID: {self.next_global_id}")
            
            if active_tracks > 0:
                log("\nActive Track Positions:")
                for track_id, pos in self.last_positions.items():
                    last_seen = self.last_seen.get(track_id, 0)
                    frames_since_update = self.current_frame - last_seen
                    log(f"  Track {track_id}:")
                    log(f"    Position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
                    log(f"    Frames since update: {frames_since_update}")
                    
        except Exception as e:
            log(f"Error logging tracking summary: {str(e)}")

    def _log_cluster_stats(self, positions_array: np.ndarray, clusters: np.ndarray):
        """Log detailed statistics about clusters"""
        try:
            unique_clusters = set(clusters)
            n_clusters = len(unique_clusters) - (1 if -1 in unique_clusters else 0)
            noise_points = np.sum(clusters == -1)
            
            log("\nClustering Results:")
            log(f"- Total points: {len(positions_array)}")
            log(f"- Number of clusters: {n_clusters}")
            log(f"- Noise points: {noise_points}")
            
            # Analyze each cluster
            if n_clusters > 0:
                log("\nCluster Details:")
                for cluster_id in unique_clusters:
                    if cluster_id == -1:
                        continue
                        
                    cluster_mask = clusters == cluster_id
                    cluster_points = positions_array[cluster_mask]
                    
                    # Calculate cluster statistics
                    center = np.mean(cluster_points, axis=0)
                    std_dev = np.std(cluster_points, axis=0)
                    max_dist = np.max([np.linalg.norm(p - center) for p in cluster_points])
                    
                    log(f"\nCluster {cluster_id}:")
                    log(f"  - Points: {len(cluster_points)}")
                    log(f"  - Center: ({center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f})")
                    log(f"  - Std Dev: ({std_dev[0]:.2f}, {std_dev[1]:.2f}, {std_dev[2]:.2f})")
                    log(f"  - Max distance from center: {max_dist:.2f}m")
            
            if noise_points > 0:
                noise_mask = clusters == -1
                noise_positions = positions_array[noise_mask]
                log(f"\nNoise Points ({noise_points}):")
                for pos in noise_positions:
                    log(f"  - Position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
                    
        except Exception as e:
            log(f"Error logging cluster stats: {str(e)}")

    def _log_tracking_matches(self, cluster_to_global_id: Dict[int, int], clusters: np.ndarray, 
                            positions_array: np.ndarray):
        """Log information about track matching"""
        try:
            log("\nTrack Matching Results:")
            
            # Group detections by global ID
            tracks_by_id = defaultdict(list)
            for i, cluster_id in enumerate(clusters):
                if cluster_id in cluster_to_global_id:
                    global_id = cluster_to_global_id[cluster_id]
                    tracks_by_id[global_id].append(positions_array[i])
            
            for global_id, positions in tracks_by_id.items():
                positions = np.array(positions)
                mean_pos = np.mean(positions, axis=0)
                
                # Get previous position if available
                prev_pos = self.last_positions.get(global_id)
                if prev_pos is not None:
                    distance = np.linalg.norm(mean_pos - prev_pos)
                    log(f"\nTrack {global_id}:")
                    log(f"  - Detections: {len(positions)}")
                    log(f"  - Current pos: ({mean_pos[0]:.2f}, {mean_pos[1]:.2f}, {mean_pos[2]:.2f})")
                    log(f"  - Previous pos: ({prev_pos[0]:.2f}, {prev_pos[1]:.2f}, {prev_pos[2]:.2f})")
                    log(f"  - Movement: {distance:.2f}m")
                else:
                    log(f"\nNew Track {global_id}:")
                    log(f"  - Detections: {len(positions)}")
                    log(f"  - Initial pos: ({mean_pos[0]:.2f}, {mean_pos[1]:.2f}, {mean_pos[2]:.2f})")
                    
        except Exception as e:
            log(f"Error logging tracking matches: {str(e)}")