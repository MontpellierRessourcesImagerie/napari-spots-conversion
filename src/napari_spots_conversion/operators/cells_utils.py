import numpy as np


class CellsUtils:
    @staticmethod
    def merge_cells(cells_array, shapes_data):
        cells_array = cells_array.copy()
        for shape_group in shapes_data:
            coordinates = np.round(shape_group).astype(np.uint16)
            values = cells_array[tuple(coordinates.T)]
            unique_values = np.unique(values)
            unique_values = unique_values[unique_values != 0]
            if len(unique_values) > 0:
                merge_value = unique_values[0]
                for value in unique_values[1:]:
                    cells_array[cells_array == value] = merge_value
        return cells_array

    @staticmethod
    def remove_cells(input_img, points_data):
        cells_array = input_img.copy()
        coordinates = np.round(points_data).astype(np.uint16)
        values = cells_array[tuple(coordinates.T)]
        unique_values = np.unique(values)
        for value in unique_values:
            if value != 0:
                cells_array[cells_array == value] = 0
        return cells_array


def remove_cells():
    import tifffile as tiff

    cells_path = "/home/clement/Desktop/dump/tracked_cells_c1.tif"
    cells_img = tiff.imread(cells_path)

    points = np.array([
        [  28.        ,  867.37110469,  407.13409617],
        [  28.        ,  895.53913617,  418.08833063],
        [  28.        ,  972.21877742,  758.45204433],
        [  28.        , 1410.54720754,  696.65163813],
        [  28.        , 1435.4676219 , 1174.53723108],
        [  28.        , 1070.45684692, 1192.1281118 ],
        [  28.        ,  529.53726472,  915.07174043]
    ])

    cells_removed = CellsUtils.remove_cells(cells_img, points)
    out_path = "/home/clement/Desktop/dump/tracked_cells_c1_removed.tif"
    
    tiff.imwrite(
        out_path, 
        cells_removed.astype(np.uint16)
    )

def merge_cells():
    import tifffile as tiff

    cells_path = "/home/clement/Desktop/dump/tracked_cells_c1.tif"
    cells_img = tiff.imread(cells_path)

    shapes = [
        np.array([[ 59.     , 962.5483 , 712.98413],
            [ 59.     , 976.43835, 700.11035]], dtype=np.float32),
        np.array([[  59.    , 1026.9164,  780.4013],
                [  59.    , 1024.8839,  765.1562]], dtype=np.float32),
        np.array([[  59.     , 1342.6381 ,  490.08945],
                [  59.     , 1396.1831 ,  454.5644 ],
                [  59.     , 1405.9655 ,  513.258  ],
                [  59.     , 1458.4807 ,  529.7334 ]], dtype=np.float32),
        np.array([[  59.     , 1347.2719 ,  550.84247],
                [  59.     , 1354.4797 ,  571.4367 ],
                [  59.     , 1366.3215 ,  571.4367 ]], dtype=np.float32),
        np.array([[  59.     , 1365.8066 ,  664.1108 ],
                [  59.     , 1388.4603 ,  618.80347]], dtype=np.float32)
    ]

    merged_cells = CellsUtils.merge_cells(cells_img, shapes)
    out_path = "/home/clement/Desktop/dump/tracked_cells_c1_merged.tif"
    tiff.imwrite(
        out_path, 
        merged_cells.astype(np.uint16)
    )


if __name__ == "__main__":
    merge_cells()