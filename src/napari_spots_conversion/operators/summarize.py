import pandas as pd

class Summarizer:
    
    @staticmethod
    def make_summary(df, time_factor):
        rows = []
        for track_id, sub in df.groupby('track_id'):
            n_birth = (sub['phase'] == 0).sum()
            n_conversion = (sub['phase'] == 1).sum()
            n_converted = (sub['phase'] == 2).sum()

            row = {
                'track_id': track_id,
                'start_time': sub['T'].min() * time_factor,
                'birth_time': n_birth * time_factor,
                'conversion_time': n_conversion * time_factor,
                'converted_time': n_converted * time_factor,
                'total_time': (n_birth + n_conversion + n_converted) * time_factor,
            }
            row['cell_id'] = sub['cell_id'].iloc[0]
            rows.append(row)

        columns = ['track_id', 'cell_id'] if 'cell_id' in df.columns else ['track_id']
        columns += ['birth_time', 'conversion_time', 'converted_time', 'total_time']

        return pd.DataFrame(rows)[columns].sort_values(['cell_id', 'track_id'])