// Updated visualizer.js
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the visualization
    initializeVisualization();
    
    // Set up periodic refresh
    setInterval(refreshVisualization, 2000);
});

// Task types we want to visualize - Updated to include FINAL instead of FORDING
const taskTypes = ['CASE', 'BOX', 'COVER', 'FINAL'];

// Log level types for styling
const logLevels = {
    INFO: 'info',
    WARNING: 'warning',
    ERROR: 'error'
};

// Initialize the visualization panels
function initializeVisualization() {
    console.log('Initializing visualization...');
    addLogEntry('System initialized', logLevels.INFO);
    addLogEntry('Connecting to data sources...', logLevels.INFO);
    refreshVisualization();
}

// Refresh the visualization with the latest data
function refreshVisualization() {
    fetch('/api/last_files')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            updateCameraFeeds(data);
            updateResultsPanel(data);
            addLogEntry('Visualization refreshed', logLevels.INFO);
        })
        .catch(error => {
            console.error('Error fetching visualization data:', error);
            addLogEntry('Failed to fetch data: ' + error.message, logLevels.ERROR);
            fallbackSimulation();
        });
    
    // Also fetch latest task statuses
    fetch('/api/task_statuses')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            updateTaskStatuses(data);
        })
        .catch(error => {
            console.error('Error fetching task statuses:', error);
            addLogEntry('Failed to fetch task statuses: ' + error.message, logLevels.ERROR);
            simulateTaskStatuses();
        });
    
    // Fetch system logs if available
    fetch('/api/system_logs')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(logs => {
            updateSystemLogs(logs);
        })
        .catch(error => {
            console.error('Error fetching system logs:', error);
            // Don't show an error message for this as it's not critical
        });
}

// Update all camera feeds with the provided data
function updateCameraFeeds(data) {
    for (const taskType of taskTypes) {
        updateCameraFeed(taskType.toLowerCase(), data[taskType]);
    }
}

// Update a single camera feed with the provided data
function updateCameraFeed(taskId, fileData) {
    const panel = document.getElementById(`${taskId}-panel`);
    if (!panel) return;
    
    const cameraFeed = panel.querySelector('.camera-feed');
    
    // Clear existing content
    cameraFeed.innerHTML = '';
    
    if (!fileData || !fileData.path) {
        cameraFeed.innerHTML = '<div class="media-placeholder">No data available</div>';
        return;
    }
    
    // Add the timestamp display
    const timestamp = document.createElement('div');
    timestamp.className = 'timestamp';
    timestamp.textContent = fileData.timestamp || 'Unknown time';
    
    // Create the media element based on the file extension
    const filePath = fileData.path;
    const fileName = filePath.split('/').pop();
    const fileExtension = fileName.split('.').pop().toLowerCase();
    
    // Always prioritize displaying as image, even for video files
    // For video files, this will effectively show the last frame
    const img = document.createElement('img');
    img.src = `/media/${fileName}`;
    img.alt = `${taskId} task result`;
    img.onerror = function() {
        // If image loading fails (possibly because it's actually a video), 
        // fall back to video element for backward compatibility
        if (['mp4', 'avi', 'webm'].includes(fileExtension)) {
            const video = document.createElement('video');
            video.src = `/media/${fileName}`;
            video.controls = true;
            video.loop = true;
            video.muted = true;
            video.autoplay = true;
            cameraFeed.innerHTML = '';
            cameraFeed.appendChild(video);
            cameraFeed.appendChild(timestamp);
            addLogEntry(`Loaded video for ${taskId}: ${fileName}`, logLevels.INFO);
        } else {
            cameraFeed.innerHTML = '<div class="media-placeholder">Failed to load media</div>';
            addLogEntry(`Failed to load media for ${taskId}: ${fileName}`, logLevels.WARNING);
        }
    };
    
    cameraFeed.appendChild(img);
    
    // Add the timestamp to the camera feed
    cameraFeed.appendChild(timestamp);
    addLogEntry(`Loaded image for ${taskId}: ${fileName}`, logLevels.INFO);
}

// Update the results panel with the provided data
function updateResultsPanel(data) {
    if (data.CASE) updateCaseResults(data.CASE);
    if (data.BOX) updateBoxResults(data.BOX);
    if (data.COVER) updateCoverResults(data.COVER);
    if (data.FINAL) updateFinalResults(data.FINAL);

    // Log significant events
    Object.entries(data).forEach(([taskType, taskData]) => {
        if (taskData?.status === 'ERROR') {
            addLogEntry(`${taskType} task reported an error: ${taskData.details}`, logLevels.ERROR);
        } else if (taskData?.status === 'OK') {
            addLogEntry(`${taskType} task completed successfully`, logLevels.INFO);
        }
    });
}

// Add specific update functions for each camera type
function updateCaseResults(data) {
    const resultPanel = document.getElementById('case-result');
    if (!resultPanel || !data) return;

    resultPanel.querySelector('.result-value').textContent = data.status || '-';
    resultPanel.querySelector('.confidence-value').textContent = `${data.confidence || 0}%`;
    resultPanel.querySelector('.details-value').textContent = data.details || '-';
}

function updateBoxResults(data) {
    const resultPanel = document.getElementById('box-result');
    if (!resultPanel || !data) return;

    resultPanel.querySelector('.result-value').textContent = data.status || '-';
    const dimensionsElement = document.getElementById('box-dimensions');
    if (dimensionsElement) dimensionsElement.textContent = data.dimensions || '-';
    const integrityElement = document.getElementById('box-integrity');
    if (integrityElement) integrityElement.textContent = data.integrity || '-';
    const qualityElement = document.getElementById('box-quality');
    if (qualityElement) qualityElement.textContent = data.quality || '-';
}

function updateCoverResults(data) {
    const resultPanel = document.getElementById('cover-result');
    if (!resultPanel || !data) return;

    resultPanel.querySelector('.result-value').textContent = data.status || '-';
    const alignmentElement = document.getElementById('cover-alignment');
    if (alignmentElement) alignmentElement.textContent = data.alignment || '-';
    const sealQualityElement = document.getElementById('seal-quality');
    if (sealQualityElement) sealQualityElement.textContent = data.sealQuality || '-';
    const surfaceCheckElement = document.getElementById('surface-check');
    if (surfaceCheckElement) surfaceCheckElement.textContent = data.surfaceCheck || '-';
    const edgeDetectionElement = document.getElementById('edge-detection');
    if (edgeDetectionElement) edgeDetectionElement.textContent = data.edgeDetection || '-';
}

function updateFinalResults(data) {
    const resultPanel = document.getElementById('final-result');
    if (!resultPanel || !data) return;

    // Update basic result information
    const resultValueElement = resultPanel.querySelector('.result-value');
    if (resultValueElement) {
        resultValueElement.textContent = data.status || '-';
        // Add appropriate class based on status
        resultValueElement.className = `result-value ${data.status}`;
    }
    
    const confidenceValue = resultPanel.querySelector('.confidence-value');
    if (confidenceValue) {
        confidenceValue.textContent = data.confidence || '-';
    }
    
    const detailsValue = resultPanel.querySelector('.details-value');
    if (detailsValue) {
        detailsValue.textContent = data.details || '-';
    }

    // Add a log entry for the final result
    if (data.status === 'OK') {
        addLogEntry('Final check completed successfully', logLevels.INFO);
    } else if (data.status === 'NG') {
        addLogEntry('Final check reported issues', logLevels.WARNING);
    }
}

// Update task statuses based on API data
function updateTaskStatuses(statusData) {
    const statusBadges = {
        'case-status': document.getElementById('case-status'),
        'box-status': document.getElementById('box-status'),
        'cover-status': document.getElementById('cover-status'),
        'final-status': document.getElementById('final-status')
    };
    
    for (const [taskType, status] of Object.entries(statusData)) {
        const badgeId = `${taskType.toLowerCase()}-status`;
        const badge = statusBadges[badgeId];
        
        if (badge) {
            const prevStatus = badge.getAttribute('data-previous');
            badge.textContent = status;
            badge.className = `badge task-status ${status}`;
            
            // Log status changes if different from previous
            if (status === 'RUNNING' && prevStatus !== 'RUNNING') {
                addLogEntry(`${taskType} task started running`, logLevels.INFO);
            } else if (status === 'ERROR' && prevStatus !== 'ERROR') {
                addLogEntry(`${taskType} task encountered an error`, logLevels.ERROR);
            } else if (status === 'COMPLETED' && prevStatus !== 'COMPLETED') {
                addLogEntry(`${taskType} task completed`, logLevels.INFO);
            }
            
            badge.setAttribute('data-previous', status);
        }
    }
}

// Update system logs from API data
function updateSystemLogs(logs) {
    if (!Array.isArray(logs) || logs.length === 0) return;
    
    const existingEntries = new Set();
    document.querySelectorAll('.log-entry').forEach(entry => {
        existingEntries.add(entry.getAttribute('data-log-id'));
    });
    
    logs.forEach(log => {
        if (log.id && existingEntries.has(log.id)) return;
        
        const level = log.level ? log.level.toLowerCase() : '';
        addLogEntry(
            log.message, 
            logLevels[level.toUpperCase()] || '', 
            log.timestamp, 
            log.id
        );
    });
}

// Simulate task statuses for demo/fallback purposes
function simulateTaskStatuses() {
    const statusBadges = {
        'case-status': document.getElementById('case-status'),
        'box-status': document.getElementById('box-status'),
        'cover-status': document.getElementById('cover-status'),
        'final-status': document.getElementById('final-status')
    };
    
    const statuses = ['IDLE', 'RUNNING', 'COMPLETED', 'ERROR'];
    
    for (const [id, badge] of Object.entries(statusBadges)) {
        if (badge) {
            // For simulation, randomly change statuses occasionally
            if (Math.random() < 0.3) {
                const newStatus = statuses[Math.floor(Math.random() * statuses.length)];
                const prevStatus = badge.getAttribute('data-previous');
                
                badge.textContent = newStatus;
                badge.className = `badge task-status ${newStatus}`;
                
                // Log status changes if different from previous
                if (newStatus === 'RUNNING' && prevStatus !== 'RUNNING') {
                    addLogEntry(`${id.replace('-status', '')} task started running`, logLevels.INFO);
                } else if (newStatus === 'ERROR' && prevStatus !== 'ERROR') {
                    addLogEntry(`${id.replace('-status', '')} task encountered an error`, logLevels.ERROR);
                }
                
                badge.setAttribute('data-previous', newStatus);
            }
        }
    }
}


// Add a log entry to all logs panels
function addLogEntry(message, level = '', timestamp = null, logId = null) {
    // Find all system logs containers using class selector
    const logsPanels = document.querySelectorAll('.logs-content');
    if (logsPanels.length === 0) return;
    
    // Create timestamp if not provided
    let timeString;
    if (timestamp) {
        timeString = formatDateTime(timestamp);
    } else {
        const now = new Date();
        timeString = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    }
    
    // Create log entry text
    const logText = `[${timeString}] ${message}`;
    
    // Add to all log panels
    logsPanels.forEach(logsPanel => {
        const entry = document.createElement('div');
        entry.className = `log-entry ${level}`;
        
        if (logId) {
            entry.setAttribute('data-log-id', logId);
        }
        
        entry.textContent = logText;
        
        // Add to the beginning for newest first
        logsPanel.prepend(entry);
        
        // Limit number of log entries to prevent excessive DOM growth
        const logEntries = logsPanel.querySelectorAll('.log-entry');
        if (logEntries.length > 100) {
            logsPanel.removeChild(logEntries[logEntries.length - 1]);
        }
    });
}

// // Add a log entry to the logs panel
// function addLogEntry(message, level = '', timestamp = null, logId = null) {
//     // Find all system logs containers in each panel
//     const logsPanels = document.querySelectorAll('#system-logs');
//     if (logsPanels.length === 0) return;
    
//     // Create timestamp if not provided
//     let timeString;
//     if (timestamp) {
//         timeString = formatDateTime(timestamp);
//     } else {
//         const now = new Date();
//         timeString = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
//     }
    
//     // Create log entry
//     const logText = `[${timeString}] ${message}`;
    
//     // Add to all log panels
//     logsPanels.forEach(logsPanel => {
//         const entry = document.createElement('div');
//         entry.className = `log-entry ${level}`;
        
//         if (logId) {
//             entry.setAttribute('data-log-id', logId);
//         }
        
//         entry.textContent = logText;
        
//         // Add to the beginning for newest first
//         logsPanel.prepend(entry);
        
//         // Limit number of log entries to prevent excessive DOM growth
//         const logEntries = logsPanel.querySelectorAll('.log-entry');
//         if (logEntries.length > 100) {
//             logsPanel.removeChild(logEntries[logEntries.length - 1]);
//         }
//     });
// }

// Helper function to format date/time
function formatDateTime(dateTimeString) {
    if (!dateTimeString) return 'Unknown';
    
    const date = new Date(dateTimeString);
    if (isNaN(date.getTime())) return dateTimeString;
    
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// Fallback simulation function for when API is not available
function fallbackSimulation() {
    console.warn("Using fallback simulation as API is not available");
    addLogEntry("API not available, using simulation mode", logLevels.WARNING);

    const now = new Date();
    const timestamp = now.toISOString();

    const simulatedData = {};
    const simulatedStatuses = {};

    for (const taskType of taskTypes) {
        const hasData = Math.random() > 0.2;

        if (hasData) {
            const statuses = ["IDLE", "RUNNING", "COMPLETED", "ERROR"];
            const status = statuses[Math.floor(Math.random() * statuses.length)];
            simulatedStatuses[taskType] = status;

            simulatedData[taskType] = {
                path: `${taskType.toLowerCase()}_frame_${Math.floor(Math.random() * 1000)}.jpg`,
                timestamp: formatDateTime(timestamp),
                status: status === "COMPLETED" ? "OK" : status === "ERROR" ? "ERROR" : "-",
                confidence: status === "COMPLETED" ? `${(80 + Math.random() * 19.9).toFixed(1)}%` : "-",
                details:
                    status === "COMPLETED"
                    ? "Task completed successfully"
                    : status === "ERROR"
                    ? "Device not responding"
                    : status === "RUNNING"
                    ? "Processing..."
                    : "-",
            };
        } else {
            simulatedData[taskType] = null;
            simulatedStatuses[taskType] = "IDLE";
        }
    }

    updateCameraFeeds(simulatedData);
    updateResultsPanel(simulatedData);

    const statusBadges = {
        "case-status": document.getElementById("case-status"),
        "box-status": document.getElementById("box-status"),
        "cover-status": document.getElementById("cover-status"),
        "final-status": document.getElementById("final-status")
    };

    for (const [taskType, status] of Object.entries(simulatedStatuses)) {
        const badge = statusBadges[`${taskType.toLowerCase()}-status`];
        if (badge) {
            badge.textContent = status;
            badge.className = `badge task-status ${status}`;
        }
    }
}