# napari-spots-conversion

- This plugin allows to quantify the conversion of spots from a channel to another.
- The performed steps are as following:
    1. Segmentation and tracking of cells.
    2. Detection and tracking of spots on both channels.
    3. Filtering of spots according to some criterions:
        - Distance to membrane
        - Distance to closest neighbor
        - Jittering
        - Track duration
    4. Binding tracks: find which spot of the first channel goes with a spot of the second.
- The result consists in a CSV containing a line per spot track and the time duration spent on each step (birth, conversion, converted).
- A detailed version is available where the intensities of spots are exported as well.