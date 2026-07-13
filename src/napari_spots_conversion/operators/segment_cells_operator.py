from cellpose_napari import CellPoseInference, ImageUtils
import xarray as xr


class SegmentCellsOperator:
    
    def __init__(self):
        self.input_image = None
        self.object_diameter = self.default_object_diameter()
        self.kill_border = self.default_kill_border()
        self.output_labels = None

    @staticmethod
    def default_object_diameter():
        return 60

    @staticmethod
    def default_kill_border():
        return True

    def set_kill_border(self, kill_border):
        self.kill_border = kill_border

    def get_kill_border(self):
        return self.kill_border

    def set_input_image(self, image):
        if image is None or image.ndim != 3:
            raise ValueError("Input image must be a 2D+t array.")
        self.input_image = xr.DataArray(image, dims=self.get_axes())

    def get_input_image(self):
        return self.input_image
    
    def set_object_diameter(self, diameter):
        if diameter <= 1:
            raise ValueError("Object diameter must be greater than 1.")
        self.object_diameter = diameter

    def get_object_diameter(self):
        return self.object_diameter
    
    def get_output_labels(self):
        if self.output_labels is None:
            raise ValueError("Output labels are not available. Run the operator first.")
        return self.output_labels
    
    @staticmethod
    def get_axes():
        return ["T", "Y", "X"]
    
    def run(self):
        if self.input_image is None:
            raise ValueError("Input image is not set.")
        
        image = ImageUtils.ensureAxes(self.input_image)
        worker = CellPoseInference( # using default model
            ch_main=image,
            ch_secondary=None,
            diameter=self.object_diameter,
            anisotropy=1.0,
            min_size=100,
            cell_prob=0.0,
            flow_thr=0.4,
            flow_smooth=1,
            use_gpu=True,
            kill_border=self.kill_border,
            margin_width=3
        )

        yield from worker.run()

        if worker.output_buffer is None:
            raise RuntimeError("CellPose inference failed to produce output.")
        
        self.output_labels = ImageUtils.removeExtraAxes(
            worker.output_buffer, 
            self.get_axes()
        )


if __name__ == "__main__":
    import tifffile as tiff
    from pathlib import Path

    img_path = Path("/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c1.tif")
    img = tiff.imread(img_path)

    op = SegmentCellsOperator()
    op.set_input_image(img)

    for _ in op.run():
        pass

    tiff.imwrite(
        "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c1_labels.tif", 
        op.get_output_labels().values,
        imagej=True
    )