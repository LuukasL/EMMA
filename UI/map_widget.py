import os
from PyQt6.QtWidgets import QVBoxLayout, QFrame
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, Qt

class MapWidget(QFrame):
    """Interactive OpenStreetMap widget using QWebEngineView"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create web view for the map
        self.web_view = QWebEngineView()
        self.web_view.setMinimumSize(800, 800)
        
        # Load the OpenStreetMap HTML
        self.init_map()
        
        # Add web view to layout
        layout.addWidget(self.web_view)
        
        # Ensure minimum size for the map
        self.setMinimumSize(800, 800)
    
    def init_map(self):
        """Initialize the map with OpenStreetMap"""
        # Tampere, Finland coordinates (approximately)
        initial_lat = 64.185717
        initial_lon = 27.704128
        initial_zoom = 13
        
        # Create simple HTML with Leaflet.js to display OpenStreetMap
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Drone Control Map</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <style>
                body {{ margin: 0; padding: 0; }}
                #map {{ width: 100%; height: 100vh; background: #2c3e50; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{initial_lat}, {initial_lon}], {initial_zoom});
                
                // Add Topographic Map tiles
                L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
                    maxZoom: 17,
                    attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a>'
                }}).addTo(map);
                
                // Add a scale control for distance reference
                L.control.scale({{
                    imperial: false,
                    position: 'bottomright'
                }}).addTo(map);
                
                // Add event listener for map interactions to be used later
                map.on('click', function(e) {{
                    console.log("Clicked at: " + e.latlng.lat + ", " + e.latlng.lng);
                }});
            </script>
        </body>
        </html>
        """
        # Load the HTML content
        self.web_view.setHtml(html)
    
    def center_map(self, lat, lon, zoom=13):
        """Center the map on specific coordinates"""
        self.web_view.page().runJavaScript(f"map.setView([{lat}, {lon}], {zoom});")