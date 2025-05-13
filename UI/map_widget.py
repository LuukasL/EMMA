import os
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import Qt
from tile_server import LocalTileServer

class MapWidget(QFrame):
    """Interactive OpenStreetMap widget using QWebEngineView with local resources"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        # Initialize web view
        self.web_view = QWebEngineView()
        self.web_view.setMinimumSize(800, 800)

        # Set up paths
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.resource_dir = os.path.join(self.app_dir, 'resources')
        self.cache_dir = os.path.join(self.app_dir, 'cache')
        try:
            os.makedirs(self.resource_dir, exist_ok=True)
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError as e:
            print(f"Error creating directories: {e}")

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

        # Optimize web view performance
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)

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

    def init_map(self):
        """Initialize the map with local resources"""
        initial_lat = 64.185717
        initial_lon = 27.704128
        initial_zoom = 14
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Drone Control Map</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="http://localhost:{self.server_port}/leaflet/leaflet.css" />
            <script src="http://localhost:{self.server_port}/leaflet/leaflet.js"></script>
            <style>
                body {{ margin: 0; padding: 0; }}
                #map {{ width: 100%; height: 100vh; background: #2c3e50; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{initial_lat}, {initial_lon}], {initial_zoom});
                L.tileLayer('http://localhost:{self.server_port}/tiles/TOPO/{{z}}/{{x}}/{{y}}.png').addTo(map);
                
                // Add debug info
                map.on('tileerror', function(e) {{
                    console.error('Tile error:', e);
                }});
            </script>
        </body>
        </html>
        """
        self.web_view.setHtml(html)