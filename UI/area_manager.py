# area_manager.py
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QPointF, QRectF
import uuid
import json
import math
import time

class MissionArea:
    """
    Represents a single rectangular area for drone missions.
    
    Stores coordinates and attributes of a mission area, and provides
    methods for manipulating and querying the area.
    """
    
    def __init__(self, id=None, bounds=None, name=None):
        """
        Initialize a new mission area.
        
        Args:
            id (str, optional): Unique identifier for this area. If None, a new UUID is generated.
            bounds (list, optional): Area bounds as [[south, west], [north, east]]. If None, creates empty bounds.
            name (str, optional): Human-readable name for this area. If None, a default name is generated.
        """
        # Assign a unique ID if none provided
        self.id = id if id else str(uuid.uuid4())
        
        # Initialize bounds as [[south, west], [north, east]]
        self.bounds = bounds if bounds else [[0, 0], [0, 0]]
        
        # Assign name or generate a default one
        self.name = name if name else f"Area {self.id[:5]}"
        
        # Additional attributes that might be useful
        self.created_at = None  # Could store timestamp
        self.modified_at = None  # Could store timestamp
        self.metadata = {}  # For any extra data (terrain info, etc.)
    
    def set_bounds(self, sw_lat, sw_lng, ne_lat, ne_lng):
        """Set the bounds of the area using individual coordinates."""
        self.bounds = [[sw_lat, sw_lng], [ne_lat, ne_lng]]
    
    def set_bounds_from_points(self, points):
        """Set the bounds from an array of points [[lat1, lng1], [lat2, lng2], ...]."""
        if not points or len(points) < 2:
            return False
            
        # Find the min/max coordinates to make a bounding rectangle
        lats = [p[0] for p in points]
        lngs = [p[1] for p in points]
        
        sw_lat = min(lats)
        sw_lng = min(lngs)
        ne_lat = max(lats)
        ne_lng = max(lngs)
        
        self.bounds = [[sw_lat, sw_lng], [ne_lat, ne_lng]]
        return True
    
    def get_center(self):
        """Calculate and return the center point of the area."""
        sw, ne = self.bounds
        return [(sw[0] + ne[0]) / 2, (sw[1] + ne[1]) / 2]
    
    def get_area_km2(self):
        """Calculate the approximate area in square kilometers."""
        sw, ne = self.bounds
        
        # Calculate width and height in degrees
        width_deg = abs(ne[1] - sw[1])
        height_deg = abs(ne[0] - sw[0])
        
        # Approximate conversion to kilometers (this is an approximation and varies by latitude)
        # More accurate calculations would use the haversine formula for each edge
        center_lat = (sw[0] + ne[0]) / 2
        km_per_deg_lat = 111.32  # km per degree latitude (roughly constant)
        km_per_deg_lng = 111.32 * math.cos(math.radians(center_lat))  # km per degree longitude (varies by latitude)
        
        width_km = width_deg * km_per_deg_lng
        height_km = height_deg * km_per_deg_lat
        
        return width_km * height_km
    
    def to_dict(self):
        """Convert the area to a dictionary for serialization."""
        return {
            "id": self.id,
            "bounds": self.bounds,
            "name": self.name,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a MissionArea instance from a dictionary."""
        area = cls(
            id=data.get("id"),
            bounds=data.get("bounds"),
            name=data.get("name")
        )
        area.metadata = data.get("metadata", {})
        return area


class AreaManager(QObject):
    """
    Manages all mission areas in the application.
    
    Acts as a central registry for areas and provides methods for 
    creating, modifying, and querying areas.
    """
    
    # Define signals for area changes
    area_added = pyqtSignal(str)  # Emits area ID when a new area is added
    area_modified = pyqtSignal(str)  # Emits area ID when an area is modified
    area_removed = pyqtSignal(str)  # Emits area ID when an area is removed
    area_selected = pyqtSignal(str)  # Emits area ID when an area is selected
    
    def __init__(self, parent=None):
        """Initialize the area manager."""
        super().__init__(parent)
        
        # Dictionary to store all areas, keyed by their ID
        self.areas = {}
        
        # Currently selected area ID, or None if no selection
        self.selected_area_id = None
    
    def add_area(self, bounds=None, name=None, area_type="patrol"):
        """Add a new area with the given bounds and properties"""
        area_id = f"area_{len(self.areas) + 1}_{int(time.time())}"
        
        if name is None:
            name = f"Area {len(self.areas) + 1}"
        
        Area = {
            "id": area_id,
            "name": name,
            "type": area_type,
            "bounds": bounds,
            "created": time.time(),
            "modified": time.time()
        }
        
        self.areas[area_id] = Area(area_id, name, bounds, area_type)
        self.area_added.emit(area_id)
        
        return area_id
    
    def save_to_file(self, file_path):
        """Save all areas to a JSON file"""
        try:
            # Prepare data for JSON serialization
            areas_data = {}
            for area_id, area in self.areas.items():
                areas_data[area_id] = {
                    "id": area.id,
                    "name": area.name,
                    "type": area.type,
                    "bounds": area.bounds,
                    "center": [
                        (area.bounds[0][0] + area.bounds[1][0]) / 2,
                        (area.bounds[0][1] + area.bounds[1][1]) / 2
                    ],
                    "dimensions": {
                        "width_km": self.calculate_width_km(area.bounds),
                        "height_km": self.calculate_height_km(area.bounds)
                    }
                }
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(areas_data, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving areas: {e}")
            return False


    def calculate_width_km(self, bounds):
        """Calculate width of bounds in kilometers"""
        from math import sin, cos, sqrt, atan2, radians
        
        # Use southwest and southeast corners
        lat1, lon1 = bounds[0][0], bounds[0][1]  # Southwest
        lat2, lon2 = bounds[0][0], bounds[1][1]  # Southeast
        
        # Approximate radius of earth in km
        R = 6371.0
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c
        return distance
    
    def calculate_height_km(self, bounds):
        """Calculate height of bounds in kilometers"""
        from math import sin, cos, sqrt, atan2, radians
        
        # Use southwest and northwest corners
        lat1, lon1 = bounds[0][0], bounds[0][1]  # Southwest
        lat2, lon2 = bounds[1][0], bounds[0][1]  # Northwest
        
        # Approximate radius of earth in km
        R = 6371.0
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c
        return distance
    
class MapBridge(QObject):
    """
    Bridge between Python and JavaScript for map operations.
    
    This class is exposed to JavaScript via QWebChannel and provides
    methods for JavaScript to call and signals for JavaScript to listen to.
    """
    
    # Signals to notify JavaScript of area changes
    areaAdded = pyqtSignal(str, list)  # area_id, bounds
    areaModified = pyqtSignal(str, list)  # area_id, bounds
    areaRemoved = pyqtSignal(str)  # area_id
    areaSelected = pyqtSignal(str)  # area_id
    
    # Signal to control drawing mode
    drawingModeChanged = pyqtSignal(bool)  # is_enabled
    
    def __init__(self, area_manager, map_widget):
        """
        Initialize the map bridge.
        """
        super().__init__()
        self.area_manager = area_manager
        self.map_widget = map_widget

    @pyqtSlot(float, float)
    def handleMapClick(self, lat, lon):
        """Handle map click event. Called from JavaScript."""
        if self.map_widget:
            self.map_widget.handle_map_click(lat, lon)

    @pyqtSlot(bool)
    def setDrawingMode(self, enabled):
        """Set the drawing mode. Called from Python, notifies JavaScript."""
        self.drawingModeChanged.emit(enabled)