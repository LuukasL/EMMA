# area_manager.py
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QPointF, QRectF
import uuid
import json
import math


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
    
    def add_area(self, area=None, bounds=None):
        """
        Add a new area to the manager.
        
        Args:
            area (MissionArea, optional): Area object to add. If None, a new one is created.
            bounds (list, optional): If area is None, these bounds are used for the new area.
            
        Returns:
            str: ID of the new or added area
        """
        if area is None:
            area = MissionArea(bounds=bounds)
        
        # Add the area to our dictionary
        self.areas[area.id] = area
        
        # Emit signal to notify observers
        self.area_added.emit(area.id)
        
        return area.id
    
    def get_area(self, area_id):
        """Get an area by ID."""
        return self.areas.get(area_id)
    
    def get_all_areas(self):
        """Get all areas as a list."""
        return list(self.areas.values())
    
    def update_area(self, area_id, bounds=None, name=None, metadata=None):
        """Update an existing area's properties."""
        area = self.areas.get(area_id)
        if not area:
            return False
        
        if bounds:
            area.bounds = bounds
        
        if name:
            area.name = name
            
        if metadata:
            area.metadata.update(metadata)
        
        # Emit signal to notify observers
        self.area_modified.emit(area_id)
        
        return True
    
    def remove_area(self, area_id):
        """Remove an area by ID."""
        if area_id in self.areas:
            del self.areas[area_id]
            
            # If we removed the selected area, clear the selection
            if self.selected_area_id == area_id:
                self.selected_area_id = None
            
            # Emit signal to notify observers
            self.area_removed.emit(area_id)
            
            return True
        return False
    
    def select_area(self, area_id):
        """Select an area by ID."""
        if area_id in self.areas or area_id is None:
            self.selected_area_id = area_id
            self.area_selected.emit(area_id if area_id else "")
            return True
        return False
    
    def get_selected_area(self):
        """Get the currently selected area."""
        if self.selected_area_id:
            return self.areas.get(self.selected_area_id)
        return None
    
    def clear_all_areas(self):
        """Remove all areas."""
        area_ids = list(self.areas.keys())
        for area_id in area_ids:
            self.remove_area(area_id)
    
    def save_to_file(self, filename):
        """Save all areas to a JSON file."""
        data = {
            "areas": [area.to_dict() for area in self.areas.values()]
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving areas: {e}")
            return False
    
    def load_from_file(self, filename):
        """Load areas from a JSON file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Clear existing areas
            self.clear_all_areas()
            
            # Create areas from the loaded data
            for area_data in data.get("areas", []):
                area = MissionArea.from_dict(area_data)
                self.add_area(area)
                
            return True
        except Exception as e:
            print(f"Error loading areas: {e}")
            return False


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
    
    def __init__(self, area_manager, parent=None):
        """
        Initialize the map bridge.
        
        Args:
            area_manager (AreaManager): Reference to the application's area manager
            parent (QObject, optional): Parent object
        """
        super().__init__(parent)
        self.area_manager = area_manager
        
        # Connect to area manager signals
        self.area_manager.area_added.connect(self._on_area_added)
        self.area_manager.area_modified.connect(self._on_area_modified)
        self.area_manager.area_removed.connect(self._on_area_removed)
        self.area_manager.area_selected.connect(self._on_area_selected)
    
    @pyqtSlot(list)
    def addArea(self, bounds):
        """Add a new area with the given bounds. Called from JavaScript."""
        area_id = self.area_manager.add_area(bounds=bounds)
        return area_id
    
    @pyqtSlot(str, list)
    def updateArea(self, area_id, bounds):
        """Update an area's bounds. Called from JavaScript."""
        success = self.area_manager.update_area(area_id, bounds=bounds)
        return success
    
    @pyqtSlot(str)
    def removeArea(self, area_id):
        """Remove an area. Called from JavaScript."""
        success = self.area_manager.remove_area(area_id)
        return success
    
    @pyqtSlot(str)
    def selectArea(self, area_id):
        """Select an area. Called from JavaScript."""
        if area_id == "":
            area_id = None
        success = self.area_manager.select_area(area_id)
        return success
    
    @pyqtSlot(result='QVariantList')
    def getAllAreas(self):
        """Get all areas. Called from JavaScript."""
        areas = []
        for area in self.area_manager.get_all_areas():
            areas.append({
                "id": area.id,
                "bounds": area.bounds,
                "name": area.name
            })
        return areas
    
    @pyqtSlot(str)
    def debug(self, message):
        """Debug log from javaScript."""
        print(f"JS Debug: {message}")
    
    @pyqtSlot(result=str)
    def testConnection(self):
        """Test function to verify the bridge is working."""
        print("testConnection called from JavaScript")
        return "Bridge is working"
    
    
    def _on_area_added(self, area_id):
        """Handle area added event from the area manager."""
        area = self.area_manager.get_area(area_id)
        if area:
            self.areaAdded.emit(area_id, area.bounds)
    
    def _on_area_modified(self, area_id):
        """Handle area modified event from the area manager."""
        area = self.area_manager.get_area(area_id)
        if area:
            self.areaModified.emit(area_id, area.bounds)
    
    def _on_area_removed(self, area_id):
        """Handle area removed event from the area manager."""
        self.areaRemoved.emit(area_id)
    
    def _on_area_selected(self, area_id):
        """Handle area selected event from the area manager."""
        self.areaSelected.emit(area_id)
    
    @pyqtSlot(bool)
    def setDrawingMode(self, enabled):
        """Set the drawing mode. Called from Python, notifies JavaScript."""
        self.drawingModeChanged.emit(enabled)