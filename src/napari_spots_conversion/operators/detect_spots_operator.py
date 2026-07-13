import xarray as xr
from spotiflow.model import Spotiflow
import pandas as pd
from tqdm import tqdm

class DetectSpotsOperator:
    def __init__(self):
        self.input_image = None
        self.detected_spots = None
        self.min_distance = self.default_min_distance()
        self.model_verbose = self.default_model_verbose()

    @staticmethod
    def default_model_verbose():
        return False

    def get_detected_spots(self):
        if self.detected_spots is None:
            raise ValueError("Detected spots are not available. Run the operator first.")
        return self.detected_spots

    @staticmethod
    def default_min_distance():
        return 2
    
    def get_axes(self):
        return ["T", "Y", "X"]
    
    def set_min_distance(self, distance):
        if distance <= 0:
            raise ValueError("Minimum distance must be positive.")
        self.min_distance = distance

    def get_min_distance(self):
        return self.min_distance
    
    def set_input_image(self, image):
        if image is None or image.ndim != 3:
            raise ValueError("Input image must be a 2D+t array.")
        self.input_image = xr.DataArray(image, dims=self.get_axes())

    def run(self):
        if self.input_image is None:
            raise ValueError("Input image is not set.")
        
        model = Spotiflow.from_pretrained("fluo_live")
        spots = []

        for t in tqdm(range(self.input_image.sizes["T"]), desc="Detecting spots"):
            frame = self.input_image.isel(T=t)
            x_index = frame.get_axis_num("X")
            y_index = frame.get_axis_num("Y")
            pts, _ = model.predict(
                frame.values,
                min_distance=self.min_distance,
                verbose=self.model_verbose
            )
            for pt1 in pts:
                spots.append({
                    "T": t, 
                    "Y": pt1[y_index], 
                    "X": pt1[x_index]
                })
            yield t+1

        self.detected_spots = pd.DataFrame(spots)


if __name__ == "__main__":
    import tifffile as tiff

    img_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c2.tif"
    img = tiff.imread(img_path)

    op = DetectSpotsOperator()
    op.set_input_image(img)
    
    for _ in op.run():
        pass

    pts = op.get_detected_spots()
    pts.to_csv(
        "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c2_detected_spots.csv", 
        index=False
    )