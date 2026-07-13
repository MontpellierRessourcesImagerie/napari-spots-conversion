from .base_tracker import BaseTracker
import trackpy as tp


class TrackpyTracker(BaseTracker):
    
    def __init__(self):
        super().__init__()

    def linkTracks(self):
        if self.detections is None:
            raise ValueError("No detections to link. Please initialize the tracker with detections first.")
        
        predictor = tp.predict.NearestVelocityPredict()
        pos_columns = [a for a in ['Z', 'Y', 'X'] if a in self.detections.columns]
        
        linked = predictor.link_df(
            self.detections,
            search_range=self.searching_distance,
            memory=self.memory,
            pos_columns=pos_columns,
            t_column='T',
            adaptive_stop=0.01,
            adaptive_step=0.75
        )
        self.detections["track_id"] = linked["particle"].astype(int) + 1