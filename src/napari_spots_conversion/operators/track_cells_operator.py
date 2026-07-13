import xarray as xr
from .trackpy_tracker import TrackpyTracker


class TrackCellsOperator:
    
    def __init__(self):
        self.input_image = None
        self.tracked_labels = None
        self.memory = self.default_memory()
        self.remove_incomplete = self.default_remove_incomplete()
        self.max_distance = self.default_max_distance()

    @staticmethod
    def default_memory():
        return 1
    
    @staticmethod
    def default_remove_incomplete():
        return True
    
    @staticmethod
    def default_max_distance():
        return 15
    
    def get_tracked_labels(self):
        if self.tracked_labels is None:
            raise ValueError("Tracked labels are not available. Run the operator first.")
        return self.tracked_labels
    
    def get_axes(self):
        return ["T", "Y", "X"]
    
    def set_input_image(self, image):
        if image is None or image.ndim != 3:
            raise ValueError("Input image must be a 2D+t array.")
        self.input_image = xr.DataArray(image, dims=self.get_axes())

    def get_input_image(self):
        return self.input_image
    
    def set_memory(self, memory):
        if memory < 0:
            raise ValueError("Memory must be non-negative.")
        self.memory = memory

    def get_memory(self):
        return self.memory
    
    def set_remove_incomplete(self, remove):
        self.remove_incomplete = remove

    def get_remove_incomplete(self):
        return self.remove_incomplete
    
    def set_max_distance(self, max_distance):
        if max_distance <= 0:
            raise ValueError("Max distance must be positive.")
        self.max_distance = max_distance

    def get_max_distance(self):
        return self.max_distance
    
    def run(self):
        if self.input_image is None:
            raise ValueError("Input image is not set.")
        
        tracker = TrackpyTracker()
        tracker.setMemory(self.memory)
        tracker.setSearchingDistance(self.max_distance)
        tracker.setRemoveIncompleteTracks(self.remove_incomplete)
        tracker.initFromLabels(self.input_image, calibration=None)

        tracker.run()
        self.tracked_labels = tracker.relabelWithTracks(self.input_image)


if __name__ == "__main__":
    import tifffile as tiff

    labels_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c1_labels.tif"
    labels = tiff.imread(labels_path)

    op = TrackCellsOperator()
    op.set_input_image(labels)
    # op.set_memory(2)
    # op.set_max_distance(10.0)
    op.run()

    tracked_labels = op.get_tracked_labels()
    tiff.imwrite(
        "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c1_tracked.tif", 
        tracked_labels.values,
        imagej=True
    )