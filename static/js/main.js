// Main JavaScript file for the Mysterium Node Dashboard

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            if (alert && bootstrap && bootstrap.Alert) {
                var bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        });
    }, 5000);
    
    // Add node button event listener
    const addNodeButton = document.getElementById('addNodeButton');
    if (addNodeButton) {
        addNodeButton.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('addNodeModal'));
            modal.show();
        });
    }
    
    // Format timestamps
    const formatTimestamps = function() {
        const timestampElements = document.querySelectorAll('.format-timestamp');
        timestampElements.forEach(function(element) {
            const timestamp = element.getAttribute('data-timestamp');
            if (timestamp) {
                const date = new Date(timestamp);
                element.textContent = date.toLocaleString();
            }
        });
    };
    
    formatTimestamps();
});

// Add utility functions that are used across multiple templates
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    return `${hours}h ${minutes}m ${secs}s`;
}

function formatCurrency(value) {
    if (value >= 1000000000) {
        return '$' + (value / 1000000000).toFixed(2) + 'B';
    } else if (value >= 1000000) {
        return '$' + (value / 1000000).toFixed(2) + 'M';
    } else if (value >= 1000) {
        return '$' + (value / 1000).toFixed(2) + 'K';
    } else {
        return '$' + value.toFixed(2);
    }
}

function formatNumber(value) {
    return new Intl.NumberFormat().format(value);
}
