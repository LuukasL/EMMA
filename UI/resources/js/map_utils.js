// Debugging utilities
function debugMapState() {
    console.log('Debug - Functions available:', Object.keys(window).filter(k => typeof window[k] === 'function'));
    console.log('Debug - setDrawMode exists:', typeof setDrawMode === 'function');
    console.log('Debug - map object exists:', typeof map === 'object');
    console.log('Debug - Current draw mode:', drawMode);
    
    if (typeof map !== 'undefined') {
        console.log('Debug - Map center:', map.getCenter());
        console.log('Debug - Map zoom:', map.getZoom());
        console.log('Debug - Map dragging enabled:', map.dragging.enabled());
    }
    
    return typeof setDrawMode === 'function';
}

// Area management
function createAreaRectangle(areaId, bounds) {
    var sw = bounds[0];
    var ne = bounds[1];
    
    var rectangle = L.rectangle(
        [
            [sw[0], sw[1]],
            [ne[0], ne[1]]
        ],
        {
            color: "#27ae60",
            weight: 3,
            opacity: 0.8,
            fillColor: "#27ae60",
            fillOpacity: 0.2
        }
    ).addTo(map);
    
    // Store in global areas object
    if (!window.drawnAreas) window.drawnAreas = {};
    window.drawnAreas[areaId] = rectangle;
    
    console.log("Created area rectangle:", areaId);
    return rectangle;
}

function removeAreaRectangle(areaId) {
    if (window.drawnAreas && window.drawnAreas[areaId]) {
        map.removeLayer(window.drawnAreas[areaId]);
        delete window.drawnAreas[areaId];
        console.log("Removed area rectangle:", areaId);
        return true;
    }
    return false;
}

// Make utils available globally
window.debugMapState = debugMapState;
window.createAreaRectangle = createAreaRectangle;
window.removeAreaRectangle = removeAreaRectangle;

console.log("Map utilities module loaded");