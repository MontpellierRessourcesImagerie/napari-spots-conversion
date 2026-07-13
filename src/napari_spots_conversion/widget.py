from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
    QComboBox,
    QLabel,
    QCheckBox,
    QTabWidget,
    QFileDialog
)
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont
import napari

from napari.layers.labels.labels import Labels
from napari.layers.points.points import Points
from napari.layers.shapes.shapes import Shapes
from napari.layers.image.image import Image
from napari.layers.tracks.tracks import Tracks

from napari.qt.threading import create_worker
from napari.utils.notifications import show_info, show_warning

from .operators import (
    SegmentCellsOperator,
    TrackCellsOperator,
    DetectSpotsOperator,
    TrackSpotsOperator,
    SpotsFeaturesOperator,
    BindTracksOperator,
    CellsUtils,
    Summarizer
)

import pandas as pd


class DataUtils:

    @staticmethod
    def spots_numpy_to_df(spots, axes=["T", "Y", "X"]):
        if spots is None:
            raise ValueError("Input spots array is None.")
        if spots.ndim != 2 or spots.shape[1] != len(axes):
            raise ValueError(f"Input spots array must be of shape (N, {len(axes)}).")
        return pd.DataFrame(spots, columns=axes)
    
    @staticmethod
    def spots_df_to_numpy(spots_df, axes=["T", "Y", "X"]):
        if spots_df is None:
            raise ValueError("Input spots DataFrame is None.")
        if not all(axis in spots_df.columns for axis in axes):
            raise ValueError(f"Input spots DataFrame must contain columns: {axes}.")
        return spots_df[axes].values


class SpotsConversionWidget(QWidget):

    cells_prefix = "cells_"
    tracked_cells_prefix = "tracked_cells_"
    spots_prefix = "spots_"
    tracked_spots_prefix = "tracked_spots_"
    bound_tracks_name = "bound_tracks"
    bound_spots_name = "bound_spots"

    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self.viewer = viewer
        self.custom_font = QFont()
        self.custom_font.setFamily("Arial Unicode MS, Segoe UI Emoji, Apple Color Emoji, Noto Color Emoji")
        self.image_comboboxes = []
        self.label_comboboxes = []
        self.shape_comboboxes = []
        self.points_comboboxes = []
        self.track_comboboxes = []
        self.init_ui()
        self.current_operator = None
        self.init_callbacks()

    # -------- UI: ----------------------------------

    def init_ui(self):
        layout = QVBoxLayout()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.yeast_cells_panel(), "Yeast cells")
        self.tabs.addTab(self.curation_panel(), "Curation")
        self.tabs.addTab(self.endocytic_patches_panel(), "Endocytic patches")
        self.tabs.addTab(self.filtering_panel(), "Filtering")
        self.tabs.addTab(self.conversion_panel(), "Conversion")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def init_callbacks(self):
        self.viewer.layers.events.inserted.connect(self.update_comboboxes)
        self.viewer.layers.events.removed.connect(self.update_comboboxes)
        self.viewer.layers.events.renamed.connect(self.update_comboboxes)
        self.update_comboboxes()

    def _update_comboboxes(self, comboboxes, layer_type):
        for combobox in comboboxes:
            current_selection = combobox.currentText()
            combobox.clear()
            for layer in self.viewer.layers:
                if isinstance(layer, layer_type):
                    combobox.addItem(layer.name)
            index = combobox.findText(current_selection)
            if index >= 0:
                combobox.setCurrentIndex(index)

    def update_comboboxes(self):
        self._update_comboboxes(self.image_comboboxes, Image)
        self._update_comboboxes(self.label_comboboxes, Labels)
        self._update_comboboxes(self.points_comboboxes, Points)
        self._update_comboboxes(self.track_comboboxes, Tracks)
        self._update_comboboxes(self.shape_comboboxes, Shapes)

    def yeast_cells_panel(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Segmentation channel
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Segmentation channel"))
        self.segmentation_channel_combo = QComboBox()
        self.image_comboboxes.append(self.segmentation_channel_combo)
        h_layout.addWidget(self.segmentation_channel_combo)
        layout.addLayout(h_layout)

        # Objects diameter
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Objects diameter"))
        self.object_diameter_input = QSpinBox()
        self.object_diameter_input.setRange(15, 120)
        self.object_diameter_input.setValue(SegmentCellsOperator.default_object_diameter())
        h_layout.addWidget(self.object_diameter_input)
        layout.addLayout(h_layout)

        # Kill borders
        self.kill_borders_checkbox = QCheckBox("Kill borders?")
        self.kill_borders_checkbox.setChecked(SegmentCellsOperator.default_kill_border())
        layout.addWidget(self.kill_borders_checkbox)

        # Launch segmentation
        self.launch_segmentation_button = QPushButton("Launch segmentation")
        self.launch_segmentation_button.setFont(self.custom_font)
        self.launch_segmentation_button.clicked.connect(self.launch_segmentation)
        layout.addWidget(self.launch_segmentation_button)

        layout.addSpacing(10)

        # Memory (t)
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Memory (t)"))
        self.memory_input = QSpinBox()
        self.memory_input.setRange(0, 10)
        self.memory_input.setValue(TrackCellsOperator.default_memory())
        h_layout.addWidget(self.memory_input)
        layout.addLayout(h_layout)

        # Displacement (µm)
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Displacement (µm)"))
        self.displacement_input = QSpinBox()
        self.displacement_input.setRange(0, 100)
        self.displacement_input.setValue(TrackCellsOperator.default_max_distance())
        h_layout.addWidget(self.displacement_input)
        layout.addLayout(h_layout)

        # Remove incomplete tracks
        self.remove_incomplete_tracks_checkbox = QCheckBox("Remove incomplete tracks")
        self.remove_incomplete_tracks_checkbox.setChecked(TrackCellsOperator.default_remove_incomplete())
        layout.addWidget(self.remove_incomplete_tracks_checkbox)

        # Launch tracking
        self.launch_tracking_button = QPushButton("Launch tracking")
        self.launch_tracking_button.setFont(self.custom_font)
        self.launch_tracking_button.clicked.connect(self.launch_cells_tracking)
        layout.addWidget(self.launch_tracking_button)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def curation_panel(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Target layer
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Target layer"))
        self.target_layer_combo = QComboBox()
        self.label_comboboxes.append(self.target_layer_combo)
        h_layout.addWidget(self.target_layer_combo)
        layout.addLayout(h_layout)

        # Remove cells
        h_layout = QHBoxLayout()
        self.remove_cells_combo = QComboBox()
        self.points_comboboxes.append(self.remove_cells_combo)
        h_layout.addWidget(self.remove_cells_combo)
        self.remove_cells_button = QPushButton("Remove cells")
        self.remove_cells_button.clicked.connect(self.remove_cells)
        h_layout.addWidget(self.remove_cells_button)
        layout.addLayout(h_layout)

        # Merge cells
        h_layout = QHBoxLayout()
        self.merge_cells_combo = QComboBox()
        self.shape_comboboxes.append(self.merge_cells_combo)
        h_layout.addWidget(self.merge_cells_combo)
        self.merge_cells_button = QPushButton("Merge cells")
        self.merge_cells_button.clicked.connect(self.merge_cells)
        h_layout.addWidget(self.merge_cells_button)
        layout.addLayout(h_layout)

        # Reset
        self.curation_reset_button = QPushButton("Reset")
        self.curation_reset_button.clicked.connect(self.curation_reset)
        layout.addWidget(self.curation_reset_button)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def endocytic_patches_panel(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Spots channel
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Spots channel"))
        self.spots_channel_combo = QComboBox()
        self.image_comboboxes.append(self.spots_channel_combo)
        h_layout.addWidget(self.spots_channel_combo)
        layout.addLayout(h_layout)

        # Memory (t)
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Memory (t)"))
        self.patches_memory_input = QSpinBox()
        self.patches_memory_input.setRange(0, 10)
        self.patches_memory_input.setValue(TrackSpotsOperator.default_memory())
        h_layout.addWidget(self.patches_memory_input)
        layout.addLayout(h_layout)

        # Displacement (µm)
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Displacement (µm)"))
        self.patches_displacement_input = QSpinBox()
        self.patches_displacement_input.setRange(0, 100)
        self.patches_displacement_input.setValue(TrackSpotsOperator.default_max_distance())
        h_layout.addWidget(self.patches_displacement_input)
        layout.addLayout(h_layout)

        # Launch detection
        h_layout = QHBoxLayout()

        self.launch_detection_button = QPushButton("Launch detection")
        self.launch_detection_button.setFont(self.custom_font)
        self.launch_detection_button.clicked.connect(self.launch_detection)

        self.launch_spots_tracking_button = QPushButton("Launch spots tracking")
        self.launch_spots_tracking_button.setFont(self.custom_font)
        self.launch_spots_tracking_button.clicked.connect(self.launch_spots_tracking)

        h_layout.addWidget(self.launch_detection_button)
        h_layout.addWidget(self.launch_spots_tracking_button)

        layout.addLayout(h_layout)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def filtering_panel(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Points cloud
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Points cloud"))
        self.points_cloud_combo = QComboBox()
        self.track_comboboxes.append(self.points_cloud_combo)
        h_layout.addWidget(self.points_cloud_combo)
        layout.addLayout(h_layout)

        # Process features button
        self.process_features_button = QPushButton("Process features")
        self.process_features_button.setFont(self.custom_font)
        self.process_features_button.clicked.connect(self.launch_process_features)
        layout.addWidget(self.process_features_button)

        # Jittering (µm)
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Jittering"))
        self.jittering_input = QDoubleSpinBox()
        self.jittering_input.setRange(0.0, 100.0)
        self.jittering_input.setValue(3.0)
        self.jittering_input.valueChanged.connect(self.update_filtered_spots_preview)
        h_layout.addWidget(self.jittering_input)
        layout.addLayout(h_layout)

        # Min. track length (t)
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Min. track length"))
        self.min_track_length_input = QSpinBox()
        self.min_track_length_input.setRange(0, 20)
        self.min_track_length_input.setValue(5)
        self.min_track_length_input.valueChanged.connect(self.update_filtered_spots_preview)
        h_layout.addWidget(self.min_track_length_input)
        layout.addLayout(h_layout)

        # Min. proximity (µm)
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Min. proximity"))
        self.min_proximity_input = QDoubleSpinBox()
        self.min_proximity_input.setRange(0.0, 100.0)
        self.min_proximity_input.setValue(5.0)
        self.min_proximity_input.valueChanged.connect(self.update_filtered_spots_preview)
        h_layout.addWidget(self.min_proximity_input)
        layout.addLayout(h_layout)

        # Distance to membrane (µm)
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Distance to membrane"))
        self.distance_to_membrane_input = QDoubleSpinBox()
        self.distance_to_membrane_input.setRange(0.0, 100.0)
        self.distance_to_membrane_input.setValue(5.0)
        self.distance_to_membrane_input.valueChanged.connect(self.update_filtered_spots_preview)
        h_layout.addWidget(self.distance_to_membrane_input)
        layout.addLayout(h_layout)

        # Remove orphan spots
        self.remove_orphan_spots_checkbox = QCheckBox("Remove orphan spots?")
        self.remove_orphan_spots_checkbox.setChecked(True)
        self.remove_orphan_spots_checkbox.stateChanged.connect(self.update_filtered_spots_preview)
        layout.addWidget(self.remove_orphan_spots_checkbox)

        # Launch filtering
        self.launch_filtering_button = QPushButton("Apply filtering")
        self.launch_filtering_button.setFont(self.custom_font)
        self.launch_filtering_button.clicked.connect(self.launch_filtering)
        layout.addWidget(self.launch_filtering_button)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def conversion_panel(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Birth track
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Birth track"))
        self.birth_cloud_combo = QComboBox()
        self.track_comboboxes.append(self.birth_cloud_combo)
        h_layout.addWidget(self.birth_cloud_combo)
        layout.addLayout(h_layout)

        # Conversion track
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Conversion track"))
        self.conversion_cloud_combo = QComboBox()
        self.track_comboboxes.append(self.conversion_cloud_combo)
        h_layout.addWidget(self.conversion_cloud_combo)
        layout.addLayout(h_layout)

        # Binding distance
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Binding distance"))
        self.binding_distance_input = QDoubleSpinBox()
        self.binding_distance_input.setRange(0.0, 100.0)
        self.binding_distance_input.setValue(BindTracksOperator.default_bind_distance())
        h_layout.addWidget(self.binding_distance_input)
        layout.addLayout(h_layout)

        # Discard incomplete cycles
        self.discard_incomplete_cycles_checkbox = QCheckBox("Discard incomplete cycles?")
        self.discard_incomplete_cycles_checkbox.setChecked(BindTracksOperator.default_remove_incomplete_cycles())
        layout.addWidget(self.discard_incomplete_cycles_checkbox)

        # Bind tracks
        self.bind_tracks_button = QPushButton("Bind tracks")
        self.bind_tracks_button.clicked.connect(self.bind_tracks)
        layout.addWidget(self.bind_tracks_button)

        # Time factor
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Time factor"))
        self.time_factor_input = QDoubleSpinBox()
        self.time_factor_input.setRange(0.0, 100.0)
        self.time_factor_input.setValue(1.0)
        h_layout.addWidget(self.time_factor_input)
        layout.addLayout(h_layout)

        # Export counts
        h_layout = QHBoxLayout()

        self.export_counts_button = QPushButton("Export counts")
        self.export_counts_button.clicked.connect(self.export_counts)
        h_layout.addWidget(self.export_counts_button)

        self.export_details_button = QPushButton("Export details")
        self.export_details_button.clicked.connect(self.export_details)
        h_layout.addWidget(self.export_details_button)

        layout.addLayout(h_layout)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    # -------- Utils: --------------------------------------

    def process_discarded_spots(self):
        jitter = self.jittering_input.value()
        min_track_length = self.min_track_length_input.value()
        min_proximity = self.min_proximity_input.value()
        memb_distance = self.distance_to_membrane_input.value()
        remove_orphan_spots = self.remove_orphan_spots_checkbox.isChecked()

        tracks_layer_name = self.points_cloud_combo.currentText()
        spots_layer_name = tracks_layer_name.replace(self.tracked_spots_prefix, self.spots_prefix)

        if tracks_layer_name not in self.viewer.layers:
            show_warning("Selected points cloud not found in layers.")
            return (None, None, None)
        
        if spots_layer_name not in self.viewer.layers:
            show_warning("Corresponding detected spots layer not found in layers.")
            return (None, None, None)
        
        tracks_layer = self.viewer.layers[tracks_layer_name]
        spots_layer = self.viewer.layers[spots_layer_name]

        dataframe = tracks_layer.features
        if dataframe is None:
            show_warning("Selected points cloud does not have features. Please run tracking first.")
            return (None, None, None)
        
        dataframe['ok'] = (
            (dataframe['jittering'] < jitter) & 
            (dataframe['closest_neighbor_distance'] > min_proximity) & 
            ((not remove_orphan_spots) | (dataframe['cell_id'] > 0)) & 
            (dataframe['track_duration'] >= min_track_length) & 
            (dataframe['distance_to_membrane'] <= memb_distance)
        )
        return (tracks_layer, spots_layer, dataframe)
    
    def update_filtered_spots_preview(self):
        tracks_layer, spots_layer, dataframe = self.process_discarded_spots()
        if tracks_layer is None or spots_layer is None or dataframe is None:
            return
        base_lut = spots_layer.metadata.get("lut", "gray")
        new_lut = list(dataframe['ok'].map({True: base_lut, False: "gray"}).values)
        spots_layer.border_color = new_lut

    def fetch_track_layers(self):
        birth_layer_name = self.birth_cloud_combo.currentText()
        conversion_layer_name = self.conversion_cloud_combo.currentText()

        if birth_layer_name not in self.viewer.layers:
            show_warning("Selected birth cloud not found in layers.")
            return (None, None)
        
        if conversion_layer_name not in self.viewer.layers:
            show_warning("Selected conversion cloud not found in layers.")
            return (None, None)
        
        birth_layer = self.viewer.layers[birth_layer_name]
        conversion_layer = self.viewer.layers[conversion_layer_name]

        return (birth_layer, conversion_layer)
        

    # -------- Callbacks: ----------------------------------

    def get_raw_cells_layer(self):
        candidate = None
        for layer in self.viewer.layers:
            if isinstance(layer, Labels) and layer.name.startswith(self.cells_prefix):
                candidate = layer
                break
        return candidate
    
    def get_tracked_cells_layer(self):
        candidate = None
        for layer in self.viewer.layers:
            if isinstance(layer, Labels) and layer.name.startswith(self.tracked_cells_prefix):
                candidate = layer
                break
        return candidate

    def launch_segmentation(self):
        self.current_operator = SegmentCellsOperator()
        layer_name = self.segmentation_channel_combo.currentText()
        if layer_name not in self.viewer.layers:
            show_warning("Selected segmentation channel not found in layers.")
            return
        img_layer = self.viewer.layers[layer_name]
        img = img_layer.data
        self.current_operator.set_input_image(img)
        self.current_operator.set_object_diameter(self.object_diameter_input.value())
        self.current_operator.set_kill_border(self.kill_borders_checkbox.isChecked())

        worker = create_worker(
            self.current_operator.run,
            _progress={
                "desc": "Running CellPose segmentation..."
            },
        )
        
        worker.finished.connect(self.finished_segmentation)
        worker.start()

    def finished_segmentation(self, *args):
        if self.current_operator is None:
            raise ValueError("No operator is currently running.")
        
        result = self.current_operator.get_output_labels().values
        layer_name = self.segmentation_channel_combo.currentText()
        new_layer_name = f"{self.cells_prefix}{layer_name}"
        layer = self.viewer.layers[layer_name]

        if new_layer_name in self.viewer.layers:
            self.viewer.layers[new_layer_name].data = result
        else:
            self.viewer.add_labels(
                result, 
                name=new_layer_name,
                scale=layer.scale
            )
        self.current_operator = None

    def launch_cells_tracking(self):
        layer = self.get_raw_cells_layer()
        if layer is None:
            show_warning("No raw cells layer found. Please run segmentation first.")
            return
        
        self.current_operator = TrackCellsOperator()
        self.current_operator.set_input_image(layer.data)
        self.current_operator.set_memory(self.memory_input.value())
        self.current_operator.set_max_distance(self.displacement_input.value())
        self.current_operator.set_remove_incomplete(self.remove_incomplete_tracks_checkbox.isChecked())

        worker = create_worker(
            self.current_operator.run,
            _progress={
                "desc": "Running cells tracking..."
            },
        )
        
        worker.finished.connect(self.finished_cells_tracking)
        worker.start()

    def finished_cells_tracking(self, *args):
        if self.current_operator is None:
            raise ValueError("No operator is currently running.")
        
        result = self.current_operator.get_tracked_labels().values
        raw_layer = self.get_raw_cells_layer()
        raw_layer_name = raw_layer.name
        new_layer_name = raw_layer_name.replace(self.cells_prefix, self.tracked_cells_prefix)

        if new_layer_name in self.viewer.layers:
            self.viewer.layers[new_layer_name].data = result
        else:
            self.viewer.add_labels(
                result, 
                name=new_layer_name,
                scale=raw_layer.scale
            )
        self.current_operator = None

    def remove_cells(self):
        target_layer_name = self.target_layer_combo.currentText()
        if target_layer_name not in self.viewer.layers:
            show_warning("Selected target layer not found in layers.")
            return
        target_layer = self.viewer.layers[target_layer_name]
        points_layer_name = self.remove_cells_combo.currentText()
        if points_layer_name not in self.viewer.layers:
            show_warning("Selected points layer not found in layers.")
            return
        points_layer = self.viewer.layers[points_layer_name]
        points_data = points_layer.data

        save_name = f"{target_layer_name}_backup"
        if save_name in self.viewer.layers:
            self.viewer.layers[save_name].data = target_layer.data.copy()
        else:
            self.viewer.add_labels(
                target_layer.data.copy(),
                name=save_name,
                visible=False
            )

        cells_removed = CellsUtils.remove_cells(target_layer.data, points_data)
        target_layer.data = cells_removed

    def merge_cells(self):
        target_layer_name = self.target_layer_combo.currentText()
        if target_layer_name not in self.viewer.layers:
            show_warning("Selected target layer not found in layers.")
            return
        target_layer = self.viewer.layers[target_layer_name]
        shapes_layer_name = self.merge_cells_combo.currentText()
        if shapes_layer_name not in self.viewer.layers:
            show_warning("Selected shapes layer not found in layers.")
            return
        shapes_layer = self.viewer.layers[shapes_layer_name]
        shapes_data = shapes_layer.data

        save_name = f"{target_layer_name}_backup"
        if save_name in self.viewer.layers:
            self.viewer.layers[save_name].data = target_layer.data.copy()
        else:
            self.viewer.add_labels(
                target_layer.data.copy(),
                name=save_name,
                visible=False
            )

        cells_merged = CellsUtils.merge_cells(target_layer.data, shapes_data)
        target_layer.data = cells_merged

    def curation_reset(self):
        target_name = self.target_layer_combo.currentText()
        backup_name = f"{target_name}_backup"
        if backup_name not in self.viewer.layers:
            show_warning("No backup layer found for the selected target layer.")
            return
        target_layer = self.viewer.layers[target_name]
        backup_layer = self.viewer.layers[backup_name]
        target_layer.data = backup_layer.data.copy()

    def launch_detection(self):
        layer_name = self.spots_channel_combo.currentText()
        if layer_name not in self.viewer.layers:
            show_warning("Selected spots channel not found in layers.")
            return
        img_layer = self.viewer.layers[layer_name]
        img = img_layer.data
        self.current_operator = DetectSpotsOperator()
        self.current_operator.set_input_image(img)

        worker = create_worker(
            self.current_operator.run,
            _progress={
                "desc": "Running spots detection..."
            },
        )
        
        worker.finished.connect(self.finished_detection)
        worker.start()

    def finished_detection(self, *args):
        if self.current_operator is None:
            raise ValueError("No operator is currently running.")
        
        pts = self.current_operator.get_detected_spots()
        layer_name = self.spots_channel_combo.currentText()
        new_layer_name = f"{self.spots_prefix}{layer_name}"
        img_layer = self.viewer.layers[layer_name]

        if new_layer_name in self.viewer.layers:
            self.viewer.layers[new_layer_name].data = pts
        else:
            self.viewer.add_points(
                pts, 
                name=new_layer_name,
                scale=img_layer.scale,
                face_color="transparent",
                border_color=img_layer.colormap.name,
                metadata={
                    "lut": img_layer.colormap.name
                    }
            )
        self.current_operator = None

    def launch_spots_tracking(self):
        layer_name = self.spots_channel_combo.currentText()
        layer_name = f"{self.spots_prefix}{layer_name}"

        if layer_name not in self.viewer.layers:
            show_warning("Detected spots layer not found. Please run detection first.")
            return
        
        as_df = DataUtils.spots_numpy_to_df(self.viewer.layers[layer_name].data)
        self.current_operator = TrackSpotsOperator()
        self.current_operator.set_input_points(as_df)
        self.current_operator.set_memory(self.patches_memory_input.value())
        self.current_operator.set_max_distance(self.patches_displacement_input.value())

        worker = create_worker(
            self.current_operator.run,
            _progress={
                "desc": "Running spots tracking..."
            },
        )

        worker.finished.connect(self.finished_spots_tracking)
        worker.start()

    def finished_spots_tracking(self, *args):
        if self.current_operator is None:
            raise ValueError("No operator is currently running.")
        
        tracked_pts_df = self.current_operator.get_tracked_points()
        layer_name = self.spots_channel_combo.currentText()
        raw_spots_layer_name = f"{self.spots_prefix}{layer_name}"
        new_layer_name = f"{self.tracked_spots_prefix}{layer_name}"
        raw_spots_layer = self.viewer.layers[raw_spots_layer_name]

        if new_layer_name in self.viewer.layers:
            self.viewer.layers[new_layer_name].data = tracked_pts_df[['track_id', 'T', 'Y', 'X']]
        else:
            self.viewer.add_tracks(
                tracked_pts_df[['track_id', 'T', 'Y', 'X']], 
                name=new_layer_name,
                features=tracked_pts_df,
                scale=raw_spots_layer.scale,
                graph=None,
                tail_length=2,
                hide_completed_tracks=True
            )
        self.current_operator = None

    def launch_process_features(self):
        tracks_layer_name = self.points_cloud_combo.currentText()
        if tracks_layer_name not in self.viewer.layers:
            show_warning("Selected points cloud not found in layers.")
            return
        
        tracks_layer = self.viewer.layers[tracks_layer_name]
        tracks_df = tracks_layer.features
        if tracks_df is None:
            show_warning("Selected points cloud does not have features. Please run tracking first.")
            return
        
        cells_layer = self.get_tracked_cells_layer()
        if cells_layer is None:
            show_warning("Tracked cells layer not found. Please run cell tracking first.")
            return
        
        intensities_layer_name = tracks_layer_name.replace(self.tracked_spots_prefix, "")
        if intensities_layer_name not in self.viewer.layers:
            show_warning("Corresponding intensity channel not found in layers.")
            return
        
        intensities_layer = self.viewer.layers[intensities_layer_name]
        
        self.current_operator = SpotsFeaturesOperator()
        self.current_operator.set_input_points(tracks_df)
        self.current_operator.set_labels_maps(cells_layer.data)
        self.current_operator.set_intensities_maps(intensities_layer.data)
        self.current_operator.set_channel_name(intensities_layer_name)

        worker = create_worker(
            self.current_operator.run,
            _progress={
                "desc": "Processing features...",
                'total': self.current_operator.n_steps()
            },
        )

        worker.finished.connect(self.finished_process_features)
        worker.start()

    def finished_process_features(self, *args):
        if self.current_operator is None:
            raise ValueError("No operator is currently running.")
        
        features_df = self.current_operator.get_features()
        tracks_layer_name = self.points_cloud_combo.currentText()
        spots_layer_name = tracks_layer_name.replace(self.tracked_spots_prefix, self.spots_prefix)
        tracks_layer = self.viewer.layers[tracks_layer_name]
        spots_layer = self.viewer.layers[spots_layer_name]

        spots_layer.data = DataUtils.spots_df_to_numpy(features_df)
        spots_layer.features = features_df

        tracks_layer.data = features_df[['track_id', 'T', 'Y', 'X']]
        tracks_layer.features = features_df

        self.current_operator = None
        self.update_filtered_spots_preview()

    def launch_filtering(self):
        tracks_layer, spots_layer, dataframe = self.process_discarded_spots()
        if tracks_layer is None or spots_layer is None or dataframe is None:
            return
        
        dataframe = dataframe[dataframe['ok'] == True]
        dataframe = dataframe.drop(columns=['ok'])

        tracks_layer.data = dataframe[['track_id', 'T', 'Y', 'X']]
        tracks_layer.features = dataframe

        spots_layer.data = DataUtils.spots_df_to_numpy(dataframe)
        spots_layer.features = dataframe
        spots_layer.border_color = spots_layer.metadata.get("lut", "gray")

    def bind_tracks(self):
        birth, conversion = self.fetch_track_layers()
        binding_distance = self.binding_distance_input.value()
        discard_incomplete_cycles = self.discard_incomplete_cycles_checkbox.isChecked()
        
        if birth is None or conversion is None:
            return
        
        self.current_operator = BindTracksOperator()
        self.current_operator.set_remove_incomplete_cycles(discard_incomplete_cycles)
        self.current_operator.set_birth_spots(birth.features)
        self.current_operator.set_conversion_spots(conversion.features)
        self.current_operator.set_binding_distance(binding_distance)

        worker = create_worker(
            self.current_operator.run,
            _progress={
                "desc": "Binding tracks..."
            },
        )

        worker.finished.connect(self.finished_bind_tracks)
        worker.start()

    def finished_bind_tracks(self, *args):
        if self.current_operator is None:
            raise ValueError("No operator is currently running.")
        
        bound_tracks = self.current_operator.get_bound_tracks()

        if self.bound_tracks_name in self.viewer.layers:
            layer = self.viewer.layers[self.bound_tracks_name]
            layer.data = bound_tracks[['track_id', 'T', 'Y', 'X']]
            layer.features = bound_tracks
        else:
            self.viewer.add_tracks(
                bound_tracks[['track_id', 'T', 'Y', 'X']],
                name=self.bound_tracks_name,
                features=bound_tracks,
                graph=None,
                tail_length=2,
                hide_completed_tracks=True
            )

        lut = list(bound_tracks['phase'].map({0: "green", 1: "yellow", 2: "red"}).values)
        if self.bound_spots_name in self.viewer.layers:
            layer = self.viewer.layers[self.bound_spots_name]
            layer.data = DataUtils.spots_df_to_numpy(bound_tracks)
            layer.features = bound_tracks
            layer.border_color = lut
        else:
            self.viewer.add_points(
                DataUtils.spots_df_to_numpy(bound_tracks),
                name=self.bound_spots_name,
                face_color="transparent",
                border_color=lut,
                features=bound_tracks
            )

        self.current_operator = None

    def export_counts(self):
        bound_tracks_layer_name = self.bound_tracks_name
        if bound_tracks_layer_name not in self.viewer.layers:
            show_warning("No bound tracks layer found. Please run binding first.")
            return
        export_path, _ = QFileDialog.getSaveFileName(self, "Export counts to CSV", "", "CSV Files (*.csv);;All Files (*)")
        bound_tracks = self.viewer.layers[bound_tracks_layer_name].features
        time_factor = self.time_factor_input.value()
        if export_path:
            summarized = Summarizer.make_summary(bound_tracks, time_factor=time_factor)
            summarized.to_csv(export_path, index=False)

    def export_details(self):
        bound_tracks_layer_name = self.bound_tracks_name
        if bound_tracks_layer_name not in self.viewer.layers:
            show_warning("No bound tracks layer found. Please run binding first.")
            return
        export_path, _ = QFileDialog.getSaveFileName(self, "Export details to CSV", "", "CSV Files (*.csv);;All Files (*)")
        bound_tracks = self.viewer.layers[bound_tracks_layer_name].features
        if export_path:
            bound_tracks.to_csv(export_path, index=False)


def run_full():
    import tifffile as tiff
    import pandas as pd

    viewer = napari.Viewer()
    widget = SpotsConversionWidget(viewer=viewer)
    viewer.window.add_dock_widget(widget)

    c1_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c1.tif"
    c1 = tiff.imread(c1_path)
    viewer.add_image(c1, name="c1", blending="additive", colormap="green")

    c2_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c2.tif"
    c2 = tiff.imread(c2_path)
    viewer.add_image(c2, name="c2", blending="additive", colormap="red")

    raw_labels_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c1_labels.tif"
    raw_labels = tiff.imread(raw_labels_path)
    viewer.add_labels(raw_labels, name=f"{widget.cells_prefix}c1", visible=False)

    tracked_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c1_tracked.tif"
    tracked_labels = tiff.imread(tracked_path)
    viewer.add_labels(tracked_labels, name=f"{widget.tracked_cells_prefix}c1")

    c1_spots_tracked_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c1_tracked_spots_features.csv"
    c1_spots_tracked = pd.read_csv(c1_spots_tracked_path)
    
    viewer.add_points(
        DataUtils.spots_df_to_numpy(c1_spots_tracked), 
        name=f"{widget.spots_prefix}c1", 
        face_color="transparent", 
        border_color="green", 
        metadata={"lut": "green"}
    )
    
    viewer.add_tracks(
        c1_spots_tracked[['track_id', 'T', 'Y', 'X']].values,
        name=f"{widget.tracked_spots_prefix}c1", 
        features=c1_spots_tracked,
        graph=None,
        tail_length=2,
        hide_completed_tracks=True
    )


    c2_spots_tracked_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c2_tracked_spots_features.csv"
    c2_spots_tracked = pd.read_csv(c2_spots_tracked_path)

    viewer.add_points(
        DataUtils.spots_df_to_numpy(c2_spots_tracked), 
        name=f"{widget.spots_prefix}c2", 
        face_color="transparent", 
        border_color="red", 
        metadata={"lut": "red"}
    )

    viewer.add_tracks(
        c2_spots_tracked[['track_id', 'T', 'Y', 'X']].values,
        name=f"{widget.tracked_spots_prefix}c2", 
        features=c2_spots_tracked,
        graph=None,
        tail_length=2,
        hide_completed_tracks=True
    )

    napari.run()


def run():
    import tifffile as tiff
    import pandas as pd

    viewer = napari.Viewer()
    widget = SpotsConversionWidget(viewer=viewer)
    viewer.window.add_dock_widget(widget)

    c1_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c1.tif"
    c1 = tiff.imread(c1_path)
    viewer.add_image(c1, name="c1", blending="additive", colormap="green")

    c2_path = "/home/clement/Documents/projects/2220-yeasts-spots-overlap/draft/2026-06-17-dump/c2.tif"
    c2 = tiff.imread(c2_path)
    viewer.add_image(c2, name="c2", blending="additive", colormap="red")

    napari.run()


if __name__ == "__main__":
    run_full()