from __future__ import annotations

from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QEvent, QTimer, Qt, QSize, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.analysis.metrics import AnalysisSnapshot, MetricsEngine
from app.analysis.spectrum import SpectrumAnalyzer
from app.analysis.genres import list_genres, get_genre
from app.audio.audio_loader import AudioLoader, AudioTrack
from app.audio.live_input import (
    LIVE_SAMPLERATE,
    LiveInputCapture,
    SystemOutputCapture,
    system_capture_setup_hint,
)
from app.audio.player import AudioPlayer
from app.coaching.coach import SafeMasteringCoach


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Half Deaf Mastering Tool")
        icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1400, 880)

        self.loader = AudioLoader()
        self.player = AudioPlayer(block_size=2048)
        self._live = LiveInputCapture()
        self._system = SystemOutputCapture()
        self.coach = SafeMasteringCoach(true_peak_target_dbtp=-1.0)
        self.current_genre = get_genre("house")

        self.main_track: AudioTrack | None = None
        self.reference_track: AudioTrack | None = None
        self.active_mode = "A"
        self._input_mode: str = "import"

        self.metrics: MetricsEngine | None = None
        self.spectrum_low: SpectrumAnalyzer | None = None
        self.spectrum_mid: SpectrumAnalyzer | None = None
        self.spectrum_high: SpectrumAnalyzer | None = None
        self.last_snapshot: AnalysisSnapshot | None = None
        self.last_chunk_mono = np.zeros(4096, dtype=np.float32)
        self.force_spectrum_silence = False
        self.meter_history_len = 96
        self.meter_history_x = np.arange(self.meter_history_len, dtype=np.float32)
        self.lufs_i_history = np.full(self.meter_history_len, np.nan, dtype=np.float32)
        self.lufs_s_history = np.full(self.meter_history_len, np.nan, dtype=np.float32)
        self.lufs_m_history = np.full(self.meter_history_len, np.nan, dtype=np.float32)
        self.sample_peak_history = np.full(self.meter_history_len, np.nan, dtype=np.float32)
        self.true_peak_history = np.full(self.meter_history_len, np.nan, dtype=np.float32)
        self.stereo_width_history = np.full(self.meter_history_len, np.nan, dtype=np.float32)
        self.correlation_history = np.full(self.meter_history_len, np.nan, dtype=np.float32)
        self.sub_history = np.full(self.meter_history_len, np.nan, dtype=np.float32)
        self.bass_history = np.full(self.meter_history_len, np.nan, dtype=np.float32)
        self.low_mid_history = np.full(self.meter_history_len, np.nan, dtype=np.float32)

        self.analysis_history: dict[str, list[float]] = {}
        self.last_spectrum_low_centers = np.array([], dtype=np.float32)
        self.last_spectrum_low_magnitudes = np.array([], dtype=np.float32)
        self.last_spectrum_low_peaks = np.array([], dtype=np.float32)
        self.max_spectrum_low_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_low_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_low_count = 0
        self.last_spectrum_mid_centers = np.array([], dtype=np.float32)
        self.last_spectrum_mid_magnitudes = np.array([], dtype=np.float32)
        self.last_spectrum_mid_peaks = np.array([], dtype=np.float32)
        self.max_spectrum_mid_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_mid_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_mid_count = 0
        self.last_spectrum_high_centers = np.array([], dtype=np.float32)
        self.last_spectrum_high_magnitudes = np.array([], dtype=np.float32)
        self.last_spectrum_high_peaks = np.array([], dtype=np.float32)
        self.max_spectrum_high_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_high_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_high_count = 0
        self.target_curve_low = np.array([], dtype=np.float32)
        self.target_curve_mid = np.array([], dtype=np.float32)
        self.target_curve_high = np.array([], dtype=np.float32)
        self.suggestion_history_lines: list[str] = []
        self.last_suggestion_signature: str | None = None
        self._panel_close_buttons: dict[QGroupBox, QPushButton] = {}
        self._spectrum_focus_buttons: dict[QGroupBox, QPushButton] = {}
        self._focused_spectrum_key: str | None = None
        self._spectrum_boxes: dict[str, QGroupBox] = {}
        self.phase_corr_value = 0.0

        self._build_ui()
        self._build_view_menu()
        self._wire_signals()
        self._refresh_system_mode_status()

        self.ui_timer = QTimer(self)
        self.ui_timer.setInterval(90)
        self.ui_timer.timeout.connect(self._refresh_plots)
        self.ui_timer.start()

        self.coaching_timer = QTimer(self)
        self.coaching_timer.setInterval(7000)
        self.coaching_timer.timeout.connect(self._update_continuous_coaching)
        self.coaching_timer.start()

        self._reset_analysis_state(clear_history=True)
        self._set_mode("import")

    def _build_ui(self) -> None:
        root = QWidget()
        outer_layout = QVBoxLayout(root)
        outer_layout.setContentsMargins(12, 6, 12, 12)
        outer_layout.setSpacing(0)

        content = QWidget()
        root_layout = QHBoxLayout(content)
        root_layout.setContentsMargins(0, 6, 0, 0)
        root_layout.setSpacing(6)
        self.root_layout = root_layout
        outer_layout.addWidget(content, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(10)
        left.setMaximumWidth(240)

        file_box = QGroupBox("Input & Reference")
        self.file_box = file_box
        file_layout = QGridLayout(file_box)
        self.open_btn = QPushButton()
        self.open_btn.setIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "folder_open_white.svg")))
        self.open_btn.setIconSize(QSize(22, 22))
        self.open_btn.setToolTip("Open Track")
        self.open_btn.setAccessibleName("Open Track")
        self.open_btn.setFixedSize(QSize(44, 32))
        self.open_ref_btn = QPushButton()
        self.open_ref_btn.setIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "folder_plus_white.svg")))
        self.open_ref_btn.setIconSize(QSize(22, 22))
        self.open_ref_btn.setToolTip("Open Reference")
        self.open_ref_btn.setAccessibleName("Open Reference")
        self.open_ref_btn.setFixedSize(QSize(44, 32))
        self.track_label = QLabel("Analysis Track")
        self.ref_label = QLabel("Reference Track")
        self.ab_btn = QPushButton("Switch to B")
        self.ab_btn.setEnabled(False)
        file_layout.addWidget(self.open_btn, 0, 0)
        file_layout.addWidget(self.track_label, 0, 1)
        file_layout.addWidget(self.open_ref_btn, 1, 0)
        file_layout.addWidget(self.ref_label, 1, 1)
        file_layout.addWidget(self.ab_btn, 2, 0, 1, 2)

        mode_box = QGroupBox("Mode")
        mode_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        mode_layout = QVBoxLayout(mode_box)
        mode_layout.setContentsMargins(8, 6, 8, 8)
        mode_layout.setSpacing(0)
        mode_layout.addWidget(self._build_mode_bar())

        playback_box = QGroupBox("Playback")
        self.playback_box = playback_box
        playback_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        playback_layout = QVBoxLayout(playback_box)
        row = QHBoxLayout()
        self.play_btn = QPushButton()
        self.play_btn.setObjectName("transportPrimaryButton")
        self.play_btn.setIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "play_white.svg")))
        self.play_btn.setToolTip("Play")
        self.play_btn.setAccessibleName("Play")
        self.play_btn.setFixedSize(QSize(44, 32))
        self.play_btn.setProperty("active", False)
        self.pause_btn = QPushButton()
        self.pause_btn.setIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "pause_white.svg")))
        self.pause_btn.setToolTip("Pause")
        self.pause_btn.setAccessibleName("Pause")
        self.pause_btn.setFixedSize(QSize(44, 32))
        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "stop_white.svg")))
        self.stop_btn.setToolTip("Stop")
        self.stop_btn.setAccessibleName("Stop")
        self.stop_btn.setFixedSize(QSize(44, 32))
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setToolTip("Reset system analysis markers")
        self.reset_btn.setAccessibleName("Reset analysis")
        self.reset_btn.setFixedSize(QSize(58, 32))
        self.reset_btn.setVisible(False)
        self.reset_btn.setEnabled(False)
        row.addWidget(self.play_btn)
        row.addWidget(self.pause_btn)
        row.addWidget(self.stop_btn)
        row.addWidget(self.reset_btn)
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.time_label = QLabel("00:00 / 00:00")
        playback_layout.addLayout(row)
        playback_layout.addWidget(self.seek_slider)
        playback_layout.addWidget(self.time_label)

        self.meter_box = QGroupBox("Safety Meters")
        meter_layout = QGridLayout(self.meter_box)
        meter_layout.setVerticalSpacing(4)
        self.lufs_i_label = QLabel("I: -- LUFS")
        self.lufs_s_label = QLabel("S: -- LUFS")
        self.lufs_m_label = QLabel("M: -- LUFS")
        self.sample_peak_label = QLabel("Sample Peak: -- dBFS")
        self.true_peak_label = QLabel("True Peak: -- dBTP")
        self.stereo_label = QLabel("Width/Correlation: --")
        self.low_end_label = QLabel("Sub/Bass/Low-mid: --")

        self.lufs_plot = self._create_meter_plot(y_min=-36.0, y_max=-6.0)
        self.lufs_i_curve = self.lufs_plot.plotItem.plot([], [], pen=pg.mkPen("#58a6ff", width=1.5))
        self.lufs_s_curve = self.lufs_plot.plotItem.plot([], [], pen=pg.mkPen("#2ea043", width=1.5))
        self.lufs_m_curve = self.lufs_plot.plotItem.plot([], [], pen=pg.mkPen("#ffd84d", width=1.5))

        self.peak_plot = self._create_meter_plot(y_min=-12.0, y_max=1.2)
        self.sample_peak_curve = self.peak_plot.plotItem.plot([], [], pen=pg.mkPen("#58a6ff", width=1.5))
        self.true_peak_curve = self.peak_plot.plotItem.plot([], [], pen=pg.mkPen("#ff9e64", width=1.5))

        self.stereo_plot = self._create_meter_plot(y_min=-1.05, y_max=2.0)
        self.stereo_width_curve = self.stereo_plot.plotItem.plot([], [], pen=pg.mkPen("#79c0ff", width=1.5))
        self.correlation_curve = self.stereo_plot.plotItem.plot([], [], pen=pg.mkPen("#2ea043", width=1.5))

        self.low_end_plot = self._create_meter_plot(y_min=-90.0, y_max=0.0)
        self.sub_curve = self.low_end_plot.plotItem.plot([], [], pen=pg.mkPen("#ff9e64", width=1.5))
        self.bass_curve = self.low_end_plot.plotItem.plot([], [], pen=pg.mkPen("#58a6ff", width=1.5))
        self.low_mid_curve = self.low_end_plot.plotItem.plot([], [], pen=pg.mkPen("#a371f7", width=1.5))

        meter_layout.addWidget(self.lufs_i_label, 0, 0)
        meter_layout.addWidget(self.lufs_s_label, 0, 1)
        meter_layout.addWidget(self.lufs_m_label, 0, 2)
        meter_layout.addWidget(self.lufs_plot, 1, 0, 1, 3)
        meter_layout.addWidget(self.sample_peak_label, 2, 0)
        meter_layout.addWidget(self.true_peak_label, 2, 1)
        meter_layout.addWidget(self.stereo_label, 2, 2)
        meter_layout.addWidget(self.peak_plot, 3, 0, 1, 2)
        meter_layout.addWidget(self.stereo_plot, 3, 2)
        meter_layout.addWidget(self.low_end_label, 4, 0, 1, 3)
        meter_layout.addWidget(self.low_end_plot, 5, 0, 1, 3)
        self.meter_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.meter_box.setFixedHeight(self.meter_box.sizeHint().height())

        settings_box = QGroupBox("Analysis Controls")
        settings_layout = QVBoxLayout(settings_box)
        settings_layout.setSpacing(8)
        self.peak_hold_toggle = QCheckBox("Peak Hold")
        self.peak_hold_toggle.setChecked(True)
        self.max_peak_toggle = QCheckBox("Peak Max")
        self.max_peak_toggle.setChecked(True)
        self.avg_peaks_toggle = QCheckBox("Peak Avg")
        self.avg_peaks_toggle.setChecked(True)
        self.house_curve_toggle = QCheckBox("Genre Curve Peak")
        self.house_curve_toggle.setChecked(True)
        self.genre_combo = QComboBox()
        for genre_key, genre_name in list_genres():
            self.genre_combo.addItem(genre_name, genre_key)
        self.tp_spin = QDoubleSpinBox()
        self.tp_spin.setRange(-3.0, 0.0)
        self.tp_spin.setSingleStep(0.1)
        self.tp_spin.setValue(-1.0)
        self.tp_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        spin_up_icon = (Path(__file__).resolve().parent / "assets" / "spin_up_white.svg").as_posix()
        spin_down_icon = (Path(__file__).resolve().parent / "assets" / "spin_down_white.svg").as_posix()
        combo_down_icon = spin_down_icon
        field_style = (
            "QComboBox, QDoubleSpinBox {"
            "background: #0d1117;"
            "border: 1px solid #586273;"
            "border-radius: 4px;"
            "padding: 4px 10px;"
            "min-height: 21px;"
            "}"
            "QComboBox {"
            "padding: 3px 28px 3px 10px;"
            "}"
            "QDoubleSpinBox {"
            "padding: 3px 28px 3px 10px;"
            "}"
            "QComboBox::drop-down {"
            "border: none;"
            "background: transparent;"
            "width: 24px;"
            "subcontrol-origin: padding;"
            "subcontrol-position: top right;"
            "}"
            "QComboBox::down-arrow {"
            f"image: url({combo_down_icon});"
            "width: 12px;"
            "height: 12px;"
            "margin-top: 2px;"
            "margin-bottom: 2px;"
            "}"
            "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {"
            "background: transparent;"
            "border: none;"
            "width: 24px;"
            "}"
            "QDoubleSpinBox::up-button {"
            "subcontrol-origin: padding;"
            "subcontrol-position: top right;"
            "height: 13px;"
            "}"
            "QDoubleSpinBox::down-button {"
            "subcontrol-origin: padding;"
            "subcontrol-position: bottom right;"
            "height: 13px;"
            "}"
            "QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow {"
            "width: 12px;"
            "height: 12px;"
            "}"
            "QDoubleSpinBox::up-arrow {"
            f"image: url({spin_up_icon});"
            "margin-top: 2px;"
            "}"
            "QDoubleSpinBox::down-arrow {"
            f"image: url({spin_down_icon});"
            "margin-bottom: 2px;"
            "}"
            "QComboBox QAbstractItemView {"
            "background: #0d1117;"
            "border: 1px solid #586273;"
            "padding: 4px;"
            "selection-background-color: #21262d;"
            "selection-color: #d0d7de;"
            "}"
        )
        self.genre_combo.setStyleSheet(field_style)
        self.tp_spin.setStyleSheet(field_style)
        self.analyze_btn = QPushButton("Analyze Heard Audio")
        settings_layout.addWidget(QLabel("Genre"))
        settings_layout.addWidget(self.genre_combo)
        settings_layout.addWidget(QLabel("True-Peak Ceiling (dBTP)"))
        settings_layout.addWidget(self.tp_spin)
        settings_layout.addSpacing(8)
        self._add_toggle_with_hint(settings_layout, self.house_curve_toggle, "#ff9e64", "dashed")
        self._add_toggle_with_hint(settings_layout, self.peak_hold_toggle, "#ffd84d", "solid")
        self._add_toggle_with_hint(settings_layout, self.max_peak_toggle, "#ff4d4f", "solid")
        self._add_toggle_with_hint(settings_layout, self.avg_peaks_toggle, "#2e89ff", "solid")

        left_layout.addWidget(mode_box)
        left_layout.addWidget(file_box)
        left_layout.addWidget(playback_box)
        left_layout.addWidget(settings_box)
        left_layout.addStretch(1)
        left_layout.addWidget(self._build_brand_badge())

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setSpacing(14)
        center.setMinimumWidth(620)
        self.center_widget = center
        self.center_layout = center_layout

        self.suggestion_box = QGroupBox("Safe Mastering Suggestions")
        suggestion_layout = QVBoxLayout(self.suggestion_box)
        self.suggestion_panel = QTextEdit()
        self.suggestion_panel.setReadOnly(True)
        self.suggestion_panel.setStyleSheet("font-size: 11px; border: none;")
        suggestion_layout.addWidget(self.suggestion_panel, 1)
        self.suggestion_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        suggestions = QWidget()
        suggestions_layout = QVBoxLayout(suggestions)
        suggestions.setMinimumWidth(300)
        suggestions.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        suggestions_layout.addWidget(self.meter_box)
        suggestions_layout.addWidget(self.suggestion_box, 1)
        self.suggestions_widget = suggestions

        # Low frequency spectrum (20-300 Hz)
        self.spectrum_plot_low = pg.PlotWidget()
        self.spectrum_plot_low.setBackground(None)
        self.spectrum_plot_low.viewport().setAutoFillBackground(False)
        self._style_spectrum_plot(
            self.spectrum_plot_low,
            title="Low Spectrum (20-300 Hz)",
            x_label="Frequency (Hz)",
            y_label="Magnitude (dBFS)",
        )
        self.spectrum_plot_low.setLogMode(x=False, y=False)
        self.spectrum_floor_db = -72.0
        self.spectrum_ceiling_db = 3.0
        self.spectrum_plot_low.setYRange(self.spectrum_floor_db, self.spectrum_ceiling_db)
        self.spectrum_bars_low = pg.BarGraphItem(x=[], height=[], width=[])
        self.spectrum_plot_low.addItem(self.spectrum_bars_low)
        self.spectrum_avg_curve_low = pg.PlotDataItem(
            [],
            [],
            pen=pg.mkPen("#ff9e64", width=2, style=Qt.PenStyle.DashLine),
        )
        self.spectrum_avg_curve_low.setZValue(15)
        self.spectrum_plot_low.addItem(self.spectrum_avg_curve_low)
        self.spectrum_avg_peaks_curve_low = pg.PlotDataItem(
            [],
            [],
            pen=pg.mkPen("#2e89ff", width=2.5),
        )
        self.spectrum_avg_peaks_curve_low.setZValue(16)
        self.spectrum_avg_peaks_curve_low.setVisible(self.avg_peaks_toggle.isChecked())
        self.spectrum_plot_low.addItem(self.spectrum_avg_peaks_curve_low)
        self.spectrum_peak_caps_low = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_peak_caps_low.setZValue(20)
        self.spectrum_plot_low.addItem(self.spectrum_peak_caps_low)
        self.spectrum_max_caps_low = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_max_caps_low.setZValue(25)
        self.spectrum_plot_low.addItem(self.spectrum_max_caps_low)
        self.zero_line_low = pg.InfiniteLine(pos=0.0, angle=0, pen=pg.mkPen("#ff8080", width=1))
        self.spectrum_plot_low.addItem(self.zero_line_low)
        self.spectrum_box_low = self._create_spectrum_box("Low Spectrum (20-300 Hz)", self.spectrum_plot_low)

        # Mid frequency spectrum (300-4000 Hz)
        self.spectrum_plot_mid = pg.PlotWidget()
        self.spectrum_plot_mid.setBackground(None)
        self.spectrum_plot_mid.viewport().setAutoFillBackground(False)
        self._style_spectrum_plot(
            self.spectrum_plot_mid,
            title="Mid Spectrum (300-4000 Hz)",
            x_label="Frequency (Hz)",
            y_label="Magnitude (dBFS)",
        )
        self.spectrum_plot_mid.setLogMode(x=False, y=False)
        self.spectrum_plot_mid.setYRange(self.spectrum_floor_db, self.spectrum_ceiling_db)
        self.spectrum_bars_mid = pg.BarGraphItem(x=[], height=[], width=[])
        self.spectrum_plot_mid.addItem(self.spectrum_bars_mid)
        self.spectrum_avg_curve_mid = pg.PlotDataItem(
            [],
            [],
            pen=pg.mkPen("#ff9e64", width=2, style=Qt.PenStyle.DashLine),
        )
        self.spectrum_avg_curve_mid.setZValue(15)
        self.spectrum_plot_mid.addItem(self.spectrum_avg_curve_mid)
        self.spectrum_avg_peaks_curve_mid = pg.PlotDataItem(
            [],
            [],
            pen=pg.mkPen("#2e89ff", width=2.5),
        )
        self.spectrum_avg_peaks_curve_mid.setZValue(16)
        self.spectrum_avg_peaks_curve_mid.setVisible(self.avg_peaks_toggle.isChecked())
        self.spectrum_plot_mid.addItem(self.spectrum_avg_peaks_curve_mid)
        self.spectrum_peak_caps_mid = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_peak_caps_mid.setZValue(20)
        self.spectrum_plot_mid.addItem(self.spectrum_peak_caps_mid)
        self.spectrum_max_caps_mid = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_max_caps_mid.setZValue(25)
        self.spectrum_plot_mid.addItem(self.spectrum_max_caps_mid)
        self.zero_line_mid = pg.InfiniteLine(pos=0.0, angle=0, pen=pg.mkPen("#ff8080", width=1))
        self.spectrum_plot_mid.addItem(self.zero_line_mid)
        self.spectrum_box_mid = self._create_spectrum_box("Mid Spectrum (300-4000 Hz)", self.spectrum_plot_mid)

        # High frequency spectrum (4000-20000 Hz)
        self.spectrum_plot_high = pg.PlotWidget()
        self.spectrum_plot_high.setBackground(None)
        self.spectrum_plot_high.viewport().setAutoFillBackground(False)
        self._style_spectrum_plot(
            self.spectrum_plot_high,
            title="High Spectrum (4000-20000 Hz)",
            x_label="Frequency (Hz)",
            y_label="Magnitude (dBFS)",
        )
        self.spectrum_plot_high.setLogMode(x=False, y=False)
        self.spectrum_plot_high.setYRange(self.spectrum_floor_db, self.spectrum_ceiling_db)
        self.spectrum_bars_high = pg.BarGraphItem(x=[], height=[], width=[])
        self.spectrum_plot_high.addItem(self.spectrum_bars_high)
        self.spectrum_avg_curve_high = pg.PlotDataItem(
            [],
            [],
            pen=pg.mkPen("#ff9e64", width=2, style=Qt.PenStyle.DashLine),
        )
        self.spectrum_avg_curve_high.setZValue(15)
        self.spectrum_plot_high.addItem(self.spectrum_avg_curve_high)
        self.spectrum_avg_peaks_curve_high = pg.PlotDataItem(
            [],
            [],
            pen=pg.mkPen("#2e89ff", width=2.5),
        )
        self.spectrum_avg_peaks_curve_high.setZValue(16)
        self.spectrum_avg_peaks_curve_high.setVisible(self.avg_peaks_toggle.isChecked())
        self.spectrum_plot_high.addItem(self.spectrum_avg_peaks_curve_high)
        self.spectrum_peak_caps_high = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_peak_caps_high.setZValue(20)
        self.spectrum_plot_high.addItem(self.spectrum_peak_caps_high)
        self.spectrum_max_caps_high = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_max_caps_high.setZValue(25)
        self.spectrum_plot_high.addItem(self.spectrum_max_caps_high)
        self.zero_line_high = pg.InfiniteLine(pos=0.0, angle=0, pen=pg.mkPen("#ff8080", width=1))
        self.spectrum_plot_high.addItem(self.zero_line_high)
        self.spectrum_box_high = self._create_spectrum_box("High Spectrum (4000-20000 Hz)", self.spectrum_plot_high)
        self._spectrum_boxes = {
            "low": self.spectrum_box_low,
            "mid": self.spectrum_box_mid,
            "high": self.spectrum_box_high,
        }
        self._install_spectrum_focus_button(self.spectrum_box_low, "low")
        self._install_spectrum_focus_button(self.spectrum_box_mid, "mid")
        self._install_spectrum_focus_button(self.spectrum_box_high, "high")

        self.spectrum_readout_label = QLabel("Spectrum readout: hover over bars")
        self.zone_legend_label = QLabel(
            "<span style='color:#8B5A2B;'>■ 200-500 Hz Mud Zone</span>  |  "
            "<span style='color:#ffd84d;'>■ ~800 Hz Presence Zone</span>  |  "
            "<span style='color:#ff4d4f;'>■ 2k-5k Hz Piercing Zone</span>"
        )

        self.phase_safety_box = QGroupBox("Phase Correlation Meters (Phase Safety)")
        phase_layout = QVBoxLayout(self.phase_safety_box)
        phase_layout.setSpacing(6)

        self.phase_safety_label = QLabel("Phase Correlation: --")
        self.phase_safety_hint_label = QLabel(
            "Safe zone: 0 to +1 (green) | Danger zone: -1 to 0 (red)"
        )
        self.phase_safety_hint_label.setStyleSheet("color: #8b949e; font-size: 10px;")

        self.phase_safety_plot = self._create_phase_meter_plot()
        self.phase_danger_region = pg.BarGraphItem(
            x=[-0.5],
            y0=[0.0],
            height=[1.0],
            width=[1.0],
            brush=pg.mkBrush(255, 77, 79, 55),
            pen=pg.mkPen(width=0),
        )
        self.phase_safe_region = pg.BarGraphItem(
            x=[0.5],
            y0=[0.0],
            height=[1.0],
            width=[1.0],
            brush=pg.mkBrush(46, 160, 67, 55),
            pen=pg.mkPen(width=0),
        )
        self.phase_corr_bar = pg.BarGraphItem(
            x=[0.0],
            y0=[0.0],
            height=[1.0],
            width=[0.0],
            brush=pg.mkBrush("#2ea043"),
            pen=pg.mkPen(width=0),
        )
        self.phase_zero_line = pg.InfiniteLine(pos=0.0, angle=90, pen=pg.mkPen("#8b949e", width=1))
        self.phase_corr_indicator = pg.InfiniteLine(pos=0.0, angle=90, pen=pg.mkPen("#d0d7de", width=2))
        self.phase_safe_region.setZValue(5)
        self.phase_danger_region.setZValue(5)
        self.phase_corr_bar.setZValue(20)
        self.phase_zero_line.setZValue(25)
        self.phase_corr_indicator.setZValue(30)
        self.phase_safety_plot.addItem(self.phase_danger_region)
        self.phase_safety_plot.addItem(self.phase_safe_region)
        self.phase_safety_plot.addItem(self.phase_corr_bar)
        self.phase_safety_plot.addItem(self.phase_zero_line)
        self.phase_safety_plot.addItem(self.phase_corr_indicator)
        phase_layout.addWidget(self.phase_safety_label)
        phase_layout.addWidget(self.phase_safety_hint_label)
        phase_layout.addWidget(self.phase_safety_plot)
        self._update_phase_safety_meter(None)

        self.report_panel = QTextEdit()
        self.report_panel.setReadOnly(True)

        self.report_box = QGroupBox("Analyze Report")
        report_layout = QVBoxLayout(self.report_box)
        report_layout.setSpacing(8)
        report_layout.addWidget(self.analyze_btn)
        report_layout.addWidget(self.report_panel, 1)

        self._install_panel_close_button(self.meter_box, self._hide_safety_meters)
        self._install_panel_close_button(self.suggestion_box, self._hide_suggestions)
        self._install_panel_close_button(self.phase_safety_box, self._hide_phase_safety)
        self._install_panel_close_button(self.report_box, self._hide_analyze_report)

        center_layout.addWidget(self.phase_safety_box)
        center_layout.addWidget(self.spectrum_box_low, 3)
        center_layout.addWidget(self.spectrum_box_mid, 3)
        center_layout.addWidget(self.spectrum_box_high, 3)
        center_layout.addWidget(self.spectrum_readout_label)
        center_layout.addWidget(self.zone_legend_label)
        center_layout.addWidget(self.report_box, 2)

        root_layout.addWidget(left, 1)
        root_layout.addWidget(center, 7)
        root_layout.addWidget(suggestions, 3)
        root_layout.setStretch(0, 0)
        root_layout.setStretch(1, 7)
        root_layout.setStretch(2, 3)
        self.suggestions_stretch = 3
        self.center_initial_stretch = 7

        self.setCentralWidget(root)
        self._apply_theme()
        self.meter_box.setVisible(False)
        self.report_box.setVisible(False)

    def _build_view_menu(self) -> None:
        self.menuBar().setNativeMenuBar(True)
        self.view_menu = self.menuBar().addMenu("View")
        self.toggle_safety_meters_action = QAction("Show Safety Meters", self)
        self.toggle_safety_meters_action.setCheckable(True)
        self.toggle_safety_meters_action.setChecked(False)
        self.view_menu.addAction(self.toggle_safety_meters_action)
        self.toggle_suggestions_action = QAction("Show Safe Mastering Suggestions", self)
        self.toggle_suggestions_action.setCheckable(True)
        self.toggle_suggestions_action.setChecked(True)
        self.view_menu.addAction(self.toggle_suggestions_action)
        self.toggle_phase_safety_action = QAction("Show Phase Correlation Meters", self)
        self.toggle_phase_safety_action.setCheckable(True)
        self.toggle_phase_safety_action.setChecked(False)
        self.view_menu.addAction(self.toggle_phase_safety_action)
        self.toggle_analyze_report_action = QAction("Show Analyze Report", self)
        self.toggle_analyze_report_action.setCheckable(True)
        self.toggle_analyze_report_action.setChecked(False)
        self.view_menu.addAction(self.toggle_analyze_report_action)

        self.help_menu = self.menuBar().addMenu("Help")
        self.support_action = QAction("Support", self)
        self.help_menu.addAction(self.support_action)

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #1f2630;
                color: #d0d7de;
                font-family: Menlo, SF Mono, monospace;
                font-size: 12px;
            }
            QGroupBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #1b222c,
                                            stop:1 #171d26);
                border: 1px solid #586273;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 13px;
                font-weight: 500;
            }
            QGroupBox * {
                font-size: 12px;
                font-weight: 400;
            }
            QGroupBox#spectrumBox {
                border: 3px solid #111821;
            }
            QGroupBox::title {
                color: #58a6ff;
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QGroupBox QLabel, QGroupBox QCheckBox, QGroupBox QSlider,
            QGroupBox QFrame, QGroupBox QWidget {
                background: transparent;
            }
            QPushButton {
                background: #21262d;
                border: 1px solid #586273;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                border-color: #58a6ff;
            }
            QPushButton#transportPrimaryButton[active="true"] {
                background: #4f89c3;
                border-color: #4f89c3;
                color: #ffffff;
            }
            QPushButton#transportPrimaryButton[active="true"]:hover {
                background: #5b95cf;
                border-color: #5b95cf;
            }
            QPushButton#panelCloseButton, QPushButton#spectrumFocusButton {
                background: #1f2630;
                color: #ffffff;
                border: 1px solid #586273;
                border-radius: 0px;
                padding: 0;
            }
            QPushButton#panelCloseButton {
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#panelCloseButton:hover, QPushButton#spectrumFocusButton:hover {
                border-color: #58a6ff;
                background: #21262d;
            }
            QToolButton#modeBtnLeft, QToolButton#modeBtnRight {
                background: #21262d;
                border: 1px solid #586273;
                border-radius: 0;
                padding: 4px 8px;
                font-size: 10px;
                color: #8b949e;
            }
            QToolButton#modeBtnLeft {
                border-top-left-radius: 5px;
                border-bottom-left-radius: 5px;
            }
            QToolButton#modeBtnRight {
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }
            QToolButton#modeBtnLeft:checked, QToolButton#modeBtnRight:checked {
                background: #388bfd;
                border-color: #388bfd;
                color: #ffffff;
            }
            QToolButton#modeBtnLeft:hover:!checked, QToolButton#modeBtnRight:hover:!checked {
                border-color: #58a6ff;
                color: #d0d7de;
            }
            QLabel#modeStatusLabel {
                color: #8b949e;
                font-size: 11px;
            }
            QFrame#brandBadge {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #1c2330,
                                            stop:1 #18202b);
                border: 1px solid #586273;
                border-radius: 8px;
            }
            QLabel#brandIcon {
                background: transparent;
            }
            QLabel#brandTitle {
                color: #d0d7de;
                font-size: 11px;
                font-weight: 700;
                background: transparent;
            }
            QLabel#brandSubtitle {
                color: #8b949e;
                font-size: 10px;
                background: transparent;
            }
            QLabel#brandStudio {
                color: #58a6ff;
                font-size: 9px;
                font-weight: 600;
                background: transparent;
            }
            QTextEdit {
                background: #0d1117;
                border: 1px solid #465264;
                border-top-color: #0b0f14;
                border-left-color: #0b0f14;
                border-right-color: #667285;
                border-bottom-color: #667285;
            }
            QSlider::groove:horizontal {
                border: 1px solid #586273;
                height: 6px;
                background: #0d1117;
            }
            QSlider::handle:horizontal {
                background: #58a6ff;
                border: 1px solid #58a6ff;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            """
        )

    # ------------------------------------------------------------------
    # Mode bar
    # ------------------------------------------------------------------

    def _build_mode_bar(self) -> QFrame:
        """Build the segmented Import / Live Input control at the top of the window."""
        bar = QFrame()
        bar.setObjectName("modeBar")
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(3)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(0)

        self.mode_import_btn = QToolButton()
        self.mode_import_btn.setObjectName("modeBtnLeft")
        self.mode_import_btn.setText("Import")
        self.mode_import_btn.setCheckable(True)
        self.mode_import_btn.setChecked(True)

        self.mode_live_btn = QToolButton()
        self.mode_live_btn.setObjectName("modeBtnRight")
        self.mode_live_btn.setText("Live Input")
        self.mode_live_btn.setCheckable(True)

        self.mode_system_btn = QToolButton()
        self.mode_system_btn.setObjectName("modeBtnLeft")
        self.mode_system_btn.setText("System")
        self.mode_system_btn.setCheckable(True)

        self.mode_placeholder_btn = QToolButton()
        self.mode_placeholder_btn.setObjectName("modeBtnRight")
        self.mode_placeholder_btn.setText("")
        self.mode_placeholder_btn.setEnabled(False)

        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self.mode_import_btn, 0)
        self._mode_group.addButton(self.mode_live_btn, 1)
        self._mode_group.addButton(self.mode_system_btn, 2)
        self._mode_group.setExclusive(True)

        self.mode_status_label = QLabel("")
        self.mode_status_label.setObjectName("modeStatusLabel")
        self.mode_status_label.setVisible(False)

        self.mode_detail_label = QLabel("")
        self.mode_detail_label.setWordWrap(True)
        self.mode_detail_label.setMinimumHeight(0)
        self.mode_detail_label.setMaximumHeight(100)
        self.mode_detail_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.mode_detail_label.setStyleSheet("color: #8b949e; font-size: 10px; padding: 3px;")
        self.mode_detail_label.setVisible(False)

        mode_buttons = [
            self.mode_import_btn,
            self.mode_live_btn,
            self.mode_system_btn,
            self.mode_placeholder_btn,
        ]
        mode_button_width = max(button.sizeHint().width() for button in mode_buttons) + 30
        mode_button_height = max(button.sizeHint().height() for button in mode_buttons) + 10
        for button in mode_buttons:
            button.setFixedSize(mode_button_width, mode_button_height)

        mode_grid_widget = QWidget()
        mode_grid_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        mode_grid_widget.setFixedSize(mode_button_width * 2, mode_button_height * 2)
        grid = QGridLayout(mode_grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing(0)

        grid.addWidget(self.mode_import_btn, 0, 0)
        grid.addWidget(self.mode_live_btn, 0, 1)
        grid.addWidget(self.mode_system_btn, 1, 0)
        grid.addWidget(self.mode_placeholder_btn, 1, 1)
        layout.addWidget(mode_grid_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(10)
        layout.addWidget(self.mode_status_label)
        layout.addWidget(self.mode_detail_label)
        return bar

    # ------------------------------------------------------------------
    # Source connection helpers & mode switching
    # ------------------------------------------------------------------

    def _connect_source(self, src: object) -> None:
        src.chunk_available.connect(self._on_chunk)
        src.position_changed.connect(self._on_position)
        src.playback_stopped.connect(self._on_playback_stopped)
        src.playback_error.connect(self._on_playback_error)
        if hasattr(src, "state_changed"):
            src.state_changed.connect(self._on_live_state_changed)

    def _disconnect_source(self, src: object) -> None:
        for sig, slot in [
            (src.chunk_available, self._on_chunk),
            (src.position_changed, self._on_position),
            (src.playback_stopped, self._on_playback_stopped),
            (src.playback_error, self._on_playback_error),
        ]:
            try:
                sig.disconnect(slot)
            except RuntimeError:
                pass
        if hasattr(src, "state_changed"):
            try:
                src.state_changed.disconnect(self._on_live_state_changed)
            except RuntimeError:
                pass

    def _set_mode(self, mode: str) -> None:
        """Switch between import, live input, and system output modes."""
        self._set_transport_button_active(False)

        # Stop any active source when switching modes
        if self._input_mode == "live":
            self._live.stop()
        elif self._input_mode == "system":
            self._system.stop()
        elif self._input_mode == "import":
            self.player.stop()

        # Disconnect both sources (safe if not yet connected)
        self._disconnect_source(self.player)
        self._disconnect_source(self._live)
        self._disconnect_source(self._system)

        self._input_mode = mode

        if mode == "import":
            self._connect_source(self.player)
            self.file_box.setVisible(True)
            self.playback_box.setTitle("Playback")
            self.seek_slider.setEnabled(True)
            self.pause_btn.setVisible(True)
            self.pause_btn.setEnabled(True)
            self.reset_btn.setVisible(False)
            self.reset_btn.setEnabled(False)
            self._set_mode_message("", "")
            self.mode_import_btn.setChecked(True)
            active_track = self._active_track()
            if active_track is not None:
                self.metrics = MetricsEngine(active_track.samplerate)
                self._configure_spectrum_analyzers(active_track.samplerate)
        elif mode == "live":
            self._connect_source(self._live)
            self.file_box.setVisible(False)
            self.playback_box.setTitle("Capture")
            self.seek_slider.setEnabled(False)
            self.pause_btn.setVisible(False)
            self.pause_btn.setEnabled(False)
            self.reset_btn.setVisible(False)
            self.reset_btn.setEnabled(False)
            self._set_mode_message("Ready", "Live Input captures the default microphone/input device.")
            self.mode_live_btn.setChecked(True)
            self._reset_analysis_state(clear_history=True)
            self.metrics = MetricsEngine(LIVE_SAMPLERATE)
            self._configure_spectrum_analyzers(LIVE_SAMPLERATE)
            self._reset_suggestion_history("Live input mode. Press Play to start listening.")
            self._set_time_label(0.0, 0.0)
        else:  # system
            self._connect_source(self._system)
            self._system.refresh_device()
            self.file_box.setVisible(False)
            self.playback_box.setTitle("System Capture")
            self.seek_slider.setEnabled(False)
            self.pause_btn.setVisible(False)
            self.pause_btn.setEnabled(False)
            self.reset_btn.setVisible(True)
            self.reset_btn.setEnabled(True)
            self.mode_system_btn.setChecked(True)
            self._reset_analysis_state(clear_history=True)
            self.metrics = MetricsEngine(LIVE_SAMPLERATE)
            self._configure_spectrum_analyzers(LIVE_SAMPLERATE)
            self._reset_suggestion_history(self._system_mode_detail())
            self._set_mode_message(self._system_mode_status(), self._system_mode_detail())
            self._set_time_label(0.0, 0.0)

    # ------------------------------------------------------------------
    # Live-specific helpers
    # ------------------------------------------------------------------

    def _configure_spectrum_analyzers(self, samplerate: int) -> None:
        """Configure spectrum analyzers and target curves for the provided sample rate."""
        self.spectrum_low = SpectrumAnalyzer(
            samplerate, display_min_hz=20.0, display_max_hz=300.0, group_hz=10.0
        )
        self.spectrum_mid = SpectrumAnalyzer(
            samplerate, display_min_hz=300.0, display_max_hz=4000.0, group_hz=50.0
        )
        self.spectrum_high = SpectrumAnalyzer(
            samplerate, display_min_hz=4000.0, display_max_hz=20000.0, group_hz=500.0
        )
        self.spectrum_plot_low.setXRange(20.0, 300.0)
        self.spectrum_plot_mid.setXRange(300.0, 4000.0)
        self.spectrum_plot_high.setXRange(4000.0, 20000.0)
        genre_key = self.genre_combo.currentData() or "house"
        self.target_curve_low = self._build_house_target_curve(self.spectrum_low.band_centers, genre_key)
        self.target_curve_mid = self._build_house_target_curve(self.spectrum_mid.band_centers, genre_key)
        self.target_curve_high = self._build_house_target_curve(self.spectrum_high.band_centers, genre_key)
        self._update_target_curve_visibility(self.house_curve_toggle.isChecked())

    def _activate_live_input(self) -> None:
        """Initialize spectrum analyzers and X ranges for 48 kHz live input."""
        self._configure_spectrum_analyzers(LIVE_SAMPLERATE)

    def _activate_system_capture(self) -> None:
        """Initialize the capture view for system output."""
        self._system.refresh_device()
        self._configure_spectrum_analyzers(LIVE_SAMPLERATE)

    def _on_live_state_changed(self, state: str) -> None:
        """Update the status label from live/system capture state changes."""
        if self._input_mode == "system":
            if state == "idle":
                self._set_mode_message(self._system_mode_status(), self._system_mode_detail())
            elif state == "listening":
                self._set_mode_message("System Output: waiting for audio…", self._system_mode_detail())
            elif state == "capturing":
                self._set_mode_message("System Output: capturing", self._system_mode_detail())
            return

        if state == "idle":
            self._set_mode_message("Ready", "Live Input captures the default microphone/input device.")
        elif state == "listening":
            self._set_mode_message("Waiting for input…", "Live Input captures the default microphone/input device.")
        elif state == "capturing":
            self._set_mode_message("Capturing", "Live Input captures the default microphone/input device.")

    @property
    def _is_source_active(self) -> bool:
        """True when audio is actively playing or being captured."""
        if self._input_mode == "live":
            return self._live.state == "capturing"
        if self._input_mode == "system":
            return self._system.state == "capturing"
        return self.player.state.is_playing

    def _system_mode_status(self) -> str:
        if self._system.has_capture_device():
            return "System Output ready"
        return "System Output needs setup"

    def _system_mode_detail(self) -> str:
        if self._system.has_capture_device():
            device_name = self._describe_system_capture_device()
            if device_name:
                return f"System will capture from {device_name}."
            return "System is ready for loopback capture."
        return system_capture_setup_hint().replace("System Output", "System")

    def _describe_system_capture_device(self) -> str:
        device_query = self._system.device_query
        if device_query is None:
            return ""
        try:
            import sounddevice as sd

            info = sd.query_devices(device_query)
        except Exception:
            return ""
        return str(info.get("name", ""))

    def _refresh_system_mode_status(self) -> None:
        self._system.refresh_device()
        if self._input_mode == "system":
            self._set_mode_message(self._system_mode_status(), self._system_mode_detail())

    def _set_mode_message(self, status: str, detail: str) -> None:
        self.mode_status_label.setText(status)
        self.mode_detail_label.setText(detail)
        self.mode_status_label.setVisible(bool(status))
        self.mode_detail_label.setVisible(bool(detail))

    def _active_capture_source(self) -> LiveInputCapture:
        if self._input_mode == "system":
            return self._system
        return self._live

    def _install_panel_close_button(self, box: QGroupBox, on_hide: callable) -> None:
        close_btn = QPushButton("X", box)
        close_btn.setObjectName("panelCloseButton")
        close_btn.setToolTip(f"Hide {box.title()}")
        close_btn.setAccessibleName(f"Hide {box.title()}")
        close_btn.setFixedSize(QSize(26, 18))
        close_btn.clicked.connect(on_hide)
        close_btn.raise_()
        self._panel_close_buttons[box] = close_btn
        box.installEventFilter(self)
        self._position_panel_close_button(box)

    def _position_panel_close_button(self, box: QGroupBox) -> None:
        close_btn = self._panel_close_buttons.get(box)
        if close_btn is None:
            return
        x_pos = max(8, box.width() - close_btn.width() - 8)
        close_btn.move(x_pos, 0)

    def _install_spectrum_focus_button(self, box: QGroupBox, key: str) -> None:
        focus_btn = QPushButton(box)
        focus_btn.setObjectName("spectrumFocusButton")
        focus_btn.setToolTip(f"Focus {box.title()}")
        focus_btn.setAccessibleName(f"Focus {box.title()}")
        focus_btn.setFixedSize(QSize(26, 18))
        self._set_spectrum_focus_button_icon(focus_btn, is_focused=False)
        focus_btn.clicked.connect(lambda _checked=False, spectrum_key=key: self._toggle_spectrum_focus(spectrum_key))
        focus_btn.raise_()
        self._spectrum_focus_buttons[box] = focus_btn
        box.installEventFilter(self)
        self._position_spectrum_focus_button(box)

    def _set_spectrum_focus_button_icon(self, button: QPushButton, is_focused: bool) -> None:
        icon_name = "compress_white.svg" if is_focused else "expand_white.svg"
        icon_path = Path(__file__).resolve().parent / "assets" / icon_name
        button.setIcon(QIcon(str(icon_path)))
        button.setIconSize(QSize(12, 12))

    def _position_spectrum_focus_button(self, box: QGroupBox) -> None:
        focus_btn = self._spectrum_focus_buttons.get(box)
        if focus_btn is None:
            return
        x_pos = max(8, box.width() - focus_btn.width() - 8)
        focus_btn.move(x_pos, 0)

    def _toggle_spectrum_focus(self, key: str) -> None:
        if self._focused_spectrum_key == key:
            self._set_spectrum_focus(None)
            return
        self._set_spectrum_focus(key)

    def _set_spectrum_focus(self, key: str | None) -> None:
        self._focused_spectrum_key = key
        for spectrum_key, box in self._spectrum_boxes.items():
            is_visible = key is None or spectrum_key == key
            box.setVisible(is_visible)

        for spectrum_key, box in self._spectrum_boxes.items():
            focus_btn = self._spectrum_focus_buttons.get(box)
            if focus_btn is None:
                continue
            if key is not None and spectrum_key == key:
                focus_btn.setText("")
                self._set_spectrum_focus_button_icon(focus_btn, is_focused=True)
                focus_btn.setToolTip("Restore all spectrum graphs")
                focus_btn.setAccessibleName("Restore all spectrum graphs")
            else:
                focus_btn.setText("")
                self._set_spectrum_focus_button_icon(focus_btn, is_focused=False)
                focus_btn.setToolTip(f"Focus {box.title()}")
                focus_btn.setAccessibleName(f"Focus {box.title()}")

        self._update_spectrum_layout_stretches()

    def _update_spectrum_layout_stretches(self) -> None:
        if self._focused_spectrum_key is None:
            self.center_layout.setStretchFactor(self.spectrum_box_low, 3)
            self.center_layout.setStretchFactor(self.spectrum_box_mid, 3)
            self.center_layout.setStretchFactor(self.spectrum_box_high, 3)
            return

        self.center_layout.setStretchFactor(self.spectrum_box_low, 0)
        self.center_layout.setStretchFactor(self.spectrum_box_mid, 0)
        self.center_layout.setStretchFactor(self.spectrum_box_high, 0)

        focused_box = self._spectrum_boxes.get(self._focused_spectrum_key)
        if focused_box is not None:
            self.center_layout.setStretchFactor(focused_box, 9)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            if watched in self._panel_close_buttons:
                self._position_panel_close_button(watched)
            if watched in self._spectrum_focus_buttons:
                self._position_spectrum_focus_button(watched)
        return super().eventFilter(watched, event)

    def _hide_safety_meters(self) -> None:
        self.toggle_safety_meters_action.setChecked(False)

    def _hide_suggestions(self) -> None:
        self.toggle_suggestions_action.setChecked(False)

    def _hide_phase_safety(self) -> None:
        self.toggle_phase_safety_action.setChecked(False)

    def _hide_analyze_report(self) -> None:
        self.toggle_analyze_report_action.setChecked(False)

    def _create_meter_plot(self, y_min: float, y_max: float) -> pg.PlotWidget:
        plot = pg.PlotWidget()
        plot.setFixedHeight(34)
        plot.setMinimumWidth(64)
        plot.setMenuEnabled(False)
        plot.setMouseEnabled(x=False, y=False)
        plot.setBackground("#0d1117")
        plot.showGrid(x=False, y=False)
        plot.plotItem.hideAxis("left")
        plot.plotItem.hideAxis("bottom")
        plot.plotItem.vb.setDefaultPadding(0.0)
        plot.plotItem.setContentsMargins(0, 0, 0, 0)
        plot.setXRange(0.0, float(self.meter_history_len - 1), padding=0.0)
        plot.setYRange(y_min, y_max, padding=0.0)
        return plot

    def _create_phase_meter_plot(self) -> pg.PlotWidget:
        plot = pg.PlotWidget()
        plot.setFixedHeight(50)
        plot.setMinimumWidth(160)
        plot.setMenuEnabled(False)
        plot.setMouseEnabled(x=False, y=False)
        plot.setBackground(None)
        plot.viewport().setAutoFillBackground(False)
        plot.setStyleSheet("background: transparent; border: none;")
        plot.showGrid(x=False, y=False)
        plot.plotItem.hideAxis("left")
        axis = plot.getAxis("bottom")
        axis.setTickFont(QFont("Menlo", 10))
        axis.setTextPen(pg.mkPen("#9aa4ad"))
        axis.setTicks([[(-1.0, "-1"), (0.0, "0"), (1.0, "+1")]])
        plot.plotItem.vb.setDefaultPadding(0.0)
        plot.plotItem.setContentsMargins(0, 0, 0, 0)
        plot.setXRange(-1.0, 1.0, padding=0.0)
        plot.setYRange(0.0, 1.0, padding=0.0)
        return plot

    def _update_phase_safety_meter(self, correlation: float | None) -> None:
        if correlation is None or not np.isfinite(correlation):
            corr = 0.0
            self.phase_safety_label.setText("Phase Correlation: --")
        else:
            corr = float(np.clip(correlation, -1.0, 1.0))
            status = "safe" if corr >= 0.0 else "warning: cancellation risk"
            self.phase_safety_label.setText(f"Phase Correlation: {corr:+.2f} ({status})")

        width = abs(corr)
        center = corr / 2.0
        bar_brush = pg.mkBrush("#2ea043" if corr >= 0.0 else "#ff4d4f")
        self.phase_corr_bar.setOpts(x=[center], width=[width], y0=[0.0], height=[1.0], brush=bar_brush)
        self.phase_corr_indicator.setValue(corr)
        self.phase_corr_value = corr

    def _style_spectrum_plot(
        self,
        plot: pg.PlotWidget,
        title: str,
        x_label: str,
        y_label: str,
    ) -> None:
        plot.setStyleSheet("border: none;")
        plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        plot.setMinimumHeight(190)
        plot.plotItem.setContentsMargins(0, 0, 0, 8)

        # Match graph text size with the app control text (12px in stylesheet).
        text_font = QFont("Menlo")
        text_font.setPixelSize(12)
        label_style = {
            "color": "#9aa4ad",
            "font-size": "12px",
            "font-family": "Menlo, SF Mono, monospace",
        }
        plot.setTitle("")
        plot.setLabel("left", y_label, **label_style)
        plot.setLabel("bottom", x_label, **label_style)
        for axis_name in ("left", "bottom"):
            axis = plot.getAxis(axis_name)
            axis.setTickFont(text_font)
            axis.setTextPen(pg.mkPen("#9aa4ad"))

    def _create_spectrum_box(self, title: str, plot: pg.PlotWidget) -> QGroupBox:
        box = QGroupBox(title)
        box.setObjectName("spectrumBox")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 0, 8, 8)
        layout.setSpacing(0)
        layout.addWidget(plot, 1)
        return box

    def _build_brand_badge(self) -> QFrame:
        """Build a professional lower-left brand badge with the app icon."""
        badge = QFrame()
        badge.setObjectName("brandBadge")
        badge.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        layout = QHBoxLayout(badge)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        icon_label = QLabel()
        icon_label.setObjectName("brandIcon")
        icon_label.setFixedSize(QSize(44, 44))
        icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path)).scaled(
                40,
                40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)

        title_label = QLabel("Half Deaf")
        title_label.setObjectName("brandTitle")
        subtitle_label = QLabel("Mastering Tool")
        subtitle_label.setObjectName("brandSubtitle")
        studio_label = QLabel("Bad Shoes Studio")
        studio_label.setObjectName("brandStudio")

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(0)
        text_col.addWidget(title_label)
        text_col.addWidget(subtitle_label)
        text_col.addWidget(studio_label)

        layout.addWidget(icon_label)
        layout.addLayout(text_col)
        layout.addStretch(1)
        return badge

    def _add_toggle_with_hint(
        self,
        settings_layout: QVBoxLayout,
        toggle: QCheckBox,
        color: str,
        line_style: str,
    ) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(toggle)
        row.addStretch(1)

        dash = "dashed" if line_style == "dashed" else "solid"
        hint_container = QWidget()
        hint_container.setStyleSheet("background: transparent;")
        hint_container.setFixedSize(34, 14)
        hint_container_layout = QVBoxLayout(hint_container)
        hint_container_layout.setContentsMargins(0, 0, 0, 0)
        hint_container_layout.setSpacing(0)
        hint_container_layout.addStretch(1)

        hint = QFrame()
        hint.setFixedSize(34, 2)
        hint.setStyleSheet(
            "QFrame {"
            "background: transparent;"
            "border: none;"
            f"border-top: 2px {dash} {color};"
            "}"
        )

        hint_container_layout.addWidget(hint)
        hint_container_layout.addStretch(1)
        row.addWidget(hint_container, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        settings_layout.addLayout(row)

    def _push_meter_value(self, history: np.ndarray, value: float) -> None:
        history[:-1] = history[1:]
        history[-1] = value

    def _reset_meter_histories(self) -> None:
        self.lufs_i_history.fill(np.nan)
        self.lufs_s_history.fill(np.nan)
        self.lufs_m_history.fill(np.nan)
        self.sample_peak_history.fill(np.nan)
        self.true_peak_history.fill(np.nan)
        self.stereo_width_history.fill(np.nan)
        self.correlation_history.fill(np.nan)
        self.sub_history.fill(np.nan)
        self.bass_history.fill(np.nan)
        self.low_mid_history.fill(np.nan)
        self._refresh_meter_curves()
        self._update_phase_safety_meter(None)

    def _refresh_meter_curves(self) -> None:
        x = self.meter_history_x
        self.lufs_i_curve.setData(x, self.lufs_i_history)
        self.lufs_s_curve.setData(x, self.lufs_s_history)
        self.lufs_m_curve.setData(x, self.lufs_m_history)
        self.sample_peak_curve.setData(x, self.sample_peak_history)
        self.true_peak_curve.setData(x, self.true_peak_history)
        self.stereo_width_curve.setData(x, self.stereo_width_history)
        self.correlation_curve.setData(x, self.correlation_history)
        self.sub_curve.setData(x, self.sub_history)
        self.bass_curve.setData(x, self.bass_history)
        self.low_mid_curve.setData(x, self.low_mid_history)

    def _wire_signals(self) -> None:
        self.toggle_safety_meters_action.toggled.connect(self.meter_box.setVisible)
        self.toggle_suggestions_action.toggled.connect(self.suggestion_box.setVisible)
        self.toggle_phase_safety_action.toggled.connect(self.phase_safety_box.setVisible)
        self.toggle_analyze_report_action.toggled.connect(self.report_box.setVisible)
        self.toggle_safety_meters_action.toggled.connect(self._update_layout_stretches)
        self.toggle_suggestions_action.toggled.connect(self._update_layout_stretches)
        self.support_action.triggered.connect(self._open_support)
        self.meter_box.setVisible(self.toggle_safety_meters_action.isChecked())
        self.suggestion_box.setVisible(self.toggle_suggestions_action.isChecked())
        self.phase_safety_box.setVisible(self.toggle_phase_safety_action.isChecked())
        self.report_box.setVisible(self.toggle_analyze_report_action.isChecked())
        self.open_btn.clicked.connect(self._open_track)
        self.open_ref_btn.clicked.connect(self._open_reference)
        self.ab_btn.clicked.connect(self._toggle_ab)

        self.play_btn.clicked.connect(self._on_play_clicked)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        self.seek_slider.sliderReleased.connect(self._on_seek)
        self.analyze_btn.clicked.connect(self._manual_analyze)
        self.tp_spin.valueChanged.connect(self.coach.set_true_peak_target)
        self.genre_combo.currentIndexChanged.connect(self._on_genre_changed)
        self.max_peak_toggle.toggled.connect(self._update_max_peak_visibility)
        self.avg_peaks_toggle.toggled.connect(self._update_avg_peak_visibility)

        self.mode_import_btn.clicked.connect(lambda: self._set_mode("import"))
        self.mode_live_btn.clicked.connect(lambda: self._set_mode("live"))
        self.mode_system_btn.clicked.connect(lambda: self._set_mode("system"))

        self.house_curve_toggle.toggled.connect(self._update_target_curve_visibility)
        self.spectrum_plot_low.scene().sigMouseMoved.connect(self._on_spectrum_low_mouse_moved)
        self.spectrum_plot_mid.scene().sigMouseMoved.connect(self._on_spectrum_mid_mouse_moved)
        self.spectrum_plot_high.scene().sigMouseMoved.connect(self._on_spectrum_high_mouse_moved)
        self._update_layout_stretches()

    def _update_layout_stretches(self, _checked: bool | None = None) -> None:
        """Collapse the right column when all right-side panels are hidden."""
        right_has_content = (not self.meter_box.isHidden()) or (not self.suggestion_box.isHidden())
        self.suggestions_widget.setVisible(right_has_content)
        if right_has_content:
            self.root_layout.setStretch(1, self.center_initial_stretch)
            self.root_layout.setStretch(2, self.suggestions_stretch)
        else:
            self.root_layout.setStretch(1, self.center_initial_stretch + self.suggestions_stretch)
            self.root_layout.setStretch(2, 0)

    def _open_track(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Track",
            "",
            "Media (*.wav *.mp3 *.flac *.ogg *.aiff *.aif *.m4a *.mp4 *.mov *.mkv *.m4v)",
        )
        if not path:
            return

        try:
            track = self.loader.load_media(path)
        except Exception as exc:
            self._show_error(str(exc))
            return

        self.main_track = track
        self.active_mode = "A"
        self.track_label.setText(Path(path).name)
        self._reset_analysis_state(clear_history=True)
        self._activate_track(track)

    def _open_reference(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Reference Track",
            "",
            "Audio (*.wav *.mp3 *.flac *.ogg *.aiff *.aif *.m4a)",
        )
        if not path:
            return

        try:
            ref = self.loader.load_media(path)
        except Exception as exc:
            self._show_error(str(exc))
            return

        if self.main_track is not None:
            ref = self._level_match_reference(self.main_track, ref)

        self.reference_track = ref
        self.ref_label.setText(Path(path).name)
        self.ab_btn.setEnabled(True)

    def _toggle_ab(self) -> None:
        if self.main_track is None or self.reference_track is None:
            return

        pos = self.player.state.position_s
        if self.active_mode == "A":
            self.active_mode = "B"
            self.ab_btn.setText("Switch to A")
            self.player.load_track(self.reference_track, keep_position_s=pos)
        else:
            self.active_mode = "A"
            self.ab_btn.setText("Switch to B")
            self.player.load_track(self.main_track, keep_position_s=pos)

    def _activate_track(self, track: AudioTrack) -> None:
        self.metrics = MetricsEngine(track.samplerate)
        self._configure_spectrum_analyzers(track.samplerate)
        self.last_snapshot = None
        self.last_chunk_mono = np.zeros(4096, dtype=np.float32)

        self.player.load_track(track)
        self._set_time_label(0.0, track.duration_s)

    def _reset_analysis_labels(self) -> None:
        self.lufs_i_label.setText("I: -- LUFS")
        self.lufs_s_label.setText("S: -- LUFS")
        self.lufs_m_label.setText("M: -- LUFS")
        self.sample_peak_label.setText("Sample Peak: -- dBFS")
        self.true_peak_label.setText("True Peak: -- dBTP")
        self.stereo_label.setText("Width/Correlation: --")
        self.low_end_label.setText("Sub/Bass/Low-mid: --")

    def _clear_spectrum_visuals(self, clear_target_curves: bool) -> None:
        if clear_target_curves:
            self.target_curve_low = np.array([], dtype=np.float32)
            self.target_curve_mid = np.array([], dtype=np.float32)
            self.target_curve_high = np.array([], dtype=np.float32)

        self.last_spectrum_low_centers = np.array([], dtype=np.float32)
        self.last_spectrum_low_magnitudes = np.array([], dtype=np.float32)
        self.last_spectrum_low_peaks = np.array([], dtype=np.float32)
        self.last_spectrum_mid_centers = np.array([], dtype=np.float32)
        self.last_spectrum_mid_magnitudes = np.array([], dtype=np.float32)
        self.last_spectrum_mid_peaks = np.array([], dtype=np.float32)
        self.last_spectrum_high_centers = np.array([], dtype=np.float32)
        self.last_spectrum_high_magnitudes = np.array([], dtype=np.float32)
        self.last_spectrum_high_peaks = np.array([], dtype=np.float32)
        self.max_spectrum_low_peaks = np.array([], dtype=np.float32)
        self.max_spectrum_mid_peaks = np.array([], dtype=np.float32)
        self.max_spectrum_high_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_low_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_mid_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_high_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_low_count = 0
        self.avg_spectrum_mid_count = 0
        self.avg_spectrum_high_count = 0

        self.spectrum_plot_low.removeItem(self.spectrum_bars_low)
        self.spectrum_bars_low = pg.BarGraphItem(x=[], height=[], width=[])
        self.spectrum_plot_low.addItem(self.spectrum_bars_low)
        self.spectrum_plot_low.removeItem(self.spectrum_peak_caps_low)
        self.spectrum_peak_caps_low = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_peak_caps_low.setZValue(20)
        self.spectrum_plot_low.addItem(self.spectrum_peak_caps_low)
        self.spectrum_plot_low.removeItem(self.spectrum_max_caps_low)
        self.spectrum_max_caps_low = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_max_caps_low.setZValue(25)
        self.spectrum_plot_low.addItem(self.spectrum_max_caps_low)
        if clear_target_curves:
            self.spectrum_avg_curve_low.setData([], [])
        self.spectrum_avg_peaks_curve_low.setData([], [])

        self.spectrum_plot_mid.removeItem(self.spectrum_bars_mid)
        self.spectrum_bars_mid = pg.BarGraphItem(x=[], height=[], width=[])
        self.spectrum_plot_mid.addItem(self.spectrum_bars_mid)
        self.spectrum_plot_mid.removeItem(self.spectrum_peak_caps_mid)
        self.spectrum_peak_caps_mid = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_peak_caps_mid.setZValue(20)
        self.spectrum_plot_mid.addItem(self.spectrum_peak_caps_mid)
        self.spectrum_plot_mid.removeItem(self.spectrum_max_caps_mid)
        self.spectrum_max_caps_mid = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_max_caps_mid.setZValue(25)
        self.spectrum_plot_mid.addItem(self.spectrum_max_caps_mid)
        if clear_target_curves:
            self.spectrum_avg_curve_mid.setData([], [])
        self.spectrum_avg_peaks_curve_mid.setData([], [])

        self.spectrum_plot_high.removeItem(self.spectrum_bars_high)
        self.spectrum_bars_high = pg.BarGraphItem(x=[], height=[], width=[])
        self.spectrum_plot_high.addItem(self.spectrum_bars_high)
        self.spectrum_plot_high.removeItem(self.spectrum_peak_caps_high)
        self.spectrum_peak_caps_high = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_peak_caps_high.setZValue(20)
        self.spectrum_plot_high.addItem(self.spectrum_peak_caps_high)
        self.spectrum_plot_high.removeItem(self.spectrum_max_caps_high)
        self.spectrum_max_caps_high = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_max_caps_high.setZValue(25)
        self.spectrum_plot_high.addItem(self.spectrum_max_caps_high)
        if clear_target_curves:
            self.spectrum_avg_curve_high.setData([], [])
        self.spectrum_avg_peaks_curve_high.setData([], [])
        self.spectrum_readout_label.setText("Spectrum readout: hover over bars")

    def _reset_metrics_for_current_input(self) -> None:
        if self._input_mode == "live":
            self.metrics = MetricsEngine(LIVE_SAMPLERATE)
        elif self._input_mode == "system":
            self.metrics = MetricsEngine(self._system.samplerate)
        else:
            track = self._active_track()
            if track is not None:
                self.metrics = MetricsEngine(track.samplerate)

    def _restart_analysis_from_now(
        self,
        suggestion_header: str,
        *,
        clear_target_curves: bool,
        reset_time_display: bool,
        clear_history: bool = False,
    ) -> None:
        self._reset_metrics_for_current_input()
        if self.spectrum_low is not None:
            self.spectrum_low.reset_state()
        if self.spectrum_mid is not None:
            self.spectrum_mid.reset_state()
        if self.spectrum_high is not None:
            self.spectrum_high.reset_state()

        self.last_snapshot = None
        self.last_chunk_mono.fill(0.0)
        self.force_spectrum_silence = True
        if clear_history:
            self.analysis_history.clear()

        self.report_panel.setPlainText(
            "Analyze report reset. Play audio and click 'Analyze Heard Audio'."
        )
        self._reset_suggestion_history(suggestion_header)
        if reset_time_display:
            self.seek_slider.setValue(0)
            self._set_time_label(0.0, 0.0)

        self._reset_analysis_labels()
        self._reset_meter_histories()
        self._clear_spectrum_visuals(clear_target_curves)

    def _reset_analysis_state(self, clear_history: bool = False) -> None:
        self.last_chunk_mono = np.zeros(4096, dtype=np.float32)
        self._restart_analysis_from_now(
            "Do this now:\n- Play audio to start live coaching.",
            clear_target_curves=True,
            reset_time_display=True,
            clear_history=clear_history,
        )

    def _level_match_reference(self, main: AudioTrack, ref: AudioTrack) -> AudioTrack:
        main_loud = self._rms_db(main.samples)
        ref_loud = self._rms_db(ref.samples)
        diff = main_loud - ref_loud
        gain = 10 ** (diff / 20.0)
        matched = np.clip(ref.samples * gain, -1.0, 1.0)
        return AudioTrack(
            path=ref.path,
            samples=matched.astype(np.float32),
            samplerate=ref.samplerate,
            duration_s=ref.duration_s,
            temp_artifacts=ref.temp_artifacts,
        )

    def _rms_db(self, samples: np.ndarray) -> float:
        mono = samples if samples.ndim == 1 else np.mean(samples[:, :2], axis=1)
        rms = np.sqrt(np.mean(mono * mono) + 1e-12)
        return float(20.0 * np.log10(rms))

    def _on_chunk(self, chunk: np.ndarray) -> None:
        if self.metrics is None:
            return

        self.force_spectrum_silence = False

        snapshot = self.metrics.update(chunk)
        self.last_snapshot = snapshot

        mono = chunk if chunk.ndim == 1 else np.mean(chunk[:, :2], axis=1)
        if mono.shape[0] >= self.last_chunk_mono.shape[0]:
            self.last_chunk_mono = mono[-self.last_chunk_mono.shape[0] :]
        else:
            self.last_chunk_mono = np.roll(self.last_chunk_mono, -mono.shape[0])
            self.last_chunk_mono[-mono.shape[0] :] = mono

        self._update_meter_labels(snapshot)

    def _on_position(self, pos_s: float) -> None:
        if self._input_mode in ("live", "system"):
            self._set_time_label(pos_s, 0.0)
            return
        track = self._active_track()
        if track is None:
            return
        if track.duration_s > 0:
            ratio = int((pos_s / track.duration_s) * 1000)
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(max(0, min(1000, ratio)))
            self.seek_slider.blockSignals(False)
        self._set_time_label(pos_s, track.duration_s)

    def _on_seek(self) -> None:
        track = self._active_track()
        if track is None:
            return
        ratio = self.seek_slider.value() / 1000.0
        self.player.seek(ratio * track.duration_s)

    def _get_bar_colors(self, centers: np.ndarray, magnitudes: np.ndarray) -> tuple[list, list]:
        """Return bar colors based on user-defined tonal zones and safety state."""
        hearing_max_hz = 16000.0
        brushes = []
        pens = []
        for freq, magnitude in zip(centers, magnitudes):
            # Safety clip alert takes priority over tonal-zone colors.
            if magnitude > 0.0:
                brushes.append(pg.mkBrush("#ff4d4f"))
                pens.append(pg.mkPen("#ff4d4f"))
            elif 200.0 <= freq <= 500.0:
                brushes.append(pg.mkBrush("#8B5A2B"))
                pens.append(pg.mkPen("#8B5A2B"))
            elif 700.0 <= freq <= 900.0:
                brushes.append(pg.mkBrush("#ffd84d"))
                pens.append(pg.mkPen("#ffd84d"))
            elif 2000.0 <= freq <= 5000.0:
                brushes.append(pg.mkBrush("#ff6b6b"))
                pens.append(pg.mkPen("#ff6b6b"))
            elif freq > hearing_max_hz:
                brushes.append(pg.mkBrush("#ffffff"))
                pens.append(pg.mkPen("#ffffff"))
            else:
                brushes.append(pg.mkBrush("#58a6ff"))
                pens.append(pg.mkPen("#58a6ff"))
        return brushes, pens

    def _build_house_target_curve(self, centers: np.ndarray, genre_key: str = "house") -> np.ndarray:
        genre = get_genre(genre_key)
        return np.interp(centers, genre.anchor_hz, genre.anchor_db).astype(np.float32)

    def _update_target_curve_visibility(self, visible: bool) -> None:
        self.spectrum_avg_curve_low.setVisible(visible)
        self.spectrum_avg_curve_mid.setVisible(visible)
        self.spectrum_avg_curve_high.setVisible(visible)

    def _on_genre_changed(self, index: int) -> None:
        """Update genre profile and rebuild target curves."""
        genre_key = self.genre_combo.currentData()
        if genre_key is None:
            return
        
        self.current_genre = get_genre(genre_key)
        self.coach.set_genre(self.current_genre)
        
        # Rebuild target curves for all three frequency bands
        if self.spectrum_low is not None:
            self.target_curve_low = self._build_house_target_curve(self.spectrum_low.band_centers, genre_key)
        if self.spectrum_mid is not None:
            self.target_curve_mid = self._build_house_target_curve(self.spectrum_mid.band_centers, genre_key)
        if self.spectrum_high is not None:
            self.target_curve_high = self._build_house_target_curve(self.spectrum_high.band_centers, genre_key)

    def _refresh_plots(self) -> None:
        if self.spectrum_low is None or self.spectrum_mid is None or self.spectrum_high is None:
            return

        should_update_avg_peaks = self._should_update_avg_peaks()
        mono_input = np.zeros_like(self.last_chunk_mono) if self.force_spectrum_silence else self.last_chunk_mono

        # Update low frequency spectrum
        centers_low, magnitudes_low, peak_magnitudes_low = self.spectrum_low.compute_bars(mono_input)
        magnitudes_low = np.clip(magnitudes_low, self.spectrum_floor_db, self.spectrum_ceiling_db)
        peak_magnitudes_low = np.clip(peak_magnitudes_low, self.spectrum_floor_db, self.spectrum_ceiling_db)
        band_widths_low = self.spectrum_low.band_widths
        self.last_spectrum_low_centers = centers_low
        self.last_spectrum_low_magnitudes = magnitudes_low
        self.last_spectrum_low_peaks = peak_magnitudes_low
        frame_peaks_low = np.maximum(magnitudes_low, peak_magnitudes_low)
        if self._is_source_active:
            if self.max_spectrum_low_peaks.size != frame_peaks_low.size:
                self.max_spectrum_low_peaks = frame_peaks_low.copy()
            else:
                self.max_spectrum_low_peaks = np.maximum(self.max_spectrum_low_peaks, frame_peaks_low)

        if should_update_avg_peaks:
            if self.avg_spectrum_low_peaks.size != magnitudes_low.size:
                self.avg_spectrum_low_peaks = magnitudes_low.astype(np.float32, copy=True)
                self.avg_spectrum_low_count = 1
            else:
                self.avg_spectrum_low_count += 1
                delta_low = magnitudes_low - self.avg_spectrum_low_peaks
                self.avg_spectrum_low_peaks += delta_low / float(self.avg_spectrum_low_count)
        bar_heights_low = magnitudes_low - self.spectrum_floor_db
        # Use 1.1x width to ensure complete coverage with overlap
        widths_low = band_widths_low * 1.1
        brushes_low, pens_low = self._get_bar_colors(centers_low, magnitudes_low)
        
        self.spectrum_plot_low.removeItem(self.spectrum_bars_low)
        self.spectrum_bars_low = pg.BarGraphItem(
            x=centers_low,
            y0=self.spectrum_floor_db,
            height=bar_heights_low,
            width=widths_low,
            brushes=brushes_low,
            pen=pg.mkPen(width=0),
        )
        self.spectrum_plot_low.addItem(self.spectrum_bars_low)
        self.spectrum_avg_curve_low.setData(centers_low, self.target_curve_low)
        if self.avg_spectrum_low_peaks.size == centers_low.size:
            self.spectrum_avg_peaks_curve_low.setData(centers_low, self.avg_spectrum_low_peaks)
        else:
            self.spectrum_avg_peaks_curve_low.setData([], [])

        if self.peak_hold_toggle.isChecked():
            cap_height = 0.28
            cap_y0_low = peak_magnitudes_low - cap_height
            self.spectrum_plot_low.removeItem(self.spectrum_peak_caps_low)
            self.spectrum_peak_caps_low = pg.BarGraphItem(
                x=centers_low,
                y0=cap_y0_low,
                height=np.full_like(centers_low, cap_height),
                width=widths_low * 0.8,
                brush="#ffd84d",
                pen=pg.mkPen("#ffd84d", width=1),
            )
            self.spectrum_peak_caps_low.setZValue(20)
            self.spectrum_plot_low.addItem(self.spectrum_peak_caps_low)
        else:
            self.spectrum_plot_low.removeItem(self.spectrum_peak_caps_low)
            self.spectrum_peak_caps_low = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
            self.spectrum_peak_caps_low.setZValue(20)
            self.spectrum_plot_low.addItem(self.spectrum_peak_caps_low)

        self.spectrum_plot_low.removeItem(self.spectrum_max_caps_low)
        if self.max_peak_toggle.isChecked() and self.max_spectrum_low_peaks.size > 0:
            max_cap_height = 0.34
            max_cap_y0_low = self.max_spectrum_low_peaks - max_cap_height
            self.spectrum_max_caps_low = pg.BarGraphItem(
                x=centers_low,
                y0=max_cap_y0_low,
                height=np.full_like(centers_low, max_cap_height),
                width=widths_low * 0.86,
                brush="#ff4d4f",
                pen=pg.mkPen("#ff4d4f", width=1),
            )
        else:
            self.spectrum_max_caps_low = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_max_caps_low.setZValue(25)
        self.spectrum_plot_low.addItem(self.spectrum_max_caps_low)

        # Update mid frequency spectrum
        centers_mid, magnitudes_mid, peak_magnitudes_mid = self.spectrum_mid.compute_bars(mono_input)
        magnitudes_mid = np.clip(magnitudes_mid, self.spectrum_floor_db, self.spectrum_ceiling_db)
        peak_magnitudes_mid = np.clip(peak_magnitudes_mid, self.spectrum_floor_db, self.spectrum_ceiling_db)
        band_widths_mid = self.spectrum_mid.band_widths
        self.last_spectrum_mid_centers = centers_mid
        self.last_spectrum_mid_magnitudes = magnitudes_mid
        self.last_spectrum_mid_peaks = peak_magnitudes_mid
        frame_peaks_mid = np.maximum(magnitudes_mid, peak_magnitudes_mid)
        if self._is_source_active:
            if self.max_spectrum_mid_peaks.size != frame_peaks_mid.size:
                self.max_spectrum_mid_peaks = frame_peaks_mid.copy()
            else:
                self.max_spectrum_mid_peaks = np.maximum(self.max_spectrum_mid_peaks, frame_peaks_mid)

        if should_update_avg_peaks:
            if self.avg_spectrum_mid_peaks.size != magnitudes_mid.size:
                self.avg_spectrum_mid_peaks = magnitudes_mid.astype(np.float32, copy=True)
                self.avg_spectrum_mid_count = 1
            else:
                self.avg_spectrum_mid_count += 1
                delta_mid = magnitudes_mid - self.avg_spectrum_mid_peaks
                self.avg_spectrum_mid_peaks += delta_mid / float(self.avg_spectrum_mid_count)
        bar_heights_mid = magnitudes_mid - self.spectrum_floor_db
        widths_mid = band_widths_mid * 1.1
        brushes_mid, pens_mid = self._get_bar_colors(centers_mid, magnitudes_mid)
        
        self.spectrum_plot_mid.removeItem(self.spectrum_bars_mid)
        self.spectrum_bars_mid = pg.BarGraphItem(
            x=centers_mid,
            y0=self.spectrum_floor_db,
            height=bar_heights_mid,
            width=widths_mid,
            brushes=brushes_mid,
            pen=pg.mkPen(width=0),
        )
        self.spectrum_plot_mid.addItem(self.spectrum_bars_mid)
        self.spectrum_avg_curve_mid.setData(centers_mid, self.target_curve_mid)
        if self.avg_spectrum_mid_peaks.size == centers_mid.size:
            self.spectrum_avg_peaks_curve_mid.setData(centers_mid, self.avg_spectrum_mid_peaks)
        else:
            self.spectrum_avg_peaks_curve_mid.setData([], [])

        if self.peak_hold_toggle.isChecked():
            cap_y0_mid = peak_magnitudes_mid - cap_height
            self.spectrum_plot_mid.removeItem(self.spectrum_peak_caps_mid)
            self.spectrum_peak_caps_mid = pg.BarGraphItem(
                x=centers_mid,
                y0=cap_y0_mid,
                height=np.full_like(centers_mid, cap_height),
                width=widths_mid * 0.8,
                brush="#ffd84d",
                pen=pg.mkPen("#ffd84d", width=1),
            )
            self.spectrum_peak_caps_mid.setZValue(20)
            self.spectrum_plot_mid.addItem(self.spectrum_peak_caps_mid)
        else:
            self.spectrum_plot_mid.removeItem(self.spectrum_peak_caps_mid)
            self.spectrum_peak_caps_mid = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
            self.spectrum_peak_caps_mid.setZValue(20)
            self.spectrum_plot_mid.addItem(self.spectrum_peak_caps_mid)

        self.spectrum_plot_mid.removeItem(self.spectrum_max_caps_mid)
        if self.max_peak_toggle.isChecked() and self.max_spectrum_mid_peaks.size > 0:
            max_cap_height = 0.34
            max_cap_y0_mid = self.max_spectrum_mid_peaks - max_cap_height
            self.spectrum_max_caps_mid = pg.BarGraphItem(
                x=centers_mid,
                y0=max_cap_y0_mid,
                height=np.full_like(centers_mid, max_cap_height),
                width=widths_mid * 0.86,
                brush="#ff4d4f",
                pen=pg.mkPen("#ff4d4f", width=1),
            )
        else:
            self.spectrum_max_caps_mid = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_max_caps_mid.setZValue(25)
        self.spectrum_plot_mid.addItem(self.spectrum_max_caps_mid)

        # Update high frequency spectrum
        centers_high, magnitudes_high, peak_magnitudes_high = self.spectrum_high.compute_bars(mono_input)
        magnitudes_high = np.clip(magnitudes_high, self.spectrum_floor_db, self.spectrum_ceiling_db)
        peak_magnitudes_high = np.clip(peak_magnitudes_high, self.spectrum_floor_db, self.spectrum_ceiling_db)
        band_widths_high = self.spectrum_high.band_widths
        self.last_spectrum_high_centers = centers_high
        self.last_spectrum_high_magnitudes = magnitudes_high
        self.last_spectrum_high_peaks = peak_magnitudes_high
        frame_peaks_high = np.maximum(magnitudes_high, peak_magnitudes_high)
        if self._is_source_active:
            if self.max_spectrum_high_peaks.size != frame_peaks_high.size:
                self.max_spectrum_high_peaks = frame_peaks_high.copy()
            else:
                self.max_spectrum_high_peaks = np.maximum(self.max_spectrum_high_peaks, frame_peaks_high)

        if should_update_avg_peaks:
            if self.avg_spectrum_high_peaks.size != magnitudes_high.size:
                self.avg_spectrum_high_peaks = magnitudes_high.astype(np.float32, copy=True)
                self.avg_spectrum_high_count = 1
            else:
                self.avg_spectrum_high_count += 1
                delta_high = magnitudes_high - self.avg_spectrum_high_peaks
                self.avg_spectrum_high_peaks += delta_high / float(self.avg_spectrum_high_count)
        bar_heights_high = magnitudes_high - self.spectrum_floor_db
        widths_high = band_widths_high * 1.1
        brushes_high, pens_high = self._get_bar_colors(centers_high, magnitudes_high)
        
        self.spectrum_plot_high.removeItem(self.spectrum_bars_high)
        self.spectrum_bars_high = pg.BarGraphItem(
            x=centers_high,
            y0=self.spectrum_floor_db,
            height=bar_heights_high,
            width=widths_high,
            brushes=brushes_high,
            pen=pg.mkPen(width=0),
        )
        self.spectrum_plot_high.addItem(self.spectrum_bars_high)
        self.spectrum_avg_curve_high.setData(centers_high, self.target_curve_high)
        if self.avg_spectrum_high_peaks.size == centers_high.size:
            self.spectrum_avg_peaks_curve_high.setData(centers_high, self.avg_spectrum_high_peaks)
        else:
            self.spectrum_avg_peaks_curve_high.setData([], [])

        if self.peak_hold_toggle.isChecked():
            cap_y0_high = peak_magnitudes_high - cap_height
            self.spectrum_plot_high.removeItem(self.spectrum_peak_caps_high)
            self.spectrum_peak_caps_high = pg.BarGraphItem(
                x=centers_high,
                y0=cap_y0_high,
                height=np.full_like(centers_high, cap_height),
                width=widths_high * 0.8,
                brush="#ffd84d",
                pen=pg.mkPen("#ffd84d", width=1),
            )
            self.spectrum_peak_caps_high.setZValue(20)
            self.spectrum_plot_high.addItem(self.spectrum_peak_caps_high)
        else:
            self.spectrum_plot_high.removeItem(self.spectrum_peak_caps_high)
            self.spectrum_peak_caps_high = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
            self.spectrum_peak_caps_high.setZValue(20)
            self.spectrum_plot_high.addItem(self.spectrum_peak_caps_high)

        self.spectrum_plot_high.removeItem(self.spectrum_max_caps_high)
        if self.max_peak_toggle.isChecked() and self.max_spectrum_high_peaks.size > 0:
            max_cap_height = 0.34
            max_cap_y0_high = self.max_spectrum_high_peaks - max_cap_height
            self.spectrum_max_caps_high = pg.BarGraphItem(
                x=centers_high,
                y0=max_cap_y0_high,
                height=np.full_like(centers_high, max_cap_height),
                width=widths_high * 0.86,
                brush="#ff4d4f",
                pen=pg.mkPen("#ff4d4f", width=1),
            )
        else:
            self.spectrum_max_caps_high = pg.BarGraphItem(x=[], y0=[], height=[], width=[])
        self.spectrum_max_caps_high.setZValue(25)
        self.spectrum_plot_high.addItem(self.spectrum_max_caps_high)

    def _should_update_avg_peaks(self) -> bool:
        if self._input_mode in ("live", "system"):
            if self._input_mode == "live":
                return self._live.state == "capturing"
            return self._system.state == "capturing"

        if not self.player.state.is_playing:
            return False

        track = self._active_track()
        if track is None or track.duration_s <= 0:
            return False

        # Freeze averaging once playback reaches the end to avoid tail-padding skew.
        return self.player.state.position_s < (track.duration_s - 1e-3)

    def _update_max_peak_visibility(self, visible: bool) -> None:
        self.spectrum_max_caps_low.setVisible(visible)
        self.spectrum_max_caps_mid.setVisible(visible)
        self.spectrum_max_caps_high.setVisible(visible)

    def _update_avg_peak_visibility(self, visible: bool) -> None:
        self.spectrum_avg_peaks_curve_low.setVisible(visible)
        self.spectrum_avg_peaks_curve_mid.setVisible(visible)
        self.spectrum_avg_peaks_curve_high.setVisible(visible)

    def _on_stop_clicked(self) -> None:
        self._set_transport_button_active(False)
        if self._input_mode == "live":
            self._live.stop()
            self.force_spectrum_silence = True
            self.last_chunk_mono.fill(0.0)
            self._reset_meter_histories()
            return
        if self._input_mode == "system":
            self._system.stop()
            self.force_spectrum_silence = True
            self.last_chunk_mono.fill(0.0)
            self._reset_meter_histories()
            return
        self.player.stop()
        if not self.max_peak_toggle.isChecked():
            self.max_spectrum_low_peaks = np.array([], dtype=np.float32)
            self.max_spectrum_mid_peaks = np.array([], dtype=np.float32)
            self.max_spectrum_high_peaks = np.array([], dtype=np.float32)
        if not self.avg_peaks_toggle.isChecked():
            self.avg_spectrum_low_peaks = np.array([], dtype=np.float32)
            self.avg_spectrum_mid_peaks = np.array([], dtype=np.float32)
            self.avg_spectrum_high_peaks = np.array([], dtype=np.float32)
            self.avg_spectrum_low_count = 0
            self.avg_spectrum_mid_count = 0
            self.avg_spectrum_high_count = 0
            self.spectrum_avg_peaks_curve_low.setData([], [])
            self.spectrum_avg_peaks_curve_mid.setData([], [])
            self.spectrum_avg_peaks_curve_high.setData([], [])
        self._reset_meter_histories()

    def _on_reset_clicked(self) -> None:
        if self._input_mode != "system":
            return
        self._restart_analysis_from_now(
            "System capture analysis restarted. Listening from this moment...",
            clear_target_curves=False,
            reset_time_display=False,
        )

    def _on_play_clicked(self) -> None:
        if self._input_mode == "live":
            self._activate_live_input()
            self._reset_analysis_for_new_playback()
            self._reset_suggestion_history("New live capture started. Listening for audio…")
            self.force_spectrum_silence = False
            self._live.play()
            self._set_transport_button_active(True)
            return
        if self._input_mode == "system":
            self._activate_system_capture()
            if not self._system.has_capture_device():
                self._set_transport_button_active(False)
                self._show_error(self._system_mode_detail())
                return
            self._reset_analysis_for_new_playback()
            self._reset_suggestion_history("New system capture started. Listening for playback…")
            self.force_spectrum_silence = False
            self._system.play()
            self._set_transport_button_active(True)
            return
        if not self.player.state.is_playing:
            self._reset_suggestion_history(
                "New playback run started. Timestamped coaching timeline restarted."
            )
            self._reset_analysis_for_new_playback()
        self.force_spectrum_silence = False
        self.player.play()
        self._set_transport_button_active(True)

    def _on_pause_clicked(self) -> None:
        self.player.pause()
        self._set_transport_button_active(False)

    def _on_playback_stopped(self) -> None:
        # Force live bars to settle to silence after stop/end.
        self._set_transport_button_active(False)
        self.force_spectrum_silence = True
        self.last_chunk_mono.fill(0.0)

    def _set_transport_button_active(self, active: bool) -> None:
        self.play_btn.setProperty("active", active)
        self.play_btn.style().unpolish(self.play_btn)
        self.play_btn.style().polish(self.play_btn)
        self.play_btn.update()

    def _reset_analysis_for_new_playback(self) -> None:
        """Start each playback/capture run with fresh analysis metrics and overlays."""
        self._reset_metrics_for_current_input()

        if self.spectrum_low is not None:
            self.spectrum_low.reset_state()
        if self.spectrum_mid is not None:
            self.spectrum_mid.reset_state()
        if self.spectrum_high is not None:
            self.spectrum_high.reset_state()

        self.last_snapshot = None
        self.last_chunk_mono.fill(0.0)
        self.force_spectrum_silence = True

        self.max_spectrum_low_peaks = np.array([], dtype=np.float32)
        self.max_spectrum_mid_peaks = np.array([], dtype=np.float32)
        self.max_spectrum_high_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_low_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_mid_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_high_peaks = np.array([], dtype=np.float32)
        self.avg_spectrum_low_count = 0
        self.avg_spectrum_mid_count = 0
        self.avg_spectrum_high_count = 0

        self.spectrum_avg_peaks_curve_low.setData([], [])
        self.spectrum_avg_peaks_curve_mid.setData([], [])
        self.spectrum_avg_peaks_curve_high.setData([], [])

        self._reset_meter_histories()
        self._reset_analysis_labels()

    def _update_meter_labels(self, snapshot: AnalysisSnapshot) -> None:
        self.lufs_i_label.setText(f"I: {snapshot.lufs_integrated:.1f} LUFS")
        self.lufs_s_label.setText(f"S: {snapshot.lufs_short_term:.1f} LUFS")
        self.lufs_m_label.setText(f"M: {snapshot.lufs_momentary:.1f} LUFS")
        self.sample_peak_label.setText(f"Sample Peak: {snapshot.sample_peak_dbfs:.2f} dBFS")
        self.true_peak_label.setText(f"True Peak: {snapshot.true_peak_dbtp:.2f} dBTP")
        self.stereo_label.setText(
            f"Width: {snapshot.stereo_width:.2f} | Corr: {snapshot.correlation:.2f}"
        )
        self.low_end_label.setText(
            "Sub/Bass/Low-mid: "
            f"{snapshot.sub_db:.1f} / {snapshot.bass_db:.1f} / {snapshot.low_mid_db:.1f} dB"
        )

        self._push_meter_value(self.lufs_i_history, snapshot.lufs_integrated)
        self._push_meter_value(self.lufs_s_history, snapshot.lufs_short_term)
        self._push_meter_value(self.lufs_m_history, snapshot.lufs_momentary)
        self._push_meter_value(self.sample_peak_history, snapshot.sample_peak_dbfs)
        self._push_meter_value(self.true_peak_history, snapshot.true_peak_dbtp)
        self._push_meter_value(self.stereo_width_history, snapshot.stereo_width)
        self._push_meter_value(self.correlation_history, snapshot.correlation)
        self._push_meter_value(self.sub_history, snapshot.sub_db)
        self._push_meter_value(self.bass_history, snapshot.bass_db)
        self._push_meter_value(self.low_mid_history, snapshot.low_mid_db)
        self._refresh_meter_curves()
        self._update_phase_safety_meter(snapshot.correlation)

    def _reset_suggestion_history(self, header_text: str) -> None:
        """Clear suggestion event history and show starter text."""
        self.suggestion_history_lines = [header_text]
        self.last_suggestion_signature = None
        self.suggestion_panel.setPlainText("\n".join(self.suggestion_history_lines))

    def _append_suggestion_event(self, reason: str, actions: list[str]) -> None:
        """Append one timestamped coaching event to suggestion history."""
        pos_s = self._live._elapsed_s if self._input_mode == "live" else self.player.state.position_s
        timestamp = self._fmt_time(pos_s)
        lines = [f"[{timestamp}] {reason}"]
        for action in actions[:3]:
            lines.append(f"- {action}")
        lines.append("")

        self.suggestion_history_lines.extend(lines)
        if len(self.suggestion_history_lines) > 240:
            self.suggestion_history_lines = self.suggestion_history_lines[-240:]

        self.suggestion_panel.setPlainText("\n".join(self.suggestion_history_lines))

    def _update_continuous_coaching(self) -> None:
        if self.last_snapshot is None or not self._is_source_active:
            return
        report = self.coach.generate(
            self.last_snapshot,
            low_end_curve_delta_db=self._low_end_curve_delta_db(),
        )
        curve_suggestion = self._curve_excess_suggestion()
        actions = list(report.do_now_actions)
        if (
            curve_suggestion is not None
            and not any("hz" in action.lower() or "khz" in action.lower() for action in actions)
        ):
            actions.insert(0, curve_suggestion[1])

        if curve_suggestion is not None:
            reason = curve_suggestion[0]
        else:
            reason = report.top_issues[0]

        signature = f"{reason}|{'|'.join(actions[:3])}"
        if signature == self.last_suggestion_signature:
            return

        self.last_suggestion_signature = signature
        self._append_suggestion_event(reason, actions)

    def _manual_analyze(self) -> None:
        if self.last_snapshot is None:
            self.report_panel.setPlainText("No audio has been analyzed yet.")
            return

        report = self.coach.generate(
            self.last_snapshot,
            low_end_curve_delta_db=self._low_end_curve_delta_db(),
        )
        curve_suggestion = self._curve_excess_suggestion()
        actions = list(report.do_now_actions)
        if (
            curve_suggestion is not None
            and not any("hz" in action.lower() or "khz" in action.lower() for action in actions)
        ):
            actions.insert(0, curve_suggestion[1])

        track = self._active_track()
        track_key = track.path if track is not None else "unknown"
        self.analysis_history.setdefault(track_key, []).append(report.score)
        trend = self._trend_text(self.analysis_history[track_key])

        issues = list(report.top_issues)
        if curve_suggestion is not None and curve_suggestion[0] not in issues:
            issues.insert(0, curve_suggestion[0])

        lines = ["Top issues:"]
        for issue in issues[:5]:
            lines.append(f"- {issue}")

        lines.append("")
        lines.append("EQ/Gain actions:")
        for action in actions[:3]:
            lines.append(f"- {action}")

        eq_lines = [
            action
            for action in actions
            if "hz" in action.lower() or "khz" in action.lower()
        ]
        if eq_lines:
            lines.append(f"EQ action (exact): {eq_lines[0]}")
        else:
            lines.append(
                "EQ action (exact): Keep 20-350 Hz at 0.0 dB adjustment. No EQ correction needed yet."
            )

        peak_over = self.last_snapshot.true_peak_dbtp - self.tp_spin.value()
        if peak_over > 0:
            trim = peak_over + 0.2
            lines.append(
                f"Gain/headroom action: Lower master gain by {trim:.1f} dB. True peak is above safety target."
            )
        else:
            lines.append(
                "Gain/headroom action: Keep master gain at 0.0 dB trim. Current headroom is within target."
            )

        lines.append("")
        lines.append(f"Confidence: {report.confidence_note}")
        lines.append(f"Trend across analyzes: {trend}")

        self.report_panel.setPlainText("\n".join(lines))
        self._update_continuous_coaching()

    def _curve_excess_suggestion(self) -> tuple[str, str] | None:
        """Return issue/action when any spectrum region is meaningfully above genre curve."""
        threshold_db = 0.6
        min_segment_bins = 1
        candidates: list[tuple[float, float, float, float]] = []

        band_sets = [
            (
                self.last_spectrum_low_centers,
                self.last_spectrum_low_magnitudes,
                self.last_spectrum_low_peaks,
                self.target_curve_low,
            ),
            (
                self.last_spectrum_mid_centers,
                self.last_spectrum_mid_magnitudes,
                self.last_spectrum_mid_peaks,
                self.target_curve_mid,
            ),
            (
                self.last_spectrum_high_centers,
                self.last_spectrum_high_magnitudes,
                self.last_spectrum_high_peaks,
                self.target_curve_high,
            ),
        ]

        for centers, magnitudes, peaks, target in band_sets:
            if centers.size == 0 or magnitudes.size == 0 or target.size == 0:
                continue
            if peaks.size == 0:
                compare_mag = magnitudes
            else:
                compare_mag = np.maximum(magnitudes, peaks)

            if centers.size != compare_mag.size or centers.size != target.size:
                continue

            delta = compare_mag - target
            over_idx = np.where(delta > threshold_db)[0]
            if over_idx.size == 0:
                continue

            split_points = np.where(np.diff(over_idx) > 1)[0] + 1
            segments = np.split(over_idx, split_points)
            for segment in segments:
                if segment.size < min_segment_bins:
                    continue

                lo_hz = float(centers[segment[0]])
                hi_hz = float(centers[segment[-1]])
                peak_db = float(np.max(delta[segment]))
                mean_db = float(np.mean(delta[segment]))
                score = mean_db + (0.4 * peak_db)
                candidates.append((score, lo_hz, hi_hz, peak_db))

        if not candidates:
            return None

        _, lo_hz, hi_hz, peak_db = max(candidates, key=lambda item: item[0])
        suggested_cut = min(3.0, max(0.5, round(peak_db * 0.6, 1)))
        issue = (
            f"Genre curve is exceeded around {lo_hz:.0f}-{hi_hz:.0f} Hz "
            f"(peak +{peak_db:.1f} dB)."
        )
        action = (
            f"Reduce {lo_hz:.0f}-{hi_hz:.0f} Hz by {suggested_cut:.1f} dB "
            f"to align with {self.current_genre.name} target."
        )
        return issue, action

    def _low_end_curve_delta_db(self) -> float | None:
        """Average 50-90 Hz amount above the selected genre curve.

        Positive values mean spectrum is above target curve.
        """
        if (
            self.last_spectrum_low_centers.size == 0
            or self.last_spectrum_low_magnitudes.size == 0
            or self.target_curve_low.size == 0
        ):
            return None

        mask = (self.last_spectrum_low_centers >= 50.0) & (self.last_spectrum_low_centers <= 90.0)
        if not np.any(mask):
            return None

        delta = self.last_spectrum_low_magnitudes[mask] - self.target_curve_low[mask]
        return float(np.mean(delta))

    def _trend_text(self, scores: list[float]) -> str:
        if len(scores) < 2:
            return "Not enough history yet"
        if scores[-1] > scores[-2] + 1:
            return "Improving"
        if scores[-1] < scores[-2] - 1:
            return "Worsening"
        return "Stable"

    def _set_time_label(self, current: float, duration: float) -> None:
        if duration > 0:
            self.time_label.setText(f"{self._fmt_time(current)} / {self._fmt_time(duration)}")
        else:
            self.time_label.setText(self._fmt_time(current))

    def _fmt_time(self, seconds: float) -> str:
        total = int(max(seconds, 0))
        m, s = divmod(total, 60)
        return f"{m:02d}:{s:02d}"

    def _on_spectrum_low_mouse_moved(self, pos) -> None:
        if self.last_spectrum_low_centers.size == 0:
            return
        if not self.spectrum_plot_low.sceneBoundingRect().contains(pos):
            return

        mouse_point = self.spectrum_plot_low.plotItem.vb.mapSceneToView(pos)
        freq_est = mouse_point.x()
        idx = int(np.argmin(np.abs(self.last_spectrum_low_centers - freq_est)))
        freq = float(self.last_spectrum_low_centers[idx])
        db = float(self.last_spectrum_low_magnitudes[idx])
        self.spectrum_readout_label.setText(
            f"Low Spectrum: ~{freq:.0f} Hz @ {db:.1f} dB"
        )

    def _on_spectrum_mid_mouse_moved(self, pos) -> None:
        if self.last_spectrum_mid_centers.size == 0:
            return
        if not self.spectrum_plot_mid.sceneBoundingRect().contains(pos):
            return

        mouse_point = self.spectrum_plot_mid.plotItem.vb.mapSceneToView(pos)
        freq_est = mouse_point.x()
        idx = int(np.argmin(np.abs(self.last_spectrum_mid_centers - freq_est)))
        freq = float(self.last_spectrum_mid_centers[idx])
        db = float(self.last_spectrum_mid_magnitudes[idx])
        self.spectrum_readout_label.setText(
            f"Mid Spectrum: ~{freq:.0f} Hz @ {db:.1f} dB"
        )

    def _on_spectrum_high_mouse_moved(self, pos) -> None:
        if self.last_spectrum_high_centers.size == 0:
            return
        if not self.spectrum_plot_high.sceneBoundingRect().contains(pos):
            return

        mouse_point = self.spectrum_plot_high.plotItem.vb.mapSceneToView(pos)
        freq_est = mouse_point.x()
        idx = int(np.argmin(np.abs(self.last_spectrum_high_centers - freq_est)))
        freq = float(self.last_spectrum_high_centers[idx])
        db = float(self.last_spectrum_high_magnitudes[idx])
        self.spectrum_readout_label.setText(
            f"High Spectrum: ~{freq:.0f} Hz @ {db:.1f} dB"
        )

    def _active_track(self) -> AudioTrack | None:
        if self.active_mode == "B" and self.reference_track is not None:
            return self.reference_track
        return self.main_track

    def _on_playback_error(self, msg: str) -> None:
        self._set_transport_button_active(False)
        if "brew install ffmpeg" in msg:
            self._show_error(msg)
            return
        if msg:
            self._show_error(msg)

    def _open_support(self) -> None:
        QDesktopServices.openUrl(QUrl("https://github.com/spatek01/halfdeaf/blob/main/README.md"))

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.player.stop()
        self._live.stop()
        self._system.stop()
        self.loader.cleanup()
        super().closeEvent(event)
