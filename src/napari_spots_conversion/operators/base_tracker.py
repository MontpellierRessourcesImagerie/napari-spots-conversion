import xarray as xr
from abc import ABC, abstractmethod
import pandas as pd
from skimage.measure import regionprops
import numpy as np

class BaseTracker(ABC):
    
    def __init__(self):
        self.detections = None
        self.searching_distance = 10.0
        self.memory = 2
        self.remove_incomplete = False

    def getSearchingDistance(self) -> float:
        return self.searching_distance
    
    def setSearchingDistance(self, distance: float):
        if distance <= 0:
            raise ValueError("Searching distance must be positive.")
        self.searching_distance = distance

    def getRemoveIncompleteTracks(self) -> bool:
        return self.remove_incomplete
    
    def setRemoveIncompleteTracks(self, remove: bool):
        self.remove_incomplete = remove

    def getMemory(self) -> int:
        return self.memory
    
    def setMemory(self, memory: int):
        if memory < 0:
            raise ValueError("Memory must be a non-negative integer.")
        self.memory = memory

    def checkAxes(self, axes: list):
        allowed = {'T', 'Z', 'Y', 'X', 'C'}
        in_axes = set(axes)
        if not in_axes.issubset(allowed):
            raise ValueError(f"Axes must be a subset of {allowed}. Found: {in_axes}")

    def initFromLabels(self, labels: xr.DataArray, calibration: dict | None):
        axes = list(str(l) for l in labels.dims)
        self.checkAxes(axes)

        if 'C' in axes:
            raise ValueError("Labels should not have a 'C' dimension.")
        
        if ('T' not in axes) or (labels.sizes['T'] <= 1):
            raise ValueError("Labels must have a 'T' dimension for tracking.")
        
        calibration = calibration if calibration is not None else {}
        complementary = {a: 1.0 for a in axes if a not in calibration}
        calibration = {**complementary, **calibration}
        rows = []

        if 'Z' in labels.dims and labels.sizes['Z'] == 1:
            labels = labels.squeeze('Z')

        for t in range(labels.sizes['T']):
            frame = labels.isel({'T': t})
            lab   = frame.values
            axes = [str(i) for i in frame.dims]
            for rp in regionprops(lab):
                pos = {a: c * calibration[a] for c, a in zip(rp.centroid, axes)}
                row = {
                    "T"         : t,
                    "size"      : rp.area,
                    "orig_label": int(rp.label)
                }
                row.update(pos)
                rows.append(row)
        
        self.detections = pd.DataFrame(rows) 

    def initFromCoordinates(self, coordinates: np.ndarray, axes: list[str], sizes: np.ndarray | None = None):
        self.checkAxes(axes)

        if 'C' in axes:
            raise ValueError("Coordinates should not have a 'C' axis.")
        
        if 'T' not in axes or coordinates.shape[axes.index('T')] <= 1:
            raise ValueError("Coordinates must have a 'T' axis for tracking.")
        
        complementary = {a: 1.0 for a in axes if a not in ['T', 'Z', 'Y', 'X']}
        calibration = {**complementary, **{a: 1.0 for a in ['T', 'Z', 'Y', 'X']}}
        rows = []

        if sizes is not None and len(sizes) != len(coordinates):
            raise ValueError("Sizes array must have the same length as the number of coordinates.")

        for i in range(len(coordinates)): # one line per coordinate, including all dimensions.
            pos = {a: coordinates[i][axes.index(a)] * calibration[a] for a in axes}
            row = {
                "T"         : coordinates[i][axes.index('T')],
                "size"      : sizes[i] if sizes is not None else 1.0,
                "orig_label": i
            }
            row.update(pos)
            rows.append(row)
        
        self.detections = pd.DataFrame(rows)

    def initFromDetections(self, detections: pd.DataFrame):
        for a in ['T', 'Y', 'X']:
            if a not in detections.columns:
                raise ValueError(f"Detections DataFrame must contain '{a}' column.")
        self.detections = detections.copy()

    @abstractmethod
    def linkTracks(self):
        raise NotImplementedError("Subclasses must implement the link_tracks method.")
    
    def relabelWithTracks(self, labels: xr.DataArray) -> xr.DataArray:
        if (self.detections is None) or ('track_id' not in self.detections.columns):
            raise ValueError("Linked DataFrame must contain 'track_id' column.")

        out = []
        for t, g in self.detections.groupby("T"):
            lab = labels.isel(T=t).values

            orig = g["orig_label"].astype(int).values
            track = g["track_id"].astype(int).values

            lut = np.zeros(lab.max() + 1, dtype=np.uint16)
            lut[orig[orig != 0]] = track[orig != 0]  # skip orig_label 0

            out.append(lut[lab])

        return xr.DataArray(np.array(out), dims=labels.dims)
    
    def keepFullTracks(self): # labels present on the last frame
        if (self.detections is None) or ('track_id' not in self.detections.columns):
            raise ValueError("Linked DataFrame must contain 'track_id' column.")
        
        n_frames = len(self.detections["T"].unique())
        complete_labels = set()

        for label in self.detections["track_id"].unique():
            track = self.detections[self.detections["track_id"] == label]
            if track["T"].unique().size == n_frames:
                complete_labels.add(label)

        self.detections = self.detections[self.detections["track_id"].isin(complete_labels)].reset_index(drop=True)

    def run(self):
        if self.detections is None:
            raise ValueError("Detections have not been set.")
        
        self.linkTracks()
        if self.remove_incomplete:
            self.keepFullTracks()