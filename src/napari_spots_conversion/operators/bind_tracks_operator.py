import pandas as pd
import numpy as np
from scipy.spatial import KDTree


class BindTracksOperator:

    def __init__(self):
        self.birth_spots = None
        self.conversion_spots = None
        self.bound_tracks = None
        self.binding_distance = self.default_bind_distance()
        self.remove_incomplete_cycles = self.default_remove_incomplete_cycles()

    @staticmethod
    def default_remove_incomplete_cycles():
        return True
    
    @staticmethod
    def default_bind_distance():
        return 1.5
    
    def set_remove_incomplete_cycles(self, remove):
        self.remove_incomplete_cycles = remove

    def get_remove_incomplete_cycles(self):
        return self.remove_incomplete_cycles
    
    def set_binding_distance(self, distance):
        self.binding_distance = distance

    def get_binding_distance(self):
        return self.binding_distance

    def set_birth_spots(self, birth_spots):
        self.birth_spots = birth_spots

    def get_birth_spots(self):
        return self.birth_spots

    def set_conversion_spots(self, conversion_spots):
        self.conversion_spots = conversion_spots

    def get_conversion_spots(self):
        return self.conversion_spots
    
    def get_bound_tracks(self):
        if self.bound_tracks is None:
            raise ValueError("Bound tracks have not been computed yet. Please run the operator first.")
        return self.bound_tracks

    def bind_tracks(self, birth_tracks, conversion_tracks, binding_dist):
        birth_tracks = birth_tracks.copy()
        conversion_tracks = conversion_tracks.copy()
        birth_tracks["T"] = birth_tracks["T"].astype(int)
        birth_tracks["track_id"] = birth_tracks["track_id"].astype(int)
        conversion_tracks["T"] = conversion_tracks["T"].astype(int)
        conversion_tracks["track_id"] = conversion_tracks["track_id"].astype(int)
        
        max_track_id = birth_tracks["track_id"].max() + 1
        # access with birth track_id, gives candidate (converted) track_id and overlap duration.
        candidates_counter = np.zeros((max_track_id, 2), dtype=int)
        max_track_id = conversion_tracks["track_id"].max() + 1
        taken_candidates = np.zeros(max_track_id, dtype=bool)

        for t in range(birth_tracks["T"].min(), birth_tracks["T"].max() + 1):
            birth_t = birth_tracks[birth_tracks["T"] == t]
            conversion_t = conversion_tracks[conversion_tracks["T"] == t]

            if birth_t.empty or conversion_t.empty:
                continue

            tree = KDTree(conversion_t[["X", "Y"]].values)
            for _, row in birth_t.iterrows():
                dist, idx = tree.query([row["X"], row["Y"]])
                if dist > binding_dist:
                    continue

                candidate_id = int(conversion_t.iloc[idx]["track_id"])
                if taken_candidates[candidate_id]:
                    continue  # This candidate has already been taken by another birth track at this timepoint
                
                taken_candidates[candidate_id] = True
                current_id = int(row["track_id"])
                current_candidate = candidates_counter[current_id, 0]
                
                if current_candidate != 0 and current_candidate != candidate_id:
                    candidates_counter[current_id, 0] = -1  # Mark as ambiguous
                else:
                    candidates_counter[current_id, 0] = candidate_id
                    candidates_counter[current_id, 1] += 1
        
        return candidates_counter
    
    def merge_tracks(self, candidates_counter, birth_tracks, conversion_tracks):
        birth_tracks = birth_tracks.copy()
        conversion_tracks = conversion_tracks.copy()
        birth_tracks["T"] = birth_tracks["T"].astype(int)
        birth_tracks["track_id"] = birth_tracks["track_id"].astype(int)
        conversion_tracks["T"] = conversion_tracks["T"].astype(int)
        conversion_tracks["track_id"] = conversion_tracks["track_id"].astype(int)

        # Identify the "_intensity" columns in each dataframe
        birth_intensity_col = next(c for c in birth_tracks.columns if c.endswith("_intensity"))
        conversion_intensity_col = next(c for c in conversion_tracks.columns if c.endswith("_intensity"))

        # If both dataframes happen to use the same column name, disambiguate them
        if birth_intensity_col == conversion_intensity_col:
            out_birth_intensity_col = f"birth_{birth_intensity_col}"
            out_conversion_intensity_col = f"conversion_{conversion_intensity_col}"
        else:
            out_birth_intensity_col = birth_intensity_col
            out_conversion_intensity_col = conversion_intensity_col

        features_rows = []
        coordinates = []

        for birth_id in birth_tracks["track_id"].unique():
            converted_id = candidates_counter[birth_id, 0]
            if converted_id <= 0:
                continue  # No conversion or ambiguous

            birth_data = birth_tracks[birth_tracks["track_id"] == birth_id][
                ["T", "X", "Y", birth_intensity_col, "cell_id"]
            ].values
            conversion_data = conversion_tracks[conversion_tracks["track_id"] == converted_id][
                ["T", "X", "Y", conversion_intensity_col, "cell_id"]
            ].values

            birth_times = set([t for t, _, _, _, _ in birth_data])
            conversion_times = set([t for t, _, _, _, _ in conversion_data])
            overlap_times = birth_times & conversion_times

            # Dictionaries for quick lookup: T -> (x, y, intensity, cell_id)
            birth_dict = {int(t): (x, y, i, cid) for t, x, y, i, cid in birth_data}
            conversion_dict = {int(t): (x, y, i, cid) for t, x, y, i, cid in conversion_data}

            all_times = sorted(birth_times | conversion_times)
            for t in all_times:
                t = int(t)
                if t in overlap_times:
                    # Overlap phase: use mean coordinates, keep both intensities separate
                    bx, by, bi, bcid = birth_dict[t]
                    cx, cy, ci, ccid = conversion_dict[t]
                    mean_x = (bx + cx) / 2
                    mean_y = (by + cy) / 2
                    coordinates.append([t, mean_y, mean_x])
                    features_rows.append({
                        "track_id": int(birth_id),
                        "phase": 1,
                        out_birth_intensity_col: bi,
                        out_conversion_intensity_col: ci,
                        "cell_id": bcid
                    })
                elif t in birth_times:
                    # Birth phase only
                    x, y, bi, bcid = birth_dict[t]
                    coordinates.append([t, y, x])
                    features_rows.append({
                        "track_id": int(birth_id),
                        "phase": 0,
                        out_birth_intensity_col: bi,
                        out_conversion_intensity_col: np.nan,
                        "cell_id": bcid
                    })
                else:
                    # Conversion phase only
                    x, y, ci, ccid = conversion_dict[t]
                    coordinates.append([t, y, x])
                    features_rows.append({
                        "track_id": int(birth_id),
                        "phase": 2,
                        out_birth_intensity_col: np.nan,
                        out_conversion_intensity_col: ci,
                        "cell_id": ccid
                    })

        coordinates_df = pd.DataFrame(coordinates, columns=["T", "Y", "X"])
        coordinates_df = coordinates_df[["T", "X", "Y"]]
        features_df = pd.DataFrame(features_rows)
        result_df = pd.concat([coordinates_df, features_df], axis=1)

        return result_df
    
    def filter_incomplete_cycles(self):
        if self.bound_tracks is None:
            return
        
        grouped = self.bound_tracks.groupby("track_id")["phase"].apply(set)
        complete_track_ids = grouped[grouped == {0, 1, 2}].index
        
        self.bound_tracks = self.bound_tracks[self.bound_tracks["track_id"].isin(complete_track_ids)]
        self.bound_tracks = self.bound_tracks.sort_values("T").reset_index(drop=True)

    def run(self):
        if self.birth_spots is None or self.conversion_spots is None:
            raise ValueError("Birth spots and conversion spots must be set before running the operator.")
        
        counter = self.bind_tracks(
            self.birth_spots, 
            self.conversion_spots, 
            self.binding_distance
        )

        self.bound_tracks = self.merge_tracks(
            counter, 
            self.birth_spots, 
            self.conversion_spots
        )

        if self.remove_incomplete_cycles:
            self.filter_incomplete_cycles()



if __name__ == "__main__":
    c1_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c1_tracked_spots_features.csv"
    c2_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c2_tracked_spots_features.csv"
    c1_points = pd.read_csv(c1_path)
    c2_points = pd.read_csv(c2_path)

    op = BindTracksOperator()
    op.set_birth_spots(c1_points)
    op.set_conversion_spots(c2_points)
    op.set_binding_distance(5.0)  # Example value, adjust as needed
    op.run()

    bound_tracks = op.get_bound_tracks()
    bound_tracks.to_csv(
        "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/bound_tracks.csv", 
        index=False
    )