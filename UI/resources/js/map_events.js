// Drawing event handlers
function onMouseDown(e) {
    console.log("Mouse down at:", e.latlng);
    if (!drawMode) return;
    
    drawStart = e.latlng;
    currentRectangle = L.rectangle([
        [drawStart.lat, drawStart.lng],
        [drawStart.lat, drawStart.lng]
    ], { 
        color: "#27ae60",
        weight: 3, 
        opacity: 0.8,
        fillColor: "#27ae60",
        fillOpacity: 0.2
    }).addTo(map);
}

function onMouseMove(e) {
    if (!drawMode || !drawStart || !currentRectangle) return;
    
    currentRectangle.setBounds([
        [drawStart.lat, drawStart.lng],
        [e.latlng.lat, e.latlng.lng]
    ]);
}

function onMouseUp(e) {
    console.log("Mouse up at:", e.latlng);
    if (!drawMode || !drawStart || !currentRectangle) return;
    
    // Get rectangle bounds
    var bounds = [
        [Math.min(drawStart.lat, e.latlng.lat), Math.min(drawStart.lng, e.latlng.lng)],
        [Math.max(drawStart.lat, e.latlng.lat), Math.max(drawStart.lng, e.latlng.lng)]
    ];
    
    // Only consider it a valid rectangle if it has some size
    var minSize = 0.0001;
    if (Math.abs(bounds[1][0] - bounds[0][0]) > minSize && 
        Math.abs(bounds[1][1] - bounds[0][1]) > minSize) {
        
        // Alert with special prefix to be caught by Python
        alert("PYACTION:addArea:" + JSON.stringify(bounds));
    }
    
    // Clean up
    map.removeLayer(currentRectangle);
    currentRectangle = null;
    drawStart = null;
}

// Make event handlers available globally
window.onMouseDown = onMouseDown;
window.onMouseMove = onMouseMove;
window.onMouseUp = onMouseUp;

console.log("Map events module loaded");