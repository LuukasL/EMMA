import os
import sys
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import QUrl, Qt, QTimer
from tile_server import LocalTileServer
import urllib.request
import urllib.error
import threading
import random

class MapWidget(QFrame):
    """Interactive OpenStreetMap widget using QWebEngineView with local resources"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        
        # Set up paths
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.resource_dir = os.path.join(self.app_dir, 'resources')
        self.cache_dir = os.path.join(self.app_dir, 'cache')
        
        # Create directories if they don't exist
        os.makedirs(self.resource_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create loading placeholder
        self.loading_label = QLabel("Initializing map...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            background-color: #2c3e50;
            color: white;
            font-size: 18px;
        """)
        layout.addWidget(self.loading_label)
        
        # Create web view for the map (hidden initially)
        self.web_view = QWebEngineView()
        self.web_view.setMinimumSize(800, 800)
        
        # Optimize web view performance
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        self.web_view.hide()  # Hide until loaded
        layout.addWidget(self.web_view)
        
        # Connect loaded signal
        self.web_view.loadFinished.connect(self.on_map_loaded)
        
        # Ensure minimum size for the map
        self.setMinimumSize(800, 800)
        
        # Start local tile server
        self.tile_server = LocalTileServer(self.resource_dir, self.cache_dir)
        self.tile_server.server_started.connect(self.on_server_started)
        self.tile_server.start()
        self.preload_initial_tiles()
        self.preload_area_tiles(lat=64.185717, lon=27.704128, zoom=14, radius=3)
    
    def on_server_started(self, port):
        """Called when the local tile server is ready"""
        self.server_port = port
        self.init_map()
    
    def on_map_loaded(self, success):
        """Called when the map finishes loading"""
        if success:
            self.loading_label.hide()
            self.web_view.show()
    
    def init_map(self):
        """Initialize the map with local resources"""
        # Updated coordinates in central Finland
        initial_lat = 64.185717
        initial_lon = 27.704128
        initial_zoom = 14
        
        # Create HTML with local resources
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
                // Initialize map with performance settings
                var map = L.map('map', {{
                    preferCanvas: true,
                    zoomControl: false,
                }}).setView([{initial_lat}, {initial_lon}], {initial_zoom});
                
                // Add topographic map tiles from local server
                L.tileLayer('http://localhost:{self.server_port}/tiles/topo/{{z}}/{{x}}/{{y}}.png', {{
                    maxZoom: 17,
                    attribution: 'Map data: © OpenStreetMap | Topo: OpenTopoMap',
                }}).addTo(map);
                
                // Add controls
                L.control.zoom({{position: 'topright'}}).addTo(map);
                L.control.scale({{imperial: false, position: 'bottomright'}}).addTo(map);
                
                // Add event listener for map interactions
                map.on('click', function(e) {{
                    console.log("Clicked at: " + e.latlng.lat + ", " + e.latlng.lng);
                }});
            </script>
        </body>
        </html>
        """
        
        # Load the HTML content
        self.web_view.setHtml(html, QUrl(f"http://localhost:{self.server_port}/"))
    
    def center_map(self, lat, lon, zoom=13):
        """Center the map on specific coordinates"""
        self.web_view.page().runJavaScript(f"map.setView([{lat}, {lon}], {zoom});")
    
    def closeEvent(self, event):
        """Clean up resources when widget is closed"""
        self.tile_server.stop()
        self.tile_server.wait()
        super().closeEvent(event)
    
        # Preload tiles for the initial view area
    def preload_initial_tiles(self):
        """Preload tiles for the initial view area"""
        # Central Finland coordinates
        lat = 64.185717
        lon = 27.704128
        
        # Preload zoom levels 10-14
        zoom_levels = range(10, 15)
        
        # Calculate tile coordinates and download them
        for zoom in zoom_levels:
            self.preload_area_tiles(lat, lon, zoom, radius=3)
        
    def preload_area_tiles(self, lat, lon, zoom, radius=2):
        """Preload tiles around a point"""
        # Convert lat/lon to tile coordinates
        import math
        n = 2.0 ** zoom
        xtile = int((lon + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.log(math.tan(math.radians(lat)) + 
                    1.0 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n)
        
        # Determine tile range to download
        for x in range(xtile - radius, xtile + radius + 1):
            for y in range(ytile - radius, ytile + radius + 1):
                # Create tile URL
                server = random.choice(['a', 'b', 'c'])
                url = f"https://{server}.tile.opentopomap.org/{zoom}/{x}/{y}.png"
                
                # Get tile path
                tile_path = os.path.join(
                    self.cache_dir, 'topo', str(zoom), str(x), f"{y}.png")
                
                # Create directory if needed
                os.makedirs(os.path.dirname(tile_path), exist_ok=True)
                
                # Check if tile exists, download if not
                if not os.path.exists(tile_path):
                    threading.Thread(
                        target=self.download_tile, 
                        args=(url, tile_path)
                    ).start()
        
    def download_tile(self, tile_url, tile_path):
        """Download a single tile from the remote server"""
        try:
            # Add a User-Agent to avoid being blocked
            headers = {
                'User-Agent': 'DroneControlApplication/1.0'
            }
            req = urllib.request.Request(url=tile_url, headers=headers)
            with urllib.request.urlopen(req) as response:
                tile_data = response.read()
                with open(tile_path, 'wb') as f:
                    f.write(tile_data)
                # Silent success - don't print anything
                return True
        except urllib.error.URLError as e:
            print(f"Error downloading tile: {e}")
            return False