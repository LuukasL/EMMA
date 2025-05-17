# Purpose: The main map display component using QGraphicsView
# Classes:
# - MapView: A QGraphicsView subclass for displaying and interacting with the map.
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtCore import pyqtSignal, Qt, QRectF, QPointF
from PyQt6.QtGui import QBrush, QColor, QPixmap, QPen
import os
import math

class MapView(QGraphicsView):
    """
    Pure PyQt implementation of an interactive map view.
    
    This class handles displaying map tiles, user interaction for
    panning and zooming, and provides the foundation for area selection
    and other map-based features.
    """

    mapClicked = pyqtSignal(float, float) # Emits coordinates of the clicked point
    mapMoved = pyqtSignal(float, float) # Emits coordinates of the new centerpoint after panning
    zoomChanged = pyqtSignal(int) # Emits the new zoom level after zooming

    def __init__(self, parent=None, cache_dir=None, initial_lat=64.185717, initial_lon=27.704128, initial_zoom=15):
        """
        Initialize the map view with default settings.
        Args:
            parent: Parent widget
            cache_dir: Directory containing cached map tiles
            initial_lat: Initial center latitude
            initial_lon: Initial center longitude
            initial_zoom: Initial zoom level (higher = more detail)
        """
        super().__init__(parent)

        # Map state
        self.latitude = initial_lat
        self.longitude = initial_lon
        self.zoom = initial_zoom
        self.tile_size = 256  

        # Set up cache directory for map tile images
        self.app_dir = os.path.dirname(os.path.abspath(__file__))   
        if cache_dir is None:
            self.cache_dir = os.path.join(os.path.dirname(self.app_dir), 'cache')
        else:
            self.cache_dir = cache_dir

        self.loaded_tiles = {}  # Dictionary to store loaded tiles

        self.panning = False  # Flag to indicate if the map is being panned
        self.last_pan_point = None  # Last position of the mouse during panning


        # Set up the QGraphicsView
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Configure view
        self.setRenderHint(self.renderHints().Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)

         # Set background color
        self.setBackgroundBrush(QBrush(QColor('#2c3e50')))
        
        # Enable mouse tracking
        self.setMouseTracking(True)

        # Debugging: Check cache structure
        self.find_any_tile()
        
        # Initial update
        self.init_map()
        print(f"MapView initialized with cache directory: {self.cache_dir}")
        print(f"Initial position: {initial_lat}, {initial_lon}, zoom: {initial_zoom}")

    def find_any_tile(self):
        """Find any valid tile to test rendering"""
        print("\n==== LOOKING FOR SAMPLE TILE ====")
        tile_source = "topo"
        
        # Try different zoom levels
        for zoom in range(10, 19):
            zoom_dir = os.path.join(self.cache_dir, tile_source, str(zoom))
            if not os.path.exists(zoom_dir):
                continue
                
            print(f"Looking in zoom level {zoom}")
            
            # Check folders
            try:
                folders = [d for d in os.listdir(zoom_dir) if os.path.isdir(os.path.join(zoom_dir, d))]
                
                if not folders:
                    continue
                    
                print(f"Found {len(folders)} folders")
                
                # Check first folder for tiles
                folder = folders[0]
                folder_path = os.path.join(zoom_dir, folder)
                
                files = [f for f in os.listdir(folder_path) if f.endswith('.png')]
                
                if not files:
                    continue
                    
                print(f"Found {len(files)} tiles in folder {folder}")
                
                # Get the first tile
                sample_file = files[0]
                sample_path = os.path.join(folder_path, sample_file)
                
                print(f"Sample tile: {sample_path}")
                
                # Display information about this tile
                folder_num = int(folder)
                file_num = int(os.path.splitext(sample_file)[0])
                
                print(f"Folder number: {folder_num}, File number: {file_num}")
                
                # Calculate possible coordinates
                possible_x = folder_num * 1024 + (file_num % 1024)
                possible_y = file_num // 1024
                
                print(f"Possible coordinates: x={possible_x}, y={possible_y}")
                print(f"Will try to use these for tile lookup")
                
                # Store these as test coordinates
                self.test_tile_info = {
                    'zoom': zoom,
                    'x': possible_x,
                    'y': possible_y,
                    'path': sample_path
                }
                
                # Add a test tile to verify rendering works
                test_pixmap = QPixmap(sample_path)
                test_item = QGraphicsPixmapItem(test_pixmap)
                test_item.setPos(0, 0)
                self.scene.addItem(test_item)
                print("Added test tile to scene")
                
                return True
            except Exception as e:
                print(f"Error finding sample tile: {e}")
        
        print("Could not find any sample tiles")
        return False
    



    def init_map(self):
        """
        Initialize the map by loading the initial tiles.
        """
        # Clear any existing items
        self.scene.clear()
        self.loaded_tiles = {}
        # Get the world pixel coordinates of the center
        world_x, world_y = self.geo_to_world_pixel(self.latitude, self.longitude)
        
        # Position the view to center on initial coordinates
        self.centerOn(world_x, world_y)
        
        # Add a temporary marker at the center
        center_marker = self.scene.addRect(world_x-5, world_y-5, 10, 10, 
                                          QPen(QColor('red')), QBrush(QColor('red')))
        
        print(f"Added center marker at {world_x}, {world_y}")
        
        # Try to use the test tile coordinates from earlier
        if hasattr(self, 'test_tile_info'):
            # Switch to the zoom level where we found a tile
            self.zoom = self.test_tile_info['zoom']
            print(f"Using zoom level {self.zoom} where we found a sample tile")
        
        # Load visible tiles
        self.update_visible_tiles()

    def update_visible_tiles(self):
        """Load and display tiles that are currently visible in the viewport"""
        print(f"\n==== UPDATING TILES FOR ZOOM {self.zoom} ====")
        
        # Get current view bounds in scene coordinates
        view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        
        print(f"View rect: {view_rect}")
        
        # Calculate the tile coordinates that cover this view
        min_tile_x, min_tile_y = self.world_pixel_to_tile(view_rect.left(), view_rect.top())
        max_tile_x, max_tile_y = self.world_pixel_to_tile(view_rect.right(), view_rect.bottom())
        
        # Limit to valid tile ranges for the current zoom
        max_tile = 2**self.zoom - 1
        min_tile_x = max(0, min_tile_x)
        min_tile_y = max(0, min_tile_y)
        max_tile_x = min(max_tile, max_tile_x)
        max_tile_y = min(max_tile, max_tile_y)
        
        print(f"Tile range: x={min_tile_x}-{max_tile_x}, y={min_tile_y}-{max_tile_y}")
        
        # Keep track of tiles we need to keep
        needed_tiles = set()
        
        # Try loading the test tile first
        if hasattr(self, 'test_tile_info'):
            try:
                test_x = self.test_tile_info['x']
                test_y = self.test_tile_info['y']
                test_path = self.test_tile_info['path']
                
                print(f"Loading test tile: x={test_x}, y={test_y}")
                
                pixmap = QPixmap(test_path)
                if not pixmap.isNull():
                    # Create a new tile item
                    tile_item = QGraphicsPixmapItem(pixmap)
                    
                    # Position it at the center for visibility
                    world_x, world_y = self.geo_to_world_pixel(self.latitude, self.longitude)
                    tile_item.setPos(world_x, world_y)
                    
                    # Add to scene
                    self.scene.addItem(tile_item)
                    print(f"Added test tile at center position")
            except Exception as e:
                print(f"Error loading test tile: {e}")
        
        # For now, focus on getting ANY tile to display
        print("\n==== MAP VIEW INITIALIZED ====")
    

    def get_tile_path(self, zoom, x, y, tile_source='TOPO'):
        """
        Get the file path for a cached tile using the observed cache structure.
        
        The structure appears to be:
        /cache/topo/{zoom}/{folder_number}/{file_number}.png
        
        Where:
        - zoom is the zoom level
        - folder_number and file_number need to be determined
        """
        return None
        
        

    def geo_to_world_pixel(self, lat, lon):
        """
        Convert geographical coordinates to world pixel coordinates.
        Args:
            lat: Latitude
            lon: Longitude
        Returns:
            Pixel coordinates (x, y)
        """

        n = 2.0 ** self.zoom
        x = (lon + 180.0) / 360.0 * n * self.tile_size
        lat_rad = math.radians(lat)
        y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n * self.tile_size
        return x, y

    def world_pixel_to_geo(self, pixel_x, pixel_y):
        """
        Convert world pixel coordinates to geographical coordinates.
        Args:
            x: Pixel x-coordinate
            y: Pixel y-coordinate
        Returns:
            Geographical coordinates (lat, lon)
        """
        n = 2.0 ** self.zoom
        lon_deg = pixel_x / self.tile_size / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * pixel_y / self.tile_size / n)))
        lat_deg = math.degrees(lat_rad)

        return lat_deg, lon_deg

    def world_pixel_to_tile(self, pixel_x, pixel_y):
        """
        Convert world pixel coordinates to tile coordinates.
        Args:
            x: Pixel x-coordinate
            y: Pixel y-coordinate
        Returns:
            Tile coordinates (z, x, y)
        """
        tile_x = int(pixel_x / self.tile_size)
        tile_y = int(pixel_y / self.tile_size)
        return tile_x, tile_y

    def tile_to_world_pixel(self, tile_x, tile_y):
        """
        Convert tile coordinates to world pixel coordinates.
        Args:
            z: Zoom level
            x: Tile x-coordinate
            y: Tile y-coordinate
        Returns:
            Pixel coordinates (x, y)
        """
        pixel_x = tile_x * self.tile_size
        pixel_y = tile_y * self.tile_size
        return pixel_x, pixel_y

    def mousePressEvent(self, event):
        """handle mouse press event"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Start panning or handle click
            self.panning = True
            self.last_pan_point = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            
            # Store the press position for potential click event
            self.press_pos = event.position()
        
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """handle mouse release event"""
        if event.button() == Qt.MouseButton.LeftButton:
            # End panning
            self.panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            
            # Check if this is a click (not a drag)
            if hasattr(self, 'press_pos'):
                # Calculate the distance moved to determine if it's a click
                distance = (event.position() - self.press_pos).manhattanLength()
                if distance < 5:  # Threshold for considering it a click
                    # Convert screen position to scene position
                    scene_pos = self.mapToScene(event.position().toPoint())
                    
                    # Convert scene position to geographic coordinates
                    lat, lon = self.world_pixel_to_geo(scene_pos.x(), scene_pos.y())
                    
                    # Emit the click signal
                    self.mapClicked.emit(lat, lon)
        
        super().mouseReleaseEvent(event)
    
    def mouseMoveEvent(self, event):
        """handle mouse move event"""
        if self.panning and self.last_pan_point:
            # Calculate the movement delta
            delta = event.position() - self.last_pan_point
            self.last_pan_point = event.position()
            
            # Pan the view
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            
            # Update visible tiles after significant movement
            if abs(delta.x()) > 10 or abs(delta.y()) > 10:
                self.update_visible_tiles()
                
                # Update center coordinates and emit signal
                center = self.mapToScene(self.viewport().rect().center())
                self.latitude, self.longitude = self.world_pixel_to_geo(center.x(), center.y())
                self.mapMoved.emit(self.latitude, self.longitude)
        
        super().mouseMoveEvent(event)
    def wheelEvent(self, event):
        """handle mouse wheel event"""
        # Get current center and cursor position before zoom
        old_center = self.mapToScene(self.viewport().rect().center())
        old_pos = self.mapToScene(event.position().toPoint())
        
        # Calculate zoom direction
        delta = event.angleDelta().y()
        zoom_in = delta > 0
        
        # Change zoom level
        old_zoom = self.zoom
        if zoom_in and self.zoom < 18:  # Max zoom level
            self.zoom += 1
        elif not zoom_in and self.zoom > 1:  # Min zoom level
            self.zoom -= 1
        
        # If zoom level changed
        if old_zoom != self.zoom:
            # Remember the geographic coordinates under cursor
            mouse_geo_lat, mouse_geo_lon = self.world_pixel_to_geo(old_pos.x(), old_pos.y())
            
            # Reset the map for new zoom level
            self.init_map()
            
            # Convert back to new world pixel coordinates
            new_mouse_pixel_x, new_mouse_pixel_y = self.geo_to_world_pixel(mouse_geo_lat, mouse_geo_lon)
            
            # Adjust view to keep the same point under cursor
            cursor_viewport_pos = event.position().toPoint()
            new_center_x = new_mouse_pixel_x - (cursor_viewport_pos.x() - self.viewport().width() / 2)
            new_center_y = new_mouse_pixel_y - (cursor_viewport_pos.y() - self.viewport().height() / 2)
            
            # Center on the calculated position
            self.centerOn(new_center_x, new_center_y)
            
            # Update visible tiles for new zoom level
            self.update_visible_tiles()
            
            # Emit zoom changed signal
            self.zoomChanged.emit(self.zoom)
        
        # Consume the event
        event.accept()

    def resizeEvent(self, event):
        """handle resize event"""
        super().resizeEvent(event)
        # Update the visible tiles when the view size changes
        self.update_visible_tiles()

    def debug_cache_structure(self):
        """Scan the cache and try to understand its structure"""
        print(f"Analyzing cache structure in: {self.cache_dir}")
        
        # Try to find zoom level directories
        try:
            topo_dir = os.path.join(self.cache_dir, "topo")
            zoom_levels = [d for d in os.listdir(topo_dir) 
                        if os.path.isdir(os.path.join(topo_dir, d))]
            
            print(f"Found zoom levels: {zoom_levels}")
            
            # Check one zoom level in detail
            if zoom_levels:
                zoom = zoom_levels[0]
                zoom_dir = os.path.join(topo_dir, zoom)
                
                folders = [d for d in os.listdir(zoom_dir) 
                        if os.path.isdir(os.path.join(zoom_dir, d))]
                
                print(f"Folders in zoom {zoom}: {folders[:5]}... ({len(folders)} total)")
                
                # Check files in one folder
                if folders:
                    folder = folders[0]
                    folder_dir = os.path.join(zoom_dir, folder)
                    
                    files = [f for f in os.listdir(folder_dir) 
                            if f.endswith('.png')]
                    
                    print(f"Files in folder {folder}: {files[:5]}... ({len(files)} total)")
                    
                    # Try to understand the pattern
                    if files:
                        print("Analyzing file naming pattern...")
                        for file in files[:5]:
                            file_name = os.path.splitext(file)[0]
                            file_num = int(file_name)
                            print(f"  File: {file_name} -> Possible coordinates:")
                            
                            # Try to reverse-engineer coordinates
                            # For OpenStreetMap style:
                            for x_offset in range(1024):
                                y_estimate = (file_num - x_offset) // 1024
                                x_estimate = x_offset + (int(folder) * 1024)
                                if (y_estimate >= 0 and 
                                    ((y_estimate % 1024) * 1024) + (x_estimate % 1024) == file_num):
                                    print(f"    x={x_estimate}, y={y_estimate}")
                                    break
            
        except Exception as e:
            print(f"Error analyzing cache: {e}")


    def debug_center_tile(self):
        """Debug tile loading for the center coordinates"""
        print("\n==== DEBUGGING CENTER TILE ====")
        center_x, center_y = self.geo_to_world_pixel(self.latitude, self.longitude)
        tile_x, tile_y = self.world_pixel_to_tile(center_x, center_y)
        
        print(f"Center coordinates: lat={self.latitude}, lon={self.longitude}")
        print(f"World pixels: x={center_x}, y={center_y}")
        print(f"Tile coordinates: x={tile_x}, y={tile_y}")
        
        # Test finding this tile
        tile_path = self.get_tile_path(self.zoom, tile_x, tile_y)
        if tile_path and os.path.exists(tile_path):
            print(f"SUCCESS: Found center tile at {tile_path}")
        else:
            print(f"FAILURE: Could not find center tile!")
        
        print("==== END CENTER TILE DEBUG ====\n")