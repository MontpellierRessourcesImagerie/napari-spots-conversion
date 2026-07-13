from .trackpy_tracker import TrackpyTracker
import pandas as pd


class TrackSpotsOperator:
    
    def __init__(self):
        self.input_points = None
        self.tracked_points = None
        self.memory = self.default_memory()
        self.max_distance = self.default_max_distance()

    @staticmethod
    def default_memory():
        return 1
    
    @staticmethod
    def default_max_distance():
        return 2
    
    def set_input_points(self, points):
        if points is None or not isinstance(points, pd.DataFrame):
            raise ValueError("Input points must be a pandas DataFrame.")
        self.input_points = points

    def get_input_points(self):
        return self.input_points
    
    def get_tracked_points(self):
        if self.tracked_points is None:
            raise ValueError("Tracked points are not available. Run the operator first.")
        return self.tracked_points
    
    def set_memory(self, memory):
        if memory < 0:
            raise ValueError("Memory must be non-negative.")
        self.memory = memory

    def get_memory(self):
        return self.memory
    
    def set_max_distance(self, max_distance):
        if max_distance <= 0:
            raise ValueError("Max distance must be positive.")
        self.max_distance = max_distance

    def get_max_distance(self):
        return self.max_distance
    
    def run(self):
        if self.input_points is None:
            raise ValueError("Input points are not set.")
        
        tracker = TrackpyTracker()
        tracker.setMemory(self.memory)
        tracker.setSearchingDistance(self.max_distance)
        tracker.setRemoveIncompleteTracks(False)
        tracker.initFromDetections(self.input_points)

        tracker.run()
        self.tracked_points = tracker.detections


if __name__ == "__main__":
    df_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c2_detected_spots.csv"
    points_df = pd.read_csv(df_path)

    op = TrackSpotsOperator()
    op.set_input_points(points_df)

    op.run()
    tracked_points = op.get_tracked_points()
    tracked_points.to_csv(
        "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c2_tracked_spots.csv", 
        index=False
    )