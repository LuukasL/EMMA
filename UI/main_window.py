import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                             QHBoxLayout, QVBoxLayout, QFrame, QLabel,
                             QPushButton, QComboBox, QSlider, QSpinBox,
                             QGroupBox, QFormLayout, QSizePolicy)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
from map_widget import MapWidget  

class SectionHeader(QLabel):
    """Custom header for sections in the side banner"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            color: white;
            padding-top: 10px;
            padding-bottom: 5px;
        """)

class SideBanner(QFrame):
    """Base side banner widget with common styling"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet("""
            background-color: #34495e;
            padding: 10px;
        """)
        
        # Fixed width for side banners, height will expand with main window
        self.setMinimumWidth(200)
        self.setMaximumWidth(200)
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 10, 5, 10)
        self.layout.setSpacing(8)
        
        # Add a title to indicate this banner's purpose
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: bold;
            padding-bottom: 10px;
            border-bottom: 1px solid #455a64;
        """)
        self.layout.addWidget(title_label)

class MissionControlBanner(SideBanner):
    """Left side banner with mission planning and control elements"""
    def __init__(self, parent=None):
        """Initialize the mission control banner with various controls"""
        super().__init__("Mission Control", parent)
        self.map_widget = MapWidget()

        # 1. Mission Selection Section
        self.layout.addWidget(SectionHeader("Mission Setup"))
        
        mission_buttons_layout = QHBoxLayout()
        
        self.new_mission_btn = QPushButton("New Mission")
        self.new_mission_btn.setStyleSheet("""
            background-color: #2980b9;
            color: white;
            padding: 8px;
            border-radius: 4px;
        """)
        mission_buttons_layout.addWidget(self.new_mission_btn)
        
        self.layout.addLayout(mission_buttons_layout)
        
        mission_type_layout = QFormLayout()
        self.mission_type_combo = QComboBox()
        self.mission_type_combo.addItems(["Patrol", "Surveillance", "Decoy"])
        self.mission_type_combo.setStyleSheet("""
            background-color: #2c3e50;
            color: white;
            padding: 6px;
            border: 1px solid #455a64;
        """)
        mission_type_layout.addRow("Mission Type:", self.mission_type_combo)
        self.layout.addLayout(mission_type_layout)
        
        # 2. Area Selection Controls
        self.layout.addWidget(SectionHeader("Area Selection"))
        
        area_buttons_layout = QHBoxLayout()
        
        self.select_area_btn = QPushButton("Select Area")
        self.select_area_btn.setStyleSheet("""
            background-color: #27ae60;
            color: white;
            padding: 8px;
            border-radius: 4px;
        """)
        area_buttons_layout.addWidget(self.select_area_btn)
        
        self.clear_selection_btn = QPushButton("Clear")
        self.clear_selection_btn.setStyleSheet("""
            background-color: #7f8c8d;
            color: white;
            padding: 8px;
            border-radius: 4px;
        """)
        area_buttons_layout.addWidget(self.clear_selection_btn)
        
        self.layout.addLayout(area_buttons_layout)
        
        self.area_size_label = QLabel("Area: Not selected")
        self.area_size_label.setStyleSheet("color: #bdc3c7;")
        self.layout.addWidget(self.area_size_label)
        
        # 3. Drone Assignment
        self.layout.addWidget(SectionHeader("Drone Assignment"))
        
        drone_form = QFormLayout()
        self.drone_combo = QComboBox()
        self.drone_combo.addItems(["Drone 1", "Drone 2", "All Drones"])
        self.drone_combo.setStyleSheet("""
            background-color: #2c3e50;
            color: white;
            padding: 6px;
            border: 1px solid #455a64;
        """)
        drone_form.addRow("Select Drone:", self.drone_combo)
        self.layout.addLayout(drone_form)
        
        self.assign_btn = QPushButton("Assign Mission")
        self.assign_btn.setStyleSheet("""
            background-color: #2980b9;
            color: white;
            padding: 8px;
            border-radius: 4px;
        """)
        self.layout.addWidget(self.assign_btn)
        
        # 4. Execution Controls
        self.layout.addWidget(SectionHeader("Execution"))
        
        self.validate_btn = QPushButton("Validate Mission")
        self.validate_btn.setStyleSheet("""
            background-color: #f39c12;
            color: white;
            padding: 8px;
            border-radius: 4px;
        """)
        self.layout.addWidget(self.validate_btn)
        
        execution_buttons = QHBoxLayout()
        
        self.launch_btn = QPushButton("LAUNCH")
        self.launch_btn.setStyleSheet("""
            background-color: #27ae60;
            color: white;
            font-weight: bold;
            padding: 12px;
            border-radius: 4px;
        """)
        execution_buttons.addWidget(self.launch_btn)
        
        self.abort_btn = QPushButton("ABORT")
        self.abort_btn.setStyleSheet("""
            background-color: #c0392b;
            color: white;
            font-weight: bold;
            padding: 12px;
            border-radius: 4px;
        """)
        self.abort_btn.setEnabled(False)  # Disabled initially
        execution_buttons.addWidget(self.abort_btn)
        
        self.layout.addLayout(execution_buttons)
        
        # Add a spacer at the bottom to push everything up
        self.layout.addStretch()
        
        # Connect signals to slots (placeholder functions for now)
        self.new_mission_btn.clicked.connect(self.on_new_mission)
        self.select_area_btn.clicked.connect(self.on_select_area)
        self.launch_btn.clicked.connect(self.on_launch_mission)

    def on_new_mission(self):
        print("New mission requested")

    def on_select_area(self):
        print("Area selection requested")

    def on_launch_mission(self):
        print("Mission launch requested")

class MainWindow(QMainWindow):
    """Main application window with map-centered layout"""
    def __init__(self):
        super().__init__()
        
        # Set window title and initial size
        self.setWindowTitle("Defence Drone Control")
        self.resize(1200, 800)
        
        # Create central widget with horizontal layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create horizontal layout for the three main sections
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create left banner with mission controls
        self.left_banner = MissionControlBanner(parent=self)
        main_layout.addWidget(self.left_banner)
        
        # Create the map widget
        self.map_widget = MapWidget()
        main_layout.addWidget(self.map_widget)
        
        # Create right banner
        self.right_banner = SideBanner("Drone Status")
        main_layout.addWidget(self.right_banner)
        
        # Set stretch factors to ensure map gets priority
        main_layout.setStretchFactor(self.left_banner, 0)   # No stretch
        main_layout.setStretchFactor(self.map_widget, 1)    # Takes all extra space
        main_layout.setStretchFactor(self.right_banner, 0)  # No stretch
        
        # Set dark theme for the application
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e272e;
                color: white;
            }
            QFrame {
                border: 1px solid #455a64;
            }
        """)

    def resizeEvent(self, event):
        """Handle window resize to maintain layout proportions"""
        super().resizeEvent(event)
        print(f"Window resized to: {self.width()}x{self.height()}")

    def closeEvent(self, event):
        """Handle application close event"""
        if hasattr(self.map_widget, 'tile_server'):
            self.map_widget.tile_server.stop()
            self.map_widget.tile_server.wait()
        super().closeEvent(event)

# For testing the layout
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


