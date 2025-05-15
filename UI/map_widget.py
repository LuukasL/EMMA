import os
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from tile_server import LocalTileServer
from area_manager import AreaManager, MapBridge

class MapWidget(QFrame):
    pointAdded = pyqtSignal(int, float, float)
    rectangleCompleted = pyqtSignal(dict)

    """Interactive OpenStreetMap widget using QWebEngineView with local resources"""
    def __init__(self, parent=None, initial_lat=64.185717, initial_lon=27.704128, initial_zoom=15):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)


        # Store initial map position
        self.initial_lat = initial_lat
        self.initial_lon = initial_lon
        self.initial_zoom = initial_zoom

        # Create area manager
        self.area_manager = AreaManager(self)

        # Create a map Bridge for JavaScript communication
        self.map_bridge = MapBridge(self.area_manager, self)

        # Initialize web view
        self.web_view = QWebEngineView()
        self.web_view.setMinimumSize(800, 800)

        # Check functionality
        self.web_view.page().settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)

        # QWebChannel setup
        self.web_channel = QWebChannel()
        self.web_view.page().setWebChannel(self.web_channel)
        self.web_channel.registerObject("bridge", self.map_bridge)

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

        # Drawing mode initialization
        self.drawing_points = []
        self.max_points = 4
        self.drawing_mode = False
    
    def run_js(self, code):
        """Run Javascript code and print debug info"""
        print(f"Running JS: {code}")
        self.web_view.page().runJavaScript(code, 0, lambda result: print(f"JS result: {result if result is not None else 'None'}"))

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
            
            js_dir = os.path.join(self.app_dir,'resources', 'js')

            self.load_javascript(os.path.join(js_dir, 'map_utils.js'))
            self.load_javascript(os.path.join(js_dir, 'map_events.js'))
            self.load_javascript(os.path.join(js_dir, 'map_drawing.js'))

    def load_javascript(self, filepath):
        """Load a JavaScript file into the web view"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    js_code = f.read()
                
                self.web_view.page().runJavaScript(js_code)
                print(f"Loaded JavaScript file: {os.path.basename(filepath)}")
            else:
                print(f"JavaScript file not found: {filepath}")
        except Exception as e:
            print(f"Error loading JavaScript file {filepath}: {e}")
    def toggle_draw_mode(self, enabled):
        """Enable or disable four-point drawing mode"""
        self.drawing_mode = enabled
        
        # Apply visual feedback
        if enabled:
            self.setStyleSheet("border: 3px solid #27ae60;")
            # Clear any existing points
            self.drawing_points = []
            # Update status indicator
            self.run_js(f"showDrawingStatus('Click point 1 of {self.max_points}')")
        else:
            self.setStyleSheet("")
            # Clear status indicator
            self.run_js("hideDrawingStatus()")
            
        # Enable map click events in JavaScript
        self.run_js(f"setPointDrawMode({str(enabled).lower()})")
        
        # Update any selection visuals
        self.run_js("clearTemporaryMarkers()")
        
        
    def set_draw_mode_if_exists(self, function_exists, enabled):
        """Called after checking if setDrawMode exists"""
        if function_exists:
            print(f"setDrawMode function exists, calling with {enabled}")
            js_code = f"setDrawMode({str(enabled).lower()})"
            self.run_js(js_code)
        else:
            print("ERROR: setDrawMode function not defined in JavaScript.")
            self.run_js("console.log('Available functions: ', Object.keys(window))")

    def init_map(self):
        """Initialize the map with local resources"""
        html_path = os.path.join(self.app_dir, 'resources', 'html', 'map.html')
        
        try:
            with open(html_path, 'r') as f:
                html_template = f.read()
                
            # Replace placeholders
            html = html_template.replace('INITIAL_LAT_PLACEHOLDER', str(self.initial_lat))
            html = html.replace('INITIAL_LON_PLACEHOLDER', str(self.initial_lon))
            html = html.replace('INITIAL_ZOOM_PLACEHOLDER', str(self.initial_zoom))
            html = html.replace('{{SERVER_PORT}}', str(self.server_port))
            
            
            # Enable JS console output
            self.web_view.page().settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)

            # Connect to JS console for debugging
            self.web_view.page().javaScriptConsoleMessage = self.js_console_message
            
            # Connect to JS alerts for callback
            self.web_view.page().javaScriptAlert = self.js_alert
            
            # Load the HTML
            print("Loading html with placeholders replaced")
            self.web_view.setHtml(html)
            
        except Exception as e:
            print(f"Error loading HTML: {e}")
            return
        
    def js_console_message(self, level, message, line, source):
        """Handle JavaScript console messages"""
        print(f"JS [{level}] {message} (line {line})")
    def update_area_info(self):
        """Update information about the current areas"""
        # You can send a signal to update UI elements if needed
        print(f"Area info updated: {len(self.area_manager.areas)} areas")
        
        # Add drawing visual for each area
        for area_id, area in self.area_manager.areas.items():
            self.add_area_to_map(area_id, area.bounds)

    def handle_map_click(self, lat, lon):
        """Handle when user clicks on map in drawing mode"""
        if not self.drawing_mode:
            return
            
        # Add point to collection
        current_point = len(self.drawing_points) + 1
        self.drawing_points.append((lat, lon))
        
        # Emit signal about the new point
        self.pointAdded.emit(current_point, lat, lon)
        
        # Add temporary marker on the map
        self.run_js(f"addTemporaryMarker({lat}, {lon}, 'Point {current_point}')")
        
        # Check if we've collected all points
        if len(self.drawing_points) >= self.max_points:
            # Calculate the rectangle that encompasses all points
            rectangle = self.calculate_rectangle_from_points(self.drawing_points)
            
            # Create the rectangle on the map
            self.add_rectangle_to_map(rectangle)
            
            # Save to area manager
            area_id = self.area_manager.add_area(bounds=rectangle['bounds'])
            
            # Emit completion signal
            self.rectangleCompleted.emit(rectangle)
            
            # Exit drawing mode
            self.toggle_draw_mode(False)
        else:
            # Update status for next point
            next_point = current_point + 1
            self.run_js(f"showDrawingStatus('Click point {next_point} of {self.max_points}')")
    
    def calculate_rectangle_from_points(self, points):
        """Calculate a rectangle that encompasses all points"""
        # Find min/max coordinates
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        
        min_lat = min(lats)
        max_lat = max(lats)
        min_lon = min(lons)
        max_lon = max(lons)
        
        # Create bounds format expected by area manager
        bounds = [
            [min_lat, min_lon],  # Southwest corner
            [max_lat, max_lon]   # Northeast corner
        ]
        
        # Create rectangle data structure
        rectangle = {
            'type': 'rectangle',
            'bounds': bounds,
            'points': points,  # Original points for reference
            'center': [(min_lat + max_lat)/2, (min_lon + max_lon)/2],
            'dimensions': {
                'width_km': self.calculate_distance(min_lat, min_lon, min_lat, max_lon),
                'height_km': self.calculate_distance(min_lat, min_lon, max_lat, min_lon)
            }
        }
        
        return rectangle
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance in kilometers between two points"""
        from math import sin, cos, sqrt, atan2, radians
        
        # Approximate radius of earth in km
        R = 6371.0
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c
        return distance
        
    def add_rectangle_to_map(self, rectangle):
        """Add a rectangle to the map"""
        bounds = rectangle['bounds']
        js_code = f"""
        (function() {{
            var bounds = {bounds};
            var sw = bounds[0];
            var ne = bounds[1];
            
            // Create rectangle
            var rect = L.rectangle(
                [
                    [sw[0], sw[1]],
                    [ne[0], ne[1]]
                ],
                {{
                    color: "#27ae60",
                    weight: 3,
                    opacity: 0.8,
                    fillColor: "#27ae60",
                    fillOpacity: 0.2
                }}
            ).addTo(map);
            
            // Store reference
            if (!window.drawnAreas) window.drawnAreas = {{}};
            var areaId = "area_" + Date.now();
            window.drawnAreas[areaId] = rect;
            
            // Center map on rectangle
            map.fitBounds([
                [sw[0], sw[1]],
                [ne[0], ne[1]]
            ]);
            
            return areaId;
        }})();
        """
        self.web_view.page().runJavaScript(js_code)



    def js_alert(self, url, msg):
        """Handle JavaScript alerts - used for callbacks from JS to Python"""
        print(f"JS Alert: {msg}")
        
        if msg.startswith('PYACTION:'):
            # Parse action command
            cmd = msg[9:].strip()
            if cmd.startswith('addArea:'):
                import json
                bounds_str = cmd[8:].strip()
                try:
                    bounds = json.loads(bounds_str)
                    area_id = self.area_manager.add_area(bounds=bounds)
                    print(f"Added area with ID: {area_id}")
                    # Update display
                    self.update_area_info()
                except Exception as e:
                    print(f"Error adding area: {e}")