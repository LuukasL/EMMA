// Drawing state variables
var drawMode = false;
var drawStart = null;
var currentRectangle = null;

// Main function to toggle drawing mode
function setDrawMode(enabled) {
    console.log("setDrawMode called with:", enabled);
    drawMode = enabled;
    
    var mapDiv = document.getElementById('map');
    if (enabled) {
        console.log("Enabling draw mode");
        mapDiv.classList.add('draw-mode-active');
        
        // Disable map dragging when in draw mode
        map.dragging.disable();
        
        // Add event listeners for drawing
        map.on('mousedown', onMouseDown);
        map.on('mousemove', onMouseMove);
        map.on('mouseup', onMouseUp);
    } else {
        console.log("Disabling draw mode");
        mapDiv.classList.remove('draw-mode-active');
        
        // Re-enable map dragging
        map.dragging.enable();
        
        // Remove event listeners
        map.off('mousedown', onMouseDown);
        map.off('mousemove', onMouseMove);
        map.off('mouseup', onMouseUp);
        
        // Clean up any in-progress drawing
        if (currentRectangle) {
            map.removeLayer(currentRectangle);
            currentRectangle = null;
        }
    }
}

// Force drawing mode
function forceDrawMode(enabled) {
    if (enabled) {
        // Force draw mode directly
        drawMode = true;
        var mapDiv = document.getElementById('map');
        mapDiv.classList.add('draw-mode-active');
        
        // Disable map dragging
        if (typeof map !== 'undefined' && map.dragging) {
            console.log('Disabling map dragging');
            map.dragging.disable();
        }
        
        // Connect events directly
        if (typeof map !== 'undefined') {
            console.log('Adding mouse event listeners');
            map.on('mousedown', function(e) { 
                console.log('Mouse down event:', e.latlng);
                if (typeof onMouseDown === 'function') {
                    onMouseDown(e);
                }
            });
            map.on('mousemove', function(e) {
                if (typeof onMouseMove === 'function') {
                    onMouseMove(e);
                }
            });
            map.on('mouseup', function(e) {
                console.log('Mouse up event:', e.latlng);
                if (typeof onMouseUp === 'function') {
                    onMouseUp(e);
                }
            });
        }
    } else {
        drawMode = false;
        var mapDiv = document.getElementById('map');
        mapDiv.classList.remove('draw-mode-active');
        
        // Re-enable map dragging
        if (typeof map !== 'undefined' && map.dragging) {
            console.log('Re-enabling map dragging');
            map.dragging.enable();
        }
        
        // Remove event listeners
        if (typeof map !== 'undefined') {
            console.log('Removing mouse event listeners');
            map.off('mousedown');
            map.off('mousemove');
            map.off('mouseup');
        }
    }
}

// Make the functions available globally
window.setDrawMode = setDrawMode;
window.forceDrawMode = forceDrawMode;

console.log("Map drawing module loaded");