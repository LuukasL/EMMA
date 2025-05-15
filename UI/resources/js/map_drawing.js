// Point drawing mode variables
let pointDrawModeActive = false;
let temporaryMarkers = [];

// Set drawing mode for points
function setPointDrawMode(enabled) {
    pointDrawModeActive = enabled;
    
    // Clear any existing temporary markers
    clearTemporaryMarkers();
    
    // Update cursor style
    if (enabled) {
        map.getContainer().style.cursor = 'crosshair';
    } else {
        map.getContainer().style.cursor = '';
    }
}

// Handle map click events
map.on('click', function(e) {
    if (pointDrawModeActive) {
        // Notify Python code of the click
        bridge.handleMapClick(e.latlng.lat, e.latlng.lng);
    }
});

// Add a temporary marker
function addTemporaryMarker(lat, lng, label) {
    var marker = L.marker([lat, lng], {
        icon: L.divIcon({
            className: 'map-point-marker',
            html: `<div>${label}</div>`,
            iconSize: [20, 20]
        })
    }).addTo(map);
    
    // Connect points with lines as they're added
    if (temporaryMarkers.length > 0) {
        var lastMarker = temporaryMarkers[temporaryMarkers.length - 1];
        var line = L.polyline([
            [lastMarker.getLatLng().lat, lastMarker.getLatLng().lng],
            [lat, lng]
        ], {
            color: '#3498db',
            weight: 2,
            dashArray: '5, 5',
            opacity: 0.7
        }).addTo(map);
        
        // Store line with markers
        temporaryMarkers.push(line);
    }
    
    temporaryMarkers.push(marker);
}

// Clear all temporary markers
function clearTemporaryMarkers() {
    temporaryMarkers.forEach(marker => {
        map.removeLayer(marker);
    });
    temporaryMarkers = [];
}

// Show drawing status indicator
function showDrawingStatus(message) {
    if (!window.statusOverlay) {
        window.statusOverlay = L.control({position: 'bottomleft'});
        
        window.statusOverlay.onAdd = function(map) {
            this._div = L.DomUtil.create('div', 'map-status-overlay');
            this._div.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
            this._div.style.color = 'white';
            this._div.style.padding = '10px';
            this._div.style.borderRadius = '4px';
            this._div.style.fontWeight = 'bold';
            this.update(message);
            return this._div;
        };
        
        window.statusOverlay.update = function(message) {
            this._div.innerHTML = message;
        };
        
        window.statusOverlay.addTo(map);
    } else {
        window.statusOverlay.update(message);
    }
}

// Hide drawing status indicator
function hideDrawingStatus() {
    if (window.statusOverlay) {
        map.removeControl(window.statusOverlay);
        window.statusOverlay = null;
    }
}