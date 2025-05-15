import os
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import Qt, QFile, QIODevice
from tile_server import LocalTileServer
from area_manager import AreaManager, MapBridge

class MapWidget(QFrame):
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
        self.draw_mode_active = False
    
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
        """Enable or disable the drawing mode on the map"""
        print(f"MapWidget.toggle_draw_mode({enabled})")
        self.draw_mode_active = enabled
        
        # Apply visual feedback
        if enabled:
            self.setStyleSheet("border: 3px solid #27ae60;")
        else:
            self.setStyleSheet("")
        
        # Run debug utils
        self.web_view.page().runJavaScript("debugMapState()", 0, lambda result: print(f"Debug result: {result}"))
        
        # Toggle drawing mode
        if enabled:
            self.web_view.page().runJavaScript("forceDrawMode(true)", 0, lambda result: print(f"Draw mode result: {result}"))
        else:
            self.web_view.page().runJavaScript("forceDrawMode(false)", 0, lambda result: print(f"Draw mode result: {result}"))
        
        
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

    def add_area_to_map(self, area_id, bounds):
        """Add an area to the map"""
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
            window.drawnAreas["{area_id}"] = rect;
            
            return "Area added to map";
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