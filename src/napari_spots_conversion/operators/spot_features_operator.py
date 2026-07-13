import pandas as pd
import numpy as np
from scipy.spatial import KDTree
import xarray as xr
from scipy.ndimage import distance_transform_edt, minimum_filter
from skimage.morphology import skeletonize


class SpotsFeaturesOperator:

    def __init__(self):
        self.input_points = None
        self.features = None
        self.labels_maps = None
        self.intensities_maps = None
        self.channel_name = ""

    def get_axes(self):
        return ['T', 'Y', 'X']
    
    def set_intensities_maps(self, intensities_map):
        if intensities_map is None or intensities_map.ndim != 3:
            raise ValueError("Intensities map must be a 3D numpy array.")
        self.intensities_maps = xr.DataArray(intensities_map, dims=self.get_axes())

    def set_channel_name(self, name):
        if not isinstance(name, str):
            raise ValueError("Channel name must be a string.")
        self.channel_name = name

    def set_labels_maps(self, labels_map):
        if labels_map is None or labels_map.ndim != 3:
            raise ValueError("Labels map must be a 3D numpy array.")
        self.labels_maps = xr.DataArray(labels_map, dims=self.get_axes())
    
    def set_input_points(self, points):
        if points is None or not isinstance(points, pd.DataFrame):
            raise ValueError("Input points must be a pandas DataFrame.")
        self.input_points = points

    def get_input_points(self):
        return self.input_points
    
    def process_track_length(self, df):
        df['track_duration'] = df.groupby('track_id')['T'].transform(lambda x: x.max() - x.min() + 1)
        return df
    
    def process_jitter(self, df):        
        jitter_values = {}
        
        for track_id in df['track_id'].unique():
            track_df = df[df['track_id'] == track_id].sort_values('T').reset_index(drop=True)
            
            total_distance = 0
            for i in range(len(track_df) - 1):
                x1, y1 = track_df.loc[i, 'X'], track_df.loc[i, 'Y']
                x2, y2 = track_df.loc[i + 1, 'X'], track_df.loc[i + 1, 'Y']
                t1, t2 = track_df.loc[i, 'T'], track_df.loc[i + 1, 'T']
                
                distance = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                frame_diff = t2 - t1
                total_distance += distance * frame_diff
            
            jitter_values[track_id] = total_distance
        
        df['jittering'] = df['track_id'].map(jitter_values) / df['track_duration']
        return df
    
    def process_closest_neighbor_distance(self, df):
        closest_neighbor = {}
        
        for track_id in df['track_id'].unique():
            closest_neighbor[track_id] = float('inf')
        
        for t in df['T'].unique():
            t_df = df[df['T'] == t].reset_index(drop=True)
            
            if len(t_df) < 2:
                continue
            
            points = t_df[['X', 'Y']].values
            kdtree = KDTree(points)
            
            index_to_track = {i: track_id for i, track_id in enumerate(t_df['track_id'].values)}
            
            for idx in range(len(t_df)):
                distances, _ = kdtree.query(points[idx], k=2)
                if len(distances) >= 2:
                    neighbor_distance = distances[1]
                    track_id = index_to_track[idx]
                    if neighbor_distance < closest_neighbor[track_id]:
                        closest_neighbor[track_id] = neighbor_distance
        
        df['closest_neighbor_distance'] = df['track_id'].map(closest_neighbor)
        return df
    
    def get_features(self):
        if self.features is None:
            raise ValueError("Features are not available. Run the operator first.")
        return self.features
    
    def bind_to_cells(self, df):
        if self.labels_maps is None:
            raise ValueError("Labels maps are not set.")
        
        cell_ids = []
        for _, row in df.iterrows():
            t, y, x = int(round(row['T'])), int(round(row['Y'])), int(round(row['X']))
            if 0 <= t < self.labels_maps.shape[0] and 0 <= y < self.labels_maps.shape[1] and 0 <= x < self.labels_maps.shape[2]:
                cell_id = self.labels_maps[t, y, x].item()
            else:
                cell_id = 0
            cell_ids.append(cell_id)
        
        df['cell_id'] = cell_ids
        return df
    
    def distance_to_membrane(self, df):
        if self.labels_maps is None:
            raise ValueError("Labels maps are not set.")
        
        lbls_copy = self.labels_maps.copy()
        lbls_copy = lbls_copy.astype(float)
        
        for t in range(self.labels_maps.sizes['T']):
            frame = self.labels_maps.loc[t].values
            eroded = minimum_filter(frame, size=3)
            membrane = (frame - eroded) > 0
            core = (frame > 0) & ~membrane
            distance = distance_transform_edt(core)
            lbls_copy.loc[t] = distance

        distances = []
        for _, row in df.iterrows():
            t, y, x = int(round(row['T'])), int(round(row['Y'])), int(round(row['X']))
            if 0 <= t < lbls_copy.shape[0] and 0 <= y < lbls_copy.shape[1] and 0 <= x < lbls_copy.shape[2]:
                distance = lbls_copy[t, y, x].item()
            else:
                distance = np.nan
            distances.append(distance)
        
        df['distance_to_membrane'] = distances
        df['distance_to_membrane'] = df.groupby('track_id')['distance_to_membrane'].transform('max')

        return df
    
    def record_intensity_features(self, df):
        if self.intensities_maps is None:
            raise ValueError("Intensities maps are not set.")
        if self.channel_name is None:
            raise ValueError("Channel name is not set.")
        
        intensities = []
        for _, row in df.iterrows():
            t, y, x = int(round(row['T'])), int(round(row['Y'])), int(round(row['X']))
            if 0 <= t < self.intensities_maps.shape[0] and 0 <= y < self.intensities_maps.shape[1] and 0 <= x < self.intensities_maps.shape[2]:
                intensity = self.intensities_maps[t, y, x].item()
            else:
                intensity = np.nan
            intensities.append(intensity)
        
        df[f'{self.channel_name}_intensity'] = intensities
        return df
    
    @staticmethod
    def n_steps():
        return 8
    
    def run(self):
        if self.input_points is None:
            raise ValueError("Input points are not set.")
        if self.labels_maps is None:
            raise ValueError("Labels maps are not set.")
        
        yield 0
        df = self.input_points.copy()
        yield 1
        df = self.distance_to_membrane(df)
        yield 2
        df = self.process_track_length(df)
        yield 3
        df = self.process_jitter(df)
        yield 4
        df = self.process_closest_neighbor_distance(df)
        yield 5
        df = self.bind_to_cells(df)
        yield 6
        df = self.record_intensity_features(df)
        yield 7
        
        self.features = df
    

if __name__ == "__main__":
    import tifffile as tiff

    df_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c2_tracked_spots.csv"
    df = pd.read_csv(df_path)

    lbls_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c1_tracked.tif"
    lbls = tiff.imread(lbls_path)

    op = SpotsFeaturesOperator()
    op.set_input_points(df)
    op.set_labels_maps(lbls)

    op.run()
    features_df = op.get_features()

    features_df.to_csv(
        "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c2_tracked_spots_features.csv", 
        index=False
    )