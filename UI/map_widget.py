import os
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QUrl, QTimer
from tile_server import LocalTileServer
from area_manager import AreaManager, MapBridge
import time


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
        self.all_clicks = []
        self.max_points = 4
        self.drawing_mode = False

        self.setup_click_detection()

        self.map_bridge.markerAdded.connect(self.on_marker_added)
        self.map_bridge.rectangleAdded.connect(self.on_rectangle_added)
        
        # Initialize storage
        self.markers = []
        self.polygons = []
        self.polylines = []

        
    def initialize_leaflet_draw(self):
        """Initialize Leaflet Draw with QWebChannel communication"""
        js_code = """
        // Initialize Leaflet Draw controls
        if (window.map) {
            // FeatureGroup to store editable layers
            window.drawnItems = new L.FeatureGroup();
            map.addLayer(window.drawnItems);
            
            // Initialize the draw control
            window.drawControl = new L.Control.Draw({
                edit: {
                    featureGroup: window.drawnItems
                },
                draw: {
                    polygon: {
                        allowIntersection: false,
                        showArea: true
                    },
                    rectangle: true,
                    marker: true,
                    polyline: true,
                    circle: false,
                    circlemarker: false
                }
            });
            map.addControl(window.drawControl);
            
            // Handle created items - use bridge to communicate with Python
            map.on(L.Draw.Event.CREATED, function(event) {
                var layer = event.layer;
                var type = event.layerType;
                
                // Add to feature group
                window.drawnItems.addLayer(layer);
                
                // Get geometry data based on type
                if (type === 'marker') {
                    var latlng = layer.getLatLng();
                    // Use bridge to call Python
                    if (window.bridge) {
                        window.bridge.handleMarkerAdded(latlng.lat, latlng.lng);
                    }
                } 
                else if (type === 'rectangle') {
                    var bounds = layer.getBounds();
                    var sw = bounds.getSouthWest();
                    var ne = bounds.getNorthEast();
                    // Use bridge to call Python
                    if (window.bridge) {
                        window.bridge.handleRectangleAdded(
                            sw.lat, sw.lng, 
                            ne.lat, ne.lng
                        );
                    }
                }
                else if (type === 'polygon') {
                    var coords = layer.getLatLngs()[0].map(function(latlng) {
                        return [latlng.lat, latlng.lng];
                    });
                    // Use bridge to call Python
                    if (window.bridge) {
                        window.bridge.handlePolygonAdded(JSON.stringify(coords));
                    }
                }
                else if (type === 'polyline') {
                    var coords = layer.getLatLngs().map(function(latlng) {
                        return [latlng.lat, latlng.lng];
                    });
                    // Use bridge to call Python
                    if (window.bridge) {
                        window.bridge.handlePolylineAdded(JSON.stringify(coords));
                    }
                }
            });
            
            // Handle deleted items
            map.on(L.Draw.Event.DELETED, function(event) {
                var layers = event.layers;
                if (window.bridge) {
                    window.bridge.handleLayersDeleted();
                }
            });
            
            console.log('Leaflet Draw initialized with QWebChannel');
        }
        """
        self.web_view.page().runJavaScript(js_code)

    def setup_click_detection(self):
        js_code = """
        // Set up click handling
        if (!window.droneClickHandler) {
            window.droneClickPoints = [];
            window.droneClickHandled = true;
            
            window.droneClickHandler = function(e) {
                window.droneClickPoints.push({
                    lat: e.latlng.lat,
                    lng: e.latlng.lng,
                    time: Date.now()
                });
                console.log("Click recorded at:", e.latlng.lat, e.latlng.lng);
            };
            
            // Add click handler to map when it's available
            if (window.map) {
                window.map.on('click', window.droneClickHandler);
                console.log("Click handler attached to map");
            } else {
                console.log("Map not yet available");
                // Use interval to wait for map to be available
                var mapCheckInterval = setInterval(function() {
                    if (window.map) {
                        window.map.on('click', window.droneClickHandler);
                        console.log("Click handler attached to map");
                        clearInterval(mapCheckInterval);
                    }
                }, 100);
            }
        }
        """
        
        self.click_timer = QTimer(self)
        self.click_timer.timeout.connect(self.check_for_clicks)
        self.click_timer.start(100)  # Check every 100ms
        self.web_view.loadFinished.connect(lambda: self.web_view.page().runJavaScript(js_code))

    def check_for_clicks(self):

        js_code = """
        var clicks = window.droneClickPoints || [];
        window.droneClickPoints = [];
        clicks;
        """
        self.web_view.page().runJavaScript(js_code, 0, self.process_clicks)

    def process_clicks(self, clicks):
        """Process clicks received from JavaScript"""
        if clicks and len(clicks) > 0:
            for click in clicks:
                lat = click.get('lat', 0)
                lng = click.get('lng', 0)
                
                # Store all clicks for reference
                self.all_clicks.append({
                    'lat': lat,
                    'lng': lng,
                    'timestamp': click.get('time', 0)
                })
                
                # Add a marker for this click (regardless of drawing mode)
                marker_id = f"click_{len(self.all_clicks)}"
                self.add_marker_to_map(lat, lng, marker_id)

                # Process the click for drawing mode
                self.handle_map_click(lat, lng)
                print(f"Processing click at {lat}, {lng}")

    def add_marker_to_map(self, lat, lng, marker_id):
        """Add a marker at the specified coordinates"""
        js_code = f"""
        (function() {{
            var marker = L.marker([{lat}, {lng}], {{
                icon: L.divIcon({{
                    className: 'map-marker',
                    html: '<div class="marker-dot"></div>',
                    iconSize: [10, 10]
                }})
            }}).addTo(map);
            
            // Store reference for later manipulation
            if (!window.mapMarkers) window.mapMarkers = {{}};
            window.mapMarkers['{marker_id}'] = marker;
        }})();
        """
        self.web_view.page().runJavaScript(js_code)


    
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


    def on_marker_added(self, lat, lng):
        """Handle marker added event"""
        self.markers.append({
            'lat': lat,
            'lng': lng,
            'time': time.time()  # Correctly using the imported module
        })
        # Handle UI updates, etc.
    
    def on_rectangle_added(self, sw_lat, sw_lng, ne_lat, ne_lng):
        """Handle rectangle added event"""
        rectangle = {
            'bounds': [
                [sw_lat, sw_lng],
                [ne_lat, ne_lng]
            ]
        }



    def init_map(self):
        """Initialize the map with local resources"""
        html_path = os.path.join(self.app_dir, 'resources', 'html', 'map.html')
        qwebchannel_path = os.path.join(self.app_dir, 'resources', 'js', 'qwebchannel.js')

        try:
            with open(html_path, 'r') as f:
                html_template = f.read()
                
            with open(qwebchannel_path, 'r') as f:
                qwebchannel_js = f.read()


            html_template = html_template.replace(
                '<script src=resources/js/qwebchannel.js></script>',
                f'<script>{qwebchannel_js}</script>' 
            )
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