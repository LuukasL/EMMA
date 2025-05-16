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
    
    
    def get_center(self):
        """Calculate and return the center point of the area."""
        sw, ne = self.bounds
        return [(sw[0] + ne[0]) / 2, (sw[1] + ne[1]) / 2]
    
    
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
    
    
class MapBridge(QObject):
    """
    Bridge between Python and JavaScript for map operations.
    
    This class is exposed to JavaScript via QWebChannel and provides
    methods for JavaScript to call and signals for JavaScript to listen to.
    """
    
    # Signal to control drawing mode
    drawingModeChanged = pyqtSignal(bool)  # is_enabled
    
    markerAdded = pyqtSignal(float, float)
    rectangleAdded = pyqtSignal(float, float, float, float)
    polygonAdded = pyqtSignal(str)
    polylineAdded = pyqtSignal(str)
    layersDeleted = pyqtSignal()
    def __init__(self, area_manager, map_widget):
        """
        Initialize the map bridge.
        """
        super().__init__()
        self.area_manager = area_manager
        self.map_widget = map_widget

    @pyqtSlot(float, float)
    def handleMarkerAdded(self, lat, lng):
        """Handle marker added event from Leaflet Draw"""
        print(f"Marker added at {lat}, {lng}")
        self.markerAdded.emit(lat, lng)
        
    @pyqtSlot(float, float, float, float)
    def handleRectangleAdded(self, sw_lat, sw_lng, ne_lat, ne_lng):
        """Handle rectangle added event from Leaflet Draw"""
        print(f"Rectangle added: SW({sw_lat}, {sw_lng}), NE({ne_lat}, {ne_lng})")
        bounds = [
            [sw_lat, sw_lng],  # Southwest corner
            [ne_lat, ne_lng]   # Northeast corner
        ]
        area_id = self.area_manager.add_area(bounds=bounds)
        self.rectangleAdded.emit(sw_lat, sw_lng, ne_lat, ne_lng)
        
    @pyqtSlot(str)
    def handlePolygonAdded(self, coords_json):
        """Handle polygon added event from Leaflet Draw"""
        import json
        coords = json.loads(coords_json)
        print(f"Polygon added with {len(coords)} vertices")
        self.polygonAdded.emit(coords_json)
        
    @pyqtSlot(str)
    def handlePolylineAdded(self, coords_json):
        """Handle polyline added event from Leaflet Draw"""
        import json
        coords = json.loads(coords_json)
        print(f"Polyline added with {len(coords)} vertices")
        self.polylineAdded.emit(coords_json)
        
    @pyqtSlot()
    def handleLayersDeleted(self):
        """Handle layers deleted event from Leaflet Draw"""
        print("Layers deleted")
        self.layersDeleted.emit()