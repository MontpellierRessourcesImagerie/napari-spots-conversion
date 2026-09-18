# napari-spots-conversion

- This plugin quantifies the conversion of spots from one channel to another.
- The steps performed are as follows:
    1. Segmentation and tracking of cells.
    2. Detection and tracking of spots on both channels.
    3. Filtering of spots according to several criteria:
        - Distance to membrane
        - Distance to closest neighbor
        - Jittering
        - Track duration
    4. Binding tracks: find which spot in the first channel corresponds to a spot in the second.
- The result consists of a CSV file containing one line per spot track and the time spent in each state (birth, conversion, converted).
- A detailed version is available, in which spot intensities are also exported.

## 0. Get your data ready

- The plugin expects the images to be registered (background subtraction is not required).
- This means you need to use the macro from the "macros" folder to perform the registration beforehand.

## 1. Setup

- Open Napari. From the "Plugins" menu, open the "Scale Tool" and "Split channels" from "Calibration Tool", as well as "Spots conversion".
- If your channels are not already split, also open "Split channels" from "Calibration Tool".
- Start by providing the physical pixel size of your images in the "Scale Tool" widget, as well as the axes order. The very first line of the widget shows the size of each axis, which can help you figure out the correct order.
- Apply the calibration to all your channels.
- If your channels were not already split, now use the "Split channels" widget to do so.
- If your channels were already split, you must assign them a colormap. Pick whichever you like, but none of the layers should use the **gray** colormap, since gray is reserved for previewing discarded spots during filtering.

## 2. Cell segmentation & tracking (1st tab)

#### A. Cell segmentation

- In "Segmentation channel", provide the layer best suited for detecting your cells.
- In "Objects diameter", provide a rough estimate of the median diameter of your objects (in number of pixels).
- The "Kill borders?" option determines whether cells cut by the image border are removed.
- You can now launch the segmentation. Wait for the spinning wheel in the lower right corner of Napari to disappear.

#### B. Cell tracking

- Once your cells are segmented, they don't necessarily keep their identity over time, so tracking is needed to address that.
- "Memory" (in number of frames) is the maximum duration a cell can disappear before it is considered lost and counted as a new object if something reappears at the same location.
- "Displacement" (in µm) is the maximum distance an object can travel between two consecutive frames before it is considered lost or a new object. It should be approximately the diameter of a cell.
- You can now launch the tracking.

## 3. Curation (2nd tab)

- Start by clicking on the layer containing the tracked cells.
- If, by inspecting the segmentation, you determine that some cells should be removed, create a new "Points layer" and place a point on each cell to remove. The time point at which you do this doesn't matter — the cell will be removed at all time points where it is present.
- To merge cells, create a new "Shapes layer" and draw lines between the cells that should be merged.

## 4. Endocytic spots (3rd tab)

For each spots layer you have:
- Select it from the dropdown menu.
- The memory and displacement parameters work the same way here as for cell tracking.
- Click "Launch detection" to detect the spots.
- You can then proceed directly to "Launch spots tracking".

## 5. Filtering (4th tab)

For each spots layer you have:
- Process the features (see below) for this layer.
- Adjust the filtering parameters.
- Apply the filtering.

**Features:**
- "Jittering" of a spot is the total distance it travels divided by the duration it is present. A low jittering value means the spot stays still, while a high value means the spot moves erratically. (deactivated = high value)
- "Min. track length" is the minimum number of frames a spot must be present in to be considered a genuine spot. If a spot only appears for 3 time points, it is more likely noise than an actual spot. (deactivated = 0)
- "Min. proximity" is the shortest tolerated distance between two spots before both are discarded. When spots get too close to each other, tracking can become unreliable. The larger this distance, the farther apart the spots must be. (deactivated = 0)
- "Distance to membrane" is the maximum distance a spot can be from a membrane (inside a cell) before it is discarded. The larger this value, the farther a spot can be from the membrane. (deactivated = high value)

## 6. Conversion

#### A. Binding

- This step is optional (only needed if you have two spots channels).
- Indicate which spots layer corresponds to the birth channel and which corresponds to the conversion channel.
- "Binding distance" is the maximum distance allowed between two spots from different channels, at the same time point, for them to be considered bound together.
- Click "Bind tracks".
- The colormap shows the state of each spot at each time point:
    - Green: Birth state
    - Yellow: Undergoing conversion
    - Red: Converted

#### B. Export CSV

- "Export counts" is only available if you have two spots channels bound together.
- The resulting CSV contains:
    - `track_id`: The ID of the spot.
    - `cell_id`: The ID of the cell it belongs to.
    - `birth_time`: Time spent in the "birth" state.
    - `conversion_time`: Time spent visible in both channels.
    - `converted_time`: Time spent in the "converted" state.
    - `total_time`: The total lifespan of the spot.
    - These counts are mutually exclusive: to get the total duration in the first channel, sum `birth_time` and `conversion_time`. To get the total duration in the second channel, sum `converted_time` and `conversion_time`.
- "Export details" is available whether you have one or two spots channels, and whether or not they are bound.
- The resulting CSV contains:
    - `T`: The current time point for this line.
    - `X`: The spot's position on the X axis.
    - `Y`: The spot's position on the Y axis.
    - `track_id`: The ID of the spot.
    - `phase`: The current phase of this spot (0 = birth, 1 = undergoing conversion, 2 = converted).
    - `c1_intensity`: Peak intensity in channel 1.
    - `c2_intensity`: Peak intensity in channel 2.
    - `cell_id`: The ID of the cell this spot belongs to.