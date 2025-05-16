# map_widget.py - ultra-simplified version
import os
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import Qt, QUrl
from tile_server import LocalTileServer

class MapWidget(QFrame):
    """Simple offline map widget - display only, no interaction"""
    def __init__(self, parent=None, initial_lat=64.185717, initial_lon=27.704128, initial_zoom=15):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        # Store initial map position
        self.initial_lat = initial_lat
        self.initial_lon = initial_lon
        self.initial_zoom = initial_zoom
        
        # Initialize web view
        self.web_view = QWebEngineView()
        self.web_view.setMinimumSize(800, 800)

        # Optimize web view performance
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)

        # Set up paths
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.resource_dir = os.path.join(self.app_dir, 'resources')
        self.cache_dir = os.path.join(self.app_dir, 'cache')
        os.makedirs(self.resource_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Loading placeholder
        self.loading_label = QLabel("Initializing map...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            background-color: #2c3e50;
            color: white;
            font-size: 18px;
        """)
        layout.addWidget(self.loading_label)

        # Hide web view until loaded
        self.web_view.hide()
        layout.addWidget(self.web_view)

        # Connect signals
        self.web_view.loadFinished.connect(self.on_map_loaded)

        # Start local tile server
        self.tile_server = LocalTileServer(self.resource_dir, self.cache_dir)
        self.tile_server.server_started.connect(self.on_server_started)
        self.tile_server.start()
        
    def on_server_started(self, port):
        """Called when the local tile server is ready"""
        if not port:
            print("Error: Tile server did not start correctly.")
            return
        self.server_port = port
        self.init_map()

    def on_map_loaded(self, success):
        """Called when the map finishes loading"""
        if success:
            self.loading_label.hide()
            self.web_view.show()
            print("Map loaded successfully")
            
    # Revised init_map method for MapWidget
    def init_map(self):
        """Load the map with the proper base URL for resource resolution"""
        html_path = os.path.join(self.app_dir, 'resources', 'html', 'map.html')
        
        try:
            with open(html_path, 'r') as f:
                html_template = f.read()
                
            # Replace placeholders
            html = html_template.replace('INITIAL_LAT_PLACEHOLDER', str(self.initial_lat))
            html = html.replace('INITIAL_LON_PLACEHOLDER', str(self.initial_lon))
            html = html.replace('INITIAL_ZOOM_PLACEHOLDER', str(self.initial_zoom))
            html = html.replace('{{SERVER_PORT}}', str(self.server_port))
            
            # Create base URL for resource resolution
            base_url = QUrl(f"http://localhost:{self.server_port}/")
            
            # Load the HTML with base URL to properly resolve resources
            print("Loading map with placeholders replaced")
            self.web_view.setHtml(html, base_url)
            
        except Exception as e:
            print(f"Error loading HTML: {e}")
            return