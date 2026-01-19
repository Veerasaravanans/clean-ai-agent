/* ═══════════════════════════════════════════════════════════════
   AI Agent Framework - JavaScript Application
   COMPLETE VERSION WITH DEVICE COORDINATES + ALL 40+ VIO MODELS + VERIFICATION IMAGES
   ═══════════════════════════════════════════════════════════════ */

/* ─────────────────────────────────────────────────────────────── */
/* Global State */
/* ─────────────────────────────────────────────────────────────── */
const state = {
    // Agent State
    agentStatus: 'idle',
    agentMode: 'idle',
    deviceConnected: false,
    
    // Current Test
    currentTest: null,
    currentStep: 0,
    totalSteps: 0,
    testProgress: 0,
    
    // Screen
    screenDimensions: { width: 0, height: 0 },
    streamActive: false,
    
    // Logs
    logs: [],
    logFilter: 'all',
    
    // WebSockets
    ws: {
        screen: null,
        logs: null,
        status: null
    },
    
    // Settings
    settings: {
        apiUrl: 'http://localhost:8000',
        streamFps: 2,
        autoScrollLogs: true,
        showCoordinates: true
    },
    
    // Statistics
    statistics: {
        testsExecuted: 0,
        testsPassed: 0,
        testsFailed: 0,
        successRate: 0
    },
    
    // RAG Stats
    ragStats: {
        testCases: 0,
        learnedSolutions: 0
    },
    
    // Device Coordinates
    deviceCoordinates: [],
    
    // Verification Images (NEW)
    verificationImages: []
};

/* ─────────────────────────────────────────────────────────────── */
/* API Functions */
/* ─────────────────────────────────────────────────────────────── */

// Base API request function
async function apiRequest(endpoint, method = 'GET', body = null) {
    const url = `${state.settings.apiUrl}${endpoint}`;
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    try {
        const response = await fetch(url, options);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || data.message || 'API request failed');
        }
        
        return data;
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        showNotification(`API Error: ${error.message}`, 'error');
        throw error;
    }
}

/* ─────────────────────────────────────────────────────────────── */
/* Test Execution APIs */
/* ─────────────────────────────────────────────────────────────── */

async function runTest(testId, options = {}) {
    const { useLearned = true, maxRetries = 3 } = options;
    
    addLog('info', `Starting test: ${testId}`);
    
    const result = await apiRequest('/api/run-tests', 'POST', {
        test_ids: [testId],
        use_learned: useLearned,
        max_retries: maxRetries,
        verify_each_step: true
    });
    
    if (result.success) {
        state.currentTest = testId;
        addLog('success', `Test started: ${testId}`);
        showNotification('Test execution started', 'success');
    }
    
    return result;
}

async function stopExecution() {
    addLog('warning', 'Stopping execution...');
    
    const result = await apiRequest('/api/stop', 'POST');
    
    if (result.success) {
        state.currentTest = null;
        state.currentStep = 0;
        state.totalSteps = 0;
        addLog('info', 'Execution stopped');
        showNotification('Execution stopped', 'info');
    }
    
    return result;
}

/* ─────────────────────────────────────────────────────────────── */
/* Standalone Command APIs */
/* ─────────────────────────────────────────────────────────────── */

async function executeCommand(command) {
    addLog('info', `Executing command: ${command}`);
    
    const result = await apiRequest('/api/execute-command', 'POST', {
        command,
        timeout: 30,
        verify: true
    });
    
    if (result.success) {
        addLog('success', `Command executed: ${command}`);
        showNotification('Command executed', 'success');
    }
    
    return result;
}

async function tap(x, y) {
    addLog('info', `Tap at (${x}, ${y})`);
    
    const result = await apiRequest('/api/tap', 'POST', { x, y });
    
    if (result.success) {
        addLog('success', `Tapped at (${x}, ${y})`);
    }
    
    return result;
}

async function swipe(x1, y1, x2, y2, duration = 300) {
    addLog('info', `Swipe from (${x1}, ${y1}) to (${x2}, ${y2})`);
    
    const result = await apiRequest('/api/swipe', 'POST', {
        start_x: x1,
        start_y: y1,
        end_x: x2,
        end_y: y2,
        duration_ms: duration
    });
    
    if (result.success) {
        addLog('success', 'Swipe executed');
    }
    
    return result;
}

async function pressBack() {
    addLog('info', 'Pressing Back button');
    const result = await apiRequest('/api/press-back', 'POST');
    if (result.success) addLog('success', 'Back button pressed');
    return result;
}

async function pressHome() {
    addLog('info', 'Pressing Home button');
    const result = await apiRequest('/api/press-home', 'POST');
    if (result.success) addLog('success', 'Home button pressed');
    return result;
}

/* ─────────────────────────────────────────────────────────────── */
/* HITL APIs */
/* ─────────────────────────────────────────────────────────────── */

async function sendGuidance(guidance, coords = null, actionType = null) {
    addLog('hitl', `Sending guidance: ${guidance}`);
    
    const result = await apiRequest('/api/send-guidance', 'POST', {
        guidance,
        coordinates: coords,
        action_type: actionType
    });
    
    if (result.success) {
        addLog('success', 'Guidance sent successfully');
        showNotification('Guidance sent', 'success');
    }
    
    return result;
}

/* ═══════════════════════════════════════════════════════════════ */
/* DEVICE COORDINATES APIs */
/* ═══════════════════════════════════════════════════════════════ */

async function addDeviceCoordinate() {
    const iconName = document.getElementById('coord-icon-name').value.trim();
    const x = document.getElementById('coord-x').value;
    const y = document.getElementById('coord-y').value;
    
    if (!iconName || !x || !y) {
        showNotification('Please fill all fields', 'warning');
        return;
    }
    
    try {
        addLog('info', `Adding coordinate: ${iconName} (${x}, ${y})`);
        
        const result = await apiRequest('/api/device/coordinate/add', 'POST', {
            icon_name: iconName,
            x: parseInt(x),
            y: parseInt(y)
        });
        
        if (result) {
            addLog('success', `Coordinate added: ${iconName}`);
            showNotification('Coordinate added successfully', 'success');
            
            // Clear inputs
            document.getElementById('coord-icon-name').value = '';
            document.getElementById('coord-x').value = '';
            document.getElementById('coord-y').value = '';
            
            // Refresh list
            await viewDeviceCoordinates();
        }
    } catch (error) {
        console.error('Add coordinate error:', error);
    }
}

async function viewDeviceCoordinates() {
    try {
        const result = await apiRequest('/api/device/coordinates');
        
        if (result && Array.isArray(result)) {
            state.deviceCoordinates = result;
            
            // Show coordinate list
            const container = document.getElementById('coord-list-container');
            const listElement = document.getElementById('coord-list');
            
            if (result.length === 0) {
                listElement.innerHTML = '<div style="padding: 8px; color: #888; font-size: 11px;">No coordinates stored yet</div>';
                container.style.display = 'block';
                addLog('info', 'No coordinates found');
            } else {
                listElement.innerHTML = result.map(coord => `
                    <div style="padding: 6px; margin-bottom: 4px; background: #2a2a3e; border-radius: 4px; font-size: 11px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: bold; color: #4a9eff;">${coord.icon_name}</span>
                            <span style="color: #888;">(${coord.x}, ${coord.y})</span>
                        </div>
                        ${coord.verified ? '<div style="margin-top: 2px; color: #4CAF50; font-size: 10px;">✓ Verified by ' + coord.verified_by + '</div>' : ''}
                    </div>
                `).join('');
                
                container.style.display = 'block';
                addLog('success', `Loaded ${result.length} stored coordinates`);
            }
        }
    } catch (error) {
        console.error('View coordinates error:', error);
        addLog('error', 'Failed to load coordinates');
    }
}

async function deleteDeviceCoordinate() {
    const iconName = document.getElementById('coord-icon-name').value.trim();
    
    if (!iconName) {
        showNotification('Enter icon name to delete', 'warning');
        return;
    }
    
    if (!confirm(`Delete coordinate for '${iconName}'?`)) {
        return;
    }
    
    try {
        addLog('info', `Deleting coordinate: ${iconName}`);
        
        const result = await apiRequest(`/api/device/coordinate/${iconName}`, 'DELETE');
        
        if (result) {
            addLog('success', `Coordinate deleted: ${iconName}`);
            showNotification('Coordinate deleted', 'success');
            
            // Clear input
            document.getElementById('coord-icon-name').value = '';
            
            // Refresh list
            await viewDeviceCoordinates();
        }
    } catch (error) {
        console.error('Delete coordinate error:', error);
    }
}

async function getCurrentDevice() {
    try {
        const result = await apiRequest('/api/device/current');
        
        if (result && result.device) {
            addLog('info', `Current device: ${result.device.screen_resolution}`);
            if (result.profile) {
                addLog('info', `Profile: ${result.profile.device_id} (${result.profile.icon_count} icons)`);
            }
        }
    } catch (error) {
        console.error('Get current device error:', error);
    }
}

/* ═══════════════════════════════════════════════════════════════ */
/* VERIFICATION IMAGES APIs - NEW */
/* ═══════════════════════════════════════════════════════════════ */

async function captureVerificationImage() {
    const imageName = document.getElementById('verification-image-name').value.trim();
    const description = document.getElementById('verification-image-description').value.trim();
    
    if (!imageName) {
        showNotification('Please enter an image name', 'warning');
        return;
    }
    
    try {
        addLog('info', `Capturing verification image: ${imageName}`);
        
        const result = await apiRequest('/api/verification/capture', 'POST', {
            image_name: imageName,
            description: description || null
        });
        
        if (result.success) {
            addLog('success', `Verification image captured: ${imageName}`);
            showNotification(`✅ Verification image "${imageName}" captured`, 'success');
            
            // Clear inputs
            document.getElementById('verification-image-name').value = '';
            document.getElementById('verification-image-description').value = '';
            
            // Update device info display
            updateVerificationDeviceInfo(result.device_id, result.resolution);
            
            // Refresh list if visible
            const listContainer = document.getElementById('verification-images-list-container');
            if (listContainer.style.display === 'block') {
                await viewVerificationImages();
            }
        }
    } catch (error) {
        console.error('Capture verification image error:', error);
        addLog('error', `Failed to capture verification image: ${error.message}`);
    }
}

async function viewVerificationImages() {
    try {
        const result = await apiRequest('/api/verification/images');
        
        if (!result.success) {
            showNotification('Failed to load verification images', 'error');
            return;
        }
        
        const container = document.getElementById('verification-images-list-container');
        const listElement = document.getElementById('verification-images-list');
        
        if (!result.images || result.images.length === 0) {
            listElement.innerHTML = '<div style="padding: 8px; color: #888; font-size: 11px;">No verification images captured yet</div>';
            container.style.display = 'block';
            addLog('info', 'No verification images found');
            return;
        }
        
        // Build list HTML
        listElement.innerHTML = result.images.map(img => {
            const date = img.created_at ? new Date(img.created_at).toLocaleDateString() : 'Unknown';
            
            return `
                <div class="verification-image-item" data-image-name="${img.name}">
                    <span class="verification-image-name">${img.name}</span>
                    <span class="verification-image-date">${date}</span>
                    <button 
                        class="verification-image-delete" 
                        onclick="deleteVerificationImage('${img.name}'); event.stopPropagation();"
                        title="Delete this image"
                    >
                        🗑️
                    </button>
                </div>
            `;
        }).join('');
        
        // Add click handlers for preview
        document.querySelectorAll('.verification-image-item').forEach(item => {
            item.addEventListener('click', () => {
                const imageName = item.getAttribute('data-image-name');
                previewVerificationImage(imageName);
            });
        });
        
        container.style.display = 'block';
        addLog('success', `Loaded ${result.images.length} verification images`);
        
        // Update device info
        updateVerificationDeviceInfo(result.device_id, result.resolution);
        
    } catch (error) {
        console.error('View verification images error:', error);
        addLog('error', 'Failed to load verification images');
    }
}

async function previewVerificationImage(imageName) {
    try {
        const imageUrl = `${state.settings.apiUrl}/api/verification/image/${imageName}`;
        
        const modal = document.getElementById('verification-image-preview-modal');
        const img = document.getElementById('verification-preview-image');
        const nameDisplay = document.getElementById('verification-preview-name');
        
        img.src = imageUrl;
        nameDisplay.textContent = imageName;
        modal.style.display = 'flex';
        
        addLog('info', `Previewing verification image: ${imageName}`);
        
        // Auto-close after 3 seconds
        setTimeout(() => {
            modal.style.display = 'none';
        }, 3000);
        
    } catch (error) {
        console.error('Preview verification image error:', error);
        showNotification('Failed to preview image', 'error');
    }
}

async function deleteVerificationImage(imageName) {
    if (!confirm(`Delete verification image "${imageName}"?`)) {
        return;
    }
    
    try {
        addLog('info', `Deleting verification image: ${imageName}`);
        
        const result = await apiRequest(`/api/verification/image/${imageName}`, 'DELETE');
        
        if (result.success) {
            addLog('success', `Verification image deleted: ${imageName}`);
            showNotification(`Verification image "${imageName}" deleted`, 'success');
            
            // Refresh list
            await viewVerificationImages();
        }
    } catch (error) {
        console.error('Delete verification image error:', error);
        addLog('error', `Failed to delete verification image: ${error.message}`);
    }
}

function updateVerificationDeviceInfo(deviceId, resolution) {
    const deviceInfoElement = document.getElementById('verification-device-id');
    if (deviceInfoElement) {
        if (deviceId) {
            deviceInfoElement.textContent = `${deviceId} (${resolution})`;
        } else {
            deviceInfoElement.textContent = 'Not connected';
        }
    }
}

/* ─────────────────────────────────────────────────────────────── */
/* Status & Info APIs */
/* ─────────────────────────────────────────────────────────────── */

async function getStatus() {
    const result = await apiRequest('/api/status');
    
    if (result.success && result.data) {
        updateAgentStatus(result.data);
    }
    
    return result;
}

async function getDeviceInfo() {
    const result = await apiRequest('/api/device');
    
    if (result.success && result.data) {
        updateDeviceInfo(result.data);
    }
    
    return result;
}

async function getStatistics() {
    const result = await apiRequest('/api/statistics');
    
    if (result.success && result.data) {
        updateStatistics(result.data);
    }
    
    return result;
}

async function getHealthCheck() {
    try {
        const result = await apiRequest('/health');
        return result;
    } catch (error) {
        console.error('Health check failed:', error);
        return { status: 'error' };
    }
}

/* ─────────────────────────────────────────────────────────────── */
/* UI Update Functions */
/* ─────────────────────────────────────────────────────────────── */

function updateAgentStatus(data) {
    state.agentStatus = data.status || 'idle';
    state.agentMode = data.mode || 'idle';
    state.currentStep = data.current_step || 0;
    state.totalSteps = data.total_steps || 0;
    
    const statusDot = document.getElementById('agent-status-dot');
    const statusText = document.getElementById('agent-status-text');
    
    if (statusDot && statusText) {
        statusDot.className = `status-dot ${state.agentStatus}`;
        statusText.textContent = state.agentStatus.charAt(0).toUpperCase() + state.agentStatus.slice(1);
    }
    
    const cardStatus = document.getElementById('card-agent-status');
    if (cardStatus) {
        cardStatus.textContent = state.agentStatus.charAt(0).toUpperCase() + state.agentStatus.slice(1);
    }
    
    if (state.totalSteps > 0) {
        state.testProgress = (state.currentStep / state.totalSteps) * 100;
        updateProgressBar(state.testProgress, state.currentStep, state.totalSteps);
    }
}

function updateDeviceInfo(data) {
    state.deviceConnected = data.connected || false;
    
    if (data.connected) {
        state.screenDimensions = data.resolution || { width: 0, height: 0 };
        
        document.getElementById('device-model').textContent = data.model || '-';
        document.getElementById('device-android').textContent = data.android_version || '-';
        document.getElementById('device-resolution').textContent = 
            `${data.resolution?.width || 0}x${data.resolution?.height || 0}`;
    }
    
    const deviceStatusDot = document.getElementById('device-status-dot');
    const deviceStatusText = document.getElementById('device-status-text');
    
    if (deviceStatusDot && deviceStatusText) {
        deviceStatusDot.className = `status-dot ${data.connected ? 'connected' : 'disconnected'}`;
        deviceStatusText.textContent = data.connected ? 'Connected' : 'Disconnected';
    }
    
    const cardDevice = document.getElementById('card-device-status');
    if (cardDevice) {
        cardDevice.textContent = data.connected ? 'Connected' : 'Disconnected';
    }
}

function updateStatistics(data) {
    state.statistics = {
        testsExecuted: data.tests_executed || 0,
        testsPassed: data.tests_passed || 0,
        testsFailed: data.tests_failed || 0,
        successRate: data.tests_executed > 0 
            ? ((data.tests_passed / data.tests_executed) * 100).toFixed(1)
            : 0
    };
    
    document.getElementById('card-tests-executed').textContent = state.statistics.testsExecuted;
    document.getElementById('card-success-rate').textContent = `${state.statistics.successRate}%`;
}

function updateProgressBar(percentage, current, total) {
    const container = document.getElementById('test-progress-container');
    const fill = document.getElementById('test-progress-fill');
    const text = document.getElementById('test-progress-text');
    
    if (container && fill && text) {
        if (total > 0) {
            container.style.display = 'block';
            fill.style.width = `${percentage}%`;
            text.textContent = `${current}/${total} steps`;
        } else {
            container.style.display = 'none';
        }
    }
}

/* ─────────────────────────────────────────────────────────────── */
/* Logging Functions */
/* ─────────────────────────────────────────────────────────────── */

function addLog(level, message, metadata = {}) {
    const timestamp = new Date().toISOString();
    const logEntry = { level, message, timestamp, metadata };
    
    state.logs.push(logEntry);
    
    const logContainer = document.getElementById('execution-log');
    if (logContainer) {
        const logElement = createLogElement(logEntry);
        logContainer.appendChild(logElement);
        
        if (state.settings.autoScrollLogs) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    }
}

function createLogElement(log) {
    const div = document.createElement('div');
    div.className = `log-entry log-${log.level}`;
    
    const category = detectLogCategory(log);
    div.setAttribute('data-category', category);
    
    const time = document.createElement('span');
    time.className = 'log-time';
    time.textContent = formatTimestamp(log.timestamp);
    
    const level = document.createElement('span');
    level.className = 'log-level';
    level.textContent = log.level.toUpperCase();
    
    const message = document.createElement('span');
    message.className = 'log-message';
    message.textContent = log.message;
    
    div.appendChild(time);
    div.appendChild(level);
    div.appendChild(message);
    
    return div;
}

function detectLogCategory(log) {
    const msg = log.message.toLowerCase();
    const logger = log.logger || '';
    
    if (msg.includes('analyz') || msg.includes('plan') || msg.includes('reasoning') || 
        msg.includes('🎯') || msg.includes('🤖') || msg.includes('vision') || 
        msg.includes('detected') || msg.includes('llm') || msg.includes('thinking') ||
        msg.includes('ai vision') || msg.includes('ai analysis')) {
        return 'ai';
    }
    
    if (msg.includes('tap at') || msg.includes('swipe') || msg.includes('press') ||
        msg.includes('⚡') || msg.includes('execut') || msg.includes('action') || 
        msg.includes('adb') || msg.includes('verif') || msg.includes('🔍') ||
        msg.includes('step') || msg.includes('capture') || msg.includes('screenshot') ||
        msg.includes('screen changed') || logger.includes('adb_tool') ||
        logger.includes('verification_tool')) {
        return 'execution';
    }
    
    if (msg.includes('starting test') || msg.includes('executing command') || 
        msg.includes('run') || msg.includes('button') || msg.includes('clicked')) {
        return 'user-action';
    }
    
    if (log.level === 'hitl' || msg.includes('guidance') || msg.includes('human') ||
        msg.includes('👤') || msg.includes('waiting for human')) {
        return 'hitl';
    }
    
    if (log.level === 'error' || log.level === 'warning' ||
        msg.includes('❌') || msg.includes('⚠')) {
        return 'error-warning';
    }
    
    if (msg.includes('system running') || msg.includes('ready') || msg.includes('connected') ||
        msg.includes('backend') || msg.includes('stream') || msg.includes('websocket') ||
        msg.includes('initial') || msg.includes('startup') || msg.includes('disconnected') ||
        msg.includes('health') || msg.includes('polling')) {
        return 'system';
    }
    
    if (logger.includes('langgraph') || logger.includes('vision_tool')) {
        return 'ai';
    }
    if (logger.includes('adb_tool') || logger.includes('verification')) {
        return 'execution';
    }
    
    if (logger.includes('backend')) {
        return 'execution';
    }
    
    return 'system';
}

function clearLogs() {
    state.logs = [];
    const logContainer = document.getElementById('execution-log');
    if (logContainer) {
        logContainer.innerHTML = '';
    }
    addLog('info', 'Logs cleared');
}

/* ─────────────────────────────────────────────────────────────── */
/* Notification Functions */
/* ─────────────────────────────────────────────────────────────── */

function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/* ─────────────────────────────────────────────────────────────── */
/* Utility Functions */
/* ─────────────────────────────────────────────────────────────── */

function formatTimestamp(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function updateConnectionTime() {
    const element = document.getElementById('connection-time');
    if (!element) return;
    
    const uptime = Math.floor((Date.now() - state.startTime) / 1000);
    element.textContent = `Connected: ${formatDuration(uptime)}`;
}

/* ─────────────────────────────────────────────────────────────── */
/* Canvas Drawing */
/* ─────────────────────────────────────────────────────────────── */

function drawImageOnCanvas(imageUrl) {
    const canvas = document.getElementById('screen-canvas');
    const overlay = document.getElementById('canvas-overlay');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const img = new Image();
    
    img.onload = () => {
        if (canvas.width !== img.width || canvas.height !== img.height) {
            canvas.width = img.width;
            canvas.height = img.height;
        }
        
        ctx.drawImage(img, 0, 0);
        
        if (overlay) {
            overlay.classList.add('hidden');
        }
        
        URL.revokeObjectURL(imageUrl);
    };
    
    img.onerror = () => {
        console.error('Failed to load image');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
        URL.revokeObjectURL(imageUrl);
    };
    
    img.src = imageUrl;
}

/* ─────────────────────────────────────────────────────────────── */
/* WebSocket - Screen Stream */
/* ─────────────────────────────────────────────────────────────── */

function connectScreenStream() {
    const wsUrl = state.settings.apiUrl.replace('http', 'ws') + '/ws/screen';
    
    console.log('Connecting to screen stream:', wsUrl);
    
    try {
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('✅ Screen stream connected');
            state.streamActive = true;
            
            const toggleBtn = document.getElementById('toggle-stream-btn');
            if (toggleBtn) {
                toggleBtn.textContent = '🟢 Stream On';
                toggleBtn.classList.add('btn-success');
            }
            
            addLog('success', 'Screen stream connected');
        };
        
        ws.onmessage = (event) => {
            if (event.data instanceof Blob) {
                const url = URL.createObjectURL(event.data);
                drawImageOnCanvas(url);
            }
        };
        
        ws.onerror = (error) => {
            console.error('Screen stream error:', error);
            addLog('error', 'Screen stream error');
        };
        
        ws.onclose = () => {
            console.log('Screen stream disconnected');
            state.streamActive = false;
            
            const toggleBtn = document.getElementById('toggle-stream-btn');
            if (toggleBtn) {
                toggleBtn.textContent = '🔴 Stream Off';
                toggleBtn.classList.remove('btn-success');
            }
            
            addLog('warning', 'Screen stream disconnected');
            handleDisconnect('screen');
        };
        
        state.ws.screen = ws;
        
    } catch (error) {
        console.error('Failed to connect screen stream:', error);
        handleDisconnect('screen');
    }
}

/* ─────────────────────────────────────────────────────────────── */
/* WebSocket - Logs Stream */
/* ─────────────────────────────────────────────────────────────── */

function connectLogsStream() {
    const wsUrl = state.settings.apiUrl.replace('http', 'ws') + '/ws/logs';
    
    console.log('Connecting to logs stream:', wsUrl);
    
    try {
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('✅ Logs stream connected');
        };
        
        ws.onmessage = (event) => {
            try {
                const logData = JSON.parse(event.data);
                
                if (logData.type === 'log') {
                    addLog(
                        logData.level || 'info',
                        logData.message || '',
                        logData.metadata || {}
                    );
                }
            } catch (error) {
                console.error('Failed to parse log message:', error);
            }
        };
        
        ws.onerror = (error) => {
            console.error('Logs stream error:', error);
        };
        
        ws.onclose = () => {
            console.log('Logs stream disconnected');
            handleDisconnect('logs');
        };
        
        state.ws.logs = ws;
        
    } catch (error) {
        console.error('Failed to connect logs stream:', error);
        handleDisconnect('logs');
    }
}

/* ─────────────────────────────────────────────────────────────── */
/* WebSocket - Status Stream */
/* ─────────────────────────────────────────────────────────────── */

function connectStatusStream() {
    const wsUrl = state.settings.apiUrl.replace('http', 'ws') + '/ws/status';
    
    console.log('Connecting to status stream:', wsUrl);
    
    try {
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('✅ Status stream connected');
        };
        
        ws.onmessage = (event) => {
            try {
                const statusData = JSON.parse(event.data);
                
                if (statusData.type === 'status') {
                    updateStatusUI(statusData);
                } else if (statusData.type === 'hitl_request') {
                    handleHITLRequest(statusData);
                }
            } catch (error) {
                console.error('Failed to parse status message:', error);
            }
        };
        
        ws.onerror = (error) => {
            console.error('Status stream error:', error);
        };
        
        ws.onclose = () => {
            console.log('Status stream disconnected');
            handleDisconnect('status');
        };
        
        state.ws.status = ws;
        
    } catch (error) {
        console.error('Failed to connect status stream:', error);
        handleDisconnect('status');
    }
}

function updateStatusUI(statusData) {
    if (statusData.status) {
        state.agentStatus = statusData.status;
        
        const statusDot = document.getElementById('agent-status-dot');
        const statusText = document.getElementById('agent-status-text');
        
        if (statusDot && statusText) {
            statusDot.className = `status-dot ${statusData.status}`;
            statusText.textContent = statusData.status.charAt(0).toUpperCase() + statusData.status.slice(1);
        }
    }
    
    if (statusData.current_step !== undefined && statusData.total_steps !== undefined) {
        state.currentStep = statusData.current_step;
        state.totalSteps = statusData.total_steps;
        
        if (state.totalSteps > 0) {
            const percentage = (state.currentStep / state.totalSteps) * 100;
            updateProgressBar(percentage, state.currentStep, state.totalSteps);
        }
    }
}

function handleHITLRequest(data) {
    addLog('hitl', `HITL Request: ${data.problem || 'Assistance needed'}`);
    showNotification('Human guidance needed!', 'warning');
    
    state.agentStatus = 'waiting_hitl';
    
    const statusDot = document.getElementById('agent-status-dot');
    if (statusDot) {
        statusDot.className = 'status-dot waiting_hitl';
    }
}

function handleDisconnect(wsType) {
    console.log(`${wsType} disconnected, will reconnect in 3 seconds...`);
    
    if (state.ws[wsType]) {
        state.ws[wsType] = null;
    }
    
    setTimeout(() => {
        if (wsType === 'screen') {
            connectScreenStream();
        } else if (wsType === 'logs') {
            connectLogsStream();
        } else if (wsType === 'status') {
            connectStatusStream();
        }
    }, 3000);
}

function connectWebSockets() {
    console.log('Connecting WebSockets...');
    
    try {
        connectScreenStream();
        connectLogsStream();
        connectStatusStream();
    } catch (error) {
        console.error('Failed to connect WebSockets:', error);
        addLog('error', 'WebSocket connection failed');
    }
}

function disconnectWebSockets() {
    console.log('Disconnecting WebSockets...');
    
    if (state.ws.screen) {
        state.ws.screen.close();
        state.ws.screen = null;
    }
    
    if (state.ws.logs) {
        state.ws.logs.close();
        state.ws.logs = null;
    }
    
    if (state.ws.status) {
        state.ws.status.close();
        state.ws.status = null;
    }
    
    state.streamActive = false;
}

/* ─────────────────────────────────────────────────────────────── */
/* Status Polling */
/* ─────────────────────────────────────────────────────────────── */

function startStatusPolling() {
    setInterval(async () => {
        try {
            await getStatus();
        } catch (error) {
            console.error('Status polling error:', error);
        }
    }, 2000);
    
    setInterval(async () => {
        try {
            await getDeviceInfo();
        } catch (error) {
            console.error('Device info polling error:', error);
        }
    }, 5000);
    
    setInterval(updateConnectionTime, 1000);
}

/* ─────────────────────────────────────────────────────────────── */
/* Modal Functions */
/* ─────────────────────────────────────────────────────────────── */

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

/* ─────────────────────────────────────────────────────────────── */
/* Initialization */
/* ─────────────────────────────────────────────────────────────── */

async function initApp() {
    console.log('Initializing AI Agent Framework...');
    
    state.startTime = Date.now();
    
    addLog('info', 'System ready. Waiting for commands...');
    
    loadSettings();
    
    try {
        const health = await getHealthCheck();
        if (health.status === 'ok') {
            addLog('success', 'Backend connection established');
            showNotification('Connected to backend', 'success');
        }
        
        await getDeviceInfo();
        await getStatistics();
        await getCurrentDevice();
        
        // Load verification device info (NEW)
        try {
            const deviceInfo = await getDeviceInfo();
            if (deviceInfo.success && deviceInfo.data && deviceInfo.data.connected) {
                const resolution = deviceInfo.data.resolution;
                const deviceId = `device_${resolution.width}x${resolution.height}`;
                updateVerificationDeviceInfo(deviceId, `${resolution.width}x${resolution.height}`);
            }
        } catch (error) {
            console.error('Failed to load verification device info:', error);
        }
        
    } catch (error) {
        console.error('Initialization error:', error);
        addLog('error', 'Failed to connect to backend');
        showNotification('Backend connection failed', 'error');
    }
    
    console.log('✅ Initialization complete');
}

function loadSettings() {
    const saved = localStorage.getItem('agentSettings');
    if (saved) {
        try {
            const settings = JSON.parse(saved);
            state.settings = { ...state.settings, ...settings };
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }
}

function saveSettings() {
    localStorage.setItem('agentSettings', JSON.stringify(state.settings));
    showNotification('Settings saved', 'success');
}

/* ─────────────────────────────────────────────────────────────── */
/* Coordinate Display Helper */
/* ─────────────────────────────────────────────────────────────── */

function updateCoordinateDisplay(x, y) {
    const display = document.getElementById('coordinate-display');
    if (display && state.settings.showCoordinates) {
        display.textContent = `x: ${x}, y: ${y}`;
    }
}

function showCoordinates(x, y) {
    updateCoordinateDisplay(x, y);
    showNotification(`Tapped at (${x}, ${y})`, 'info');
}

/* ─────────────────────────────────────────────────────────────── */
/* Log Export & Filter */
/* ─────────────────────────────────────────────────────────────── */

function exportLogs() {
    const logsText = state.logs.map(log => 
        `[${formatTimestamp(log.timestamp)}] [${log.level.toUpperCase()}] ${log.message}`
    ).join('\n');
    
    const blob = new Blob([logsText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    
    showNotification('Logs exported', 'success');
}

function filterLogs() {
    const filter = document.getElementById('log-filter-select').value;
    state.logFilter = filter;
    
    const logContainer = document.getElementById('execution-log');
    if (!logContainer) return;
    
    const entries = logContainer.querySelectorAll('.log-entry');
    entries.forEach(entry => {
        let shouldShow = false;
        
        if (filter === 'all') {
            shouldShow = true;
        } else if (filter === 'execution-only') {
            const cat = entry.getAttribute('data-category');
            shouldShow = cat === 'execution' || cat === 'ai' || cat === 'hitl' || cat === 'error-warning';
        } else if (filter === 'ai-only') {
            shouldShow = entry.getAttribute('data-category') === 'ai';
        } else if (filter === 'user-actions') {
            shouldShow = entry.getAttribute('data-category') === 'user-action';
        } else if (filter === 'errors-warnings') {
            shouldShow = entry.getAttribute('data-category') === 'error-warning';
        } else {
            shouldShow = entry.classList.contains(`log-${filter}`);
        }
        
        entry.style.display = shouldShow ? 'flex' : 'none';
    });
}

/* ═══════════════════════════════════════════════════════════════ */
/* VIO MODEL SWITCHING - ALL 40+ MODELS - COMPLETE DATABASE */
/* ═══════════════════════════════════════════════════════════════ */

const VIO_MODELS = {
    // Vision & Image Models
    'pixtral-large': {
        name: 'Pixtral Large',
        category: 'vision',
        description: 'Image understanding',
        icon: '🖼️',
        speed: '⚡',
        quality: '⭐⭐⭐⭐⭐'
    },
    'gpt-5': {
        name: 'GPT-5',
        category: 'vision',
        description: 'Image understanding',
        icon: '🖼️',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐⭐'
    },
    'gemini-2.5-pro': {
        name: 'Gemini 2.5 Pro',
        category: 'agentic',
        description: 'Agentic AI usage',
        icon: '🤖',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐⭐'
    },
    'claude-4.5-sonnet': {
        name: 'Claude 4.5 Sonnet',
        category: 'vision',
        description: 'Advanced vision',
        icon: '👁️',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐⭐'
    },
    'claude-3.7-sonnet': {
        name: 'Claude 3.7 Sonnet',
        category: 'vision',
        description: 'Vision capable',
        icon: '👁️',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐'
    },
    'claude-3.5-sonnet': {
        name: 'Claude 3.5 Sonnet',
        category: 'general',
        description: 'Balanced',
        icon: '🎯',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐'
    },
    
    // Reasoning Models
    'deepseek-r1': {
        name: 'DeepSeek R1',
        category: 'reasoning',
        description: 'Deep reasoning',
        icon: '🧠',
        speed: '⚡',
        quality: '⭐⭐⭐⭐⭐'
    },
    'grok-4-fast-non-reasoning': {
        name: 'Grok-4-fast-non-reasoning',
        category: 'fast',
        description: 'Fast responses',
        icon: '⚡',
        speed: '⚡⚡⚡',
        quality: '⭐⭐⭐'
    },
    'phi-4-reasoning': {
        name: 'Phi-4-reasoning',
        category: 'reasoning',
        description: 'Reasoning focused',
        icon: '🧠',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐'
    },
    
    // Fast Models
    'gemini-2.0-flash': {
        name: 'Gemini 2.0 Flash',
        category: 'fast',
        description: 'Very fast',
        icon: '⚡',
        speed: '⚡⚡⚡',
        quality: '⭐⭐⭐'
    },
    'gpt-5-mini': {
        name: 'GPT 5-mini',
        category: 'fast',
        description: 'Fast GPT',
        icon: '⚡',
        speed: '⚡⚡⚡',
        quality: '⭐⭐⭐'
    },
    'gpt-5-nano': {
        name: 'GPT 5-nano',
        category: 'fast',
        description: 'Ultra fast',
        icon: '⚡',
        speed: '⚡⚡⚡⚡',
        quality: '⭐⭐'
    },
    'nova-lite': {
        name: 'Nova Lite',
        category: 'fast',
        description: 'Lightweight',
        icon: '⚡',
        speed: '⚡⚡⚡',
        quality: '⭐⭐'
    },
    'nova-micro': {
        name: 'Nova Micro',
        category: 'fast',
        description: 'Minimal',
        icon: '⚡',
        speed: '⚡⚡⚡⚡',
        quality: '⭐⭐'
    },
    
    // GPT Family
    'gpt-5-chat': {
        name: 'GPT 5-chat',
        category: 'general',
        description: 'Chat optimized',
        icon: '💬',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐'
    },
    'gpt-5-high': {
        name: 'GPT-5-high',
        category: 'general',
        description: 'High quality',
        icon: '⭐',
        speed: '⚡',
        quality: '⭐⭐⭐⭐⭐'
    },
    'gpt-5-low': {
        name: 'GPT-5-low',
        category: 'general',
        description: 'Low cost',
        icon: '💰',
        speed: '⚡⚡⚡',
        quality: '⭐⭐'
    },
    'gpt-5-medium': {
        name: 'GPT-5-medium',
        category: 'general',
        description: 'Balanced',
        icon: '⚖️',
        speed: '⚡⚡',
        quality: '⭐⭐⭐'
    },
    'gpt-4o': {
        name: 'GPT-4o',
        category: 'general',
        description: 'GPT-4 optimized',
        icon: '🎯',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐'
    },
    'gpt-3.5-turbo': {
        name: 'GPT-3.5 Turbo',
        category: 'fast',
        description: 'Fast and efficient',
        icon: '⚡',
        speed: '⚡⚡⚡',
        quality: '⭐⭐⭐'
    },
    'gpt-o3-mini': {
        name: 'GPT-o3-mini',
        category: 'fast',
        description: 'Compact GPT',
        icon: '⚡',
        speed: '⚡⚡⚡',
        quality: '⭐⭐'
    },
    'gpt-oss-120b': {
        name: 'GPT-OSS-120B',
        category: 'general',
        description: 'Open source',
        icon: '🔓',
        speed: '⚡⚡',
        quality: '⭐⭐⭐'
    },
    'gpt-oss-20b': {
        name: 'GPT-OSS-20B',
        category: 'general',
        description: 'Open source',
        icon: '🔓',
        speed: '⚡⚡',
        quality: '⭐⭐⭐'
    },
    'gpt-5.1': {
        name: 'Gpt-5.1',
        category: 'general',
        description: 'Latest GPT',
        icon: '🆕',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐'
    },
    
    // LLaMA Family
    'llama-3.1-8b': {
        name: 'LLaMA 3.1 8B',
        category: 'general',
        description: 'Efficient',
        icon: '🦙',
        speed: '⚡⚡⚡',
        quality: '⭐⭐⭐'
    },
    'llama3-405b': {
        name: 'Llama3 405B',
        category: 'general',
        description: 'Very large',
        icon: '🦙',
        speed: '⚡',
        quality: '⭐⭐⭐⭐⭐'
    },
    'meta-llama-3.3-70b': {
        name: 'Meta LLaMA 3.3 70B',
        category: 'general',
        description: "Meta's latest",
        icon: '🦙',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐'
    },
    
    // Mistral Family
    'mistral-large-2': {
        name: 'Mistral Large 2',
        category: 'general',
        description: 'Large model',
        icon: '🌪️',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐'
    },
    'mistral-large-2402': {
        name: 'Mistral Large 2402',
        category: 'general',
        description: 'Latest version',
        icon: '🌪️',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐'
    },
    
    // Nova Family
    'nova-premier': {
        name: 'Nova Premier',
        category: 'general',
        description: 'Premium model',
        icon: '⭐',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐'
    },
    'nova-pro-v1': {
        name: 'Nova Pro v1',
        category: 'general',
        description: 'Professional',
        icon: '💼',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐'
    },
    
    // Qwen Family
    'qwen-3.5-235b': {
        name: 'Qwen 3.5 235B',
        category: 'general',
        description: 'Very large Chinese model',
        icon: '🇨🇳',
        speed: '⚡',
        quality: '⭐⭐⭐⭐⭐'
    },
    'qwen3-coder-480b-a35b-v1': {
        name: 'Qwen3-coder-480b-a35b-v1',
        category: 'code',
        description: 'Coding specialist',
        icon: '💻',
        speed: '⚡',
        quality: '⭐⭐⭐⭐⭐'
    },
    
    // Other Models
    'mai-ds-r1': {
        name: 'MAI-DS-R1',
        category: 'general',
        description: 'Specialized model',
        icon: '🔬',
        speed: '⚡⚡',
        quality: '⭐⭐⭐'
    },
    'grok-3': {
        name: 'Grok-3',
        category: 'general',
        description: 'Grok model',
        icon: '🤖',
        speed: '⚡⚡',
        quality: '⭐⭐⭐⭐'
    }
};

const VIO_SCENARIOS = {
    'vision': 'pixtral-large',
    'agentic': 'gemini-2.5-pro',
    'fast': 'gemini-2.0-flash',
    'balanced': 'claude-4.5-sonnet',
    'reasoning': 'deepseek-r1'
};

function selectVIOScenario(scenarioName) {
    const modelKey = VIO_SCENARIOS[scenarioName];
    
    if (!modelKey) {
        showNotification('Unknown scenario', 'error');
        return;
    }
    
    document.getElementById('vioModelSelect').value = modelKey;
    updateVIOModelInfo(modelKey);
    showNotification(`Scenario: ${scenarioName}`, 'info');
}

function updateVIOModelInfo(modelKey) {
    const model = VIO_MODELS[modelKey];
    
    if (model) {
        document.getElementById('currentVIOModel').textContent = model.name;
        document.getElementById('vioModelCategory').textContent = model.category;
        document.getElementById('vioModelSpeed').textContent = model.speed;
        document.getElementById('vioModelQuality').textContent = model.quality;
        document.getElementById('vioModelDesc').textContent = model.description;
    }
}

async function applyVIOModelChange() {
    const modelKey = document.getElementById('vioModelSelect').value;
    const applyBtn = document.getElementById('applyVIOModelBtn');
    
    if (!modelKey) {
        showNotification('Please select a model', 'warning');
        return;
    }
    
    applyBtn.disabled = true;
    applyBtn.textContent = 'Applying...';
    
    try {
        const response = await fetch(`${state.settings.apiUrl}/api/model/switch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                vision_model: modelKey
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            updateVIOModelInfo(modelKey);
            
            const modelName = VIO_MODELS[modelKey]?.name || modelKey;
            showNotification(`✅ Switched to ${modelName}`, 'success');
            
            addLog('info', `VIO model switched to: ${modelName}`);
            
        } else {
            throw new Error(data.message || 'Failed to switch model');
        }
        
    } catch (error) {
        console.error('VIO model switch error:', error);
        showNotification(`❌ Failed to switch model: ${error.message}`, 'error');
        addLog('error', `VIO model switch failed: ${error.message}`);
    } finally {
        applyBtn.disabled = false;
        applyBtn.textContent = 'Apply Model Change';
    }
}

async function fetchCurrentVIOModel() {
    try {
        const response = await fetch(`${state.settings.apiUrl}/api/model/current`);
        const data = await response.json();
        
        if (data.success && data.current_model) {
            let modelKey = 'gemini-2.5-pro';
            
            for (const [key, model] of Object.entries(VIO_MODELS)) {
                if (model.name === data.current_model || key === data.current_model) {
                    modelKey = key;
                    break;
                }
            }
            
            document.getElementById('vioModelSelect').value = modelKey;
            updateVIOModelInfo(modelKey);
            
            const modelName = VIO_MODELS[modelKey]?.name || data.current_model;
            addLog('info', `Current VIO model: ${modelName}`);
        }
    } catch (error) {
        console.error('Failed to fetch current VIO model:', error);
    }
}

// Expose functions globally for inline onclick handlers
window.selectVIOScenario = selectVIOScenario;
window.applyVIOModelChange = applyVIOModelChange;
window.deleteVerificationImage = deleteVerificationImage;

/* ─────────────────────────────────────────────────────────────── */
/* Event Listener Setup */
/* ─────────────────────────────────────────────────────────────── */

function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Test Execution Handlers
    const runTestBtn = document.getElementById('run-test-btn');
    if (runTestBtn) {
        runTestBtn.addEventListener('click', async () => {
            const testId = document.getElementById('test-id-input').value.trim();
            
            if (!testId) {
                showNotification('Please enter a Test ID', 'warning');
                return;
            }
            
            const useLearned = document.getElementById('use-learned-checkbox').checked;
            const maxRetries = parseInt(document.getElementById('max-retries-input').value) || 3;
            
            try {
                await runTest(testId, { useLearned, maxRetries });
            } catch (error) {
                console.error('Run test error:', error);
            }
        });
    }
    
    const stopTestBtn = document.getElementById('stop-test-btn');
    if (stopTestBtn) {
        stopTestBtn.addEventListener('click', async () => {
            try {
                await stopExecution();
            } catch (error) {
                console.error('Stop execution error:', error);
            }
        });
    }
    
    // Standalone Command Handler
    const standaloneForm = document.getElementById('standalone-form');
    if (standaloneForm) {
        standaloneForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const command = document.getElementById('command-input').value.trim();
            
            if (!command) {
                showNotification('Please enter a command', 'warning');
                return;
            }
            
            try {
                await executeCommand(command);
                document.getElementById('command-input').value = '';
            } catch (error) {
                console.error('Execute command error:', error);
            }
        });
    }
    
    // Canvas Click-to-Tap
    const canvas = document.getElementById('screen-canvas');
    if (canvas) {
        canvas.addEventListener('click', async (event) => {
            const rect = canvas.getBoundingClientRect();
            
            if (!state.screenDimensions.width || !state.screenDimensions.height) {
                showNotification('No device connected', 'warning');
                return;
            }
            
            const scaleX = state.screenDimensions.width / rect.width;
            const scaleY = state.screenDimensions.height / rect.height;
            
            const x = Math.round((event.clientX - rect.left) * scaleX);
            const y = Math.round((event.clientY - rect.top) * scaleY);
            
            if (isNaN(x) || isNaN(y)) {
                showNotification('Invalid coordinates', 'error');
                return;
            }
            
            try {
                await tap(x, y);
                showCoordinates(x, y);
            } catch (error) {
                console.error('Tap error:', error);
            }
        });
        
        canvas.addEventListener('mousemove', (event) => {
            if (!state.screenDimensions.width || !state.screenDimensions.height) {
                updateCoordinateDisplay(0, 0);
                return;
            }
            
            const rect = canvas.getBoundingClientRect();
            
            const scaleX = state.screenDimensions.width / rect.width;
            const scaleY = state.screenDimensions.height / rect.height;
            
            const x = Math.round((event.clientX - rect.left) * scaleX);
            const y = Math.round((event.clientY - rect.top) * scaleY);
            
            if (!isNaN(x) && !isNaN(y)) {
                updateCoordinateDisplay(x, y);
            }
        });
    }
    
    // Device Control Handlers
    const pressBackBtn = document.getElementById('press-back-btn');
    if (pressBackBtn) {
        pressBackBtn.addEventListener('click', async () => {
            try {
                await pressBack();
            } catch (error) {
                console.error('Press back error:', error);
            }
        });
    }
    
    const pressHomeBtn = document.getElementById('press-home-btn');
    if (pressHomeBtn) {
        pressHomeBtn.addEventListener('click', async () => {
            try {
                await pressHome();
            } catch (error) {
                console.error('Press home error:', error);
            }
        });
    }
    
    const screenshotBtn = document.getElementById('screenshot-btn');
    if (screenshotBtn) {
        screenshotBtn.addEventListener('click', async () => {
            try {
                addLog('info', 'Capturing screenshot...');
                showNotification('Screenshot captured', 'success');
            } catch (error) {
                console.error('Screenshot error:', error);
            }
        });
    }
    
    const refreshDeviceBtn = document.getElementById('refresh-device-btn');
    if (refreshDeviceBtn) {
        refreshDeviceBtn.addEventListener('click', async () => {
            try {
                await getDeviceInfo();
                showNotification('Device info refreshed', 'success');
            } catch (error) {
                console.error('Refresh device error:', error);
            }
        });
    }
    
    // ═══════════════════════════════════════════════════════════
    // Device Coordinates Event Listeners
    // ═══════════════════════════════════════════════════════════
    
    const addCoordBtn = document.getElementById('add-coord-btn');
    if (addCoordBtn) {
        addCoordBtn.addEventListener('click', async () => {
            await addDeviceCoordinate();
        });
    }
    
    const viewCoordsBtn = document.getElementById('view-coords-btn');
    if (viewCoordsBtn) {
        viewCoordsBtn.addEventListener('click', async () => {
            await viewDeviceCoordinates();
        });
    }
    
    const deleteCoordBtn = document.getElementById('delete-coord-btn');
    if (deleteCoordBtn) {
        deleteCoordBtn.addEventListener('click', async () => {
            await deleteDeviceCoordinate();
        });
    }
    
    // ═══════════════════════════════════════════════════════════
    // Verification Images Event Listeners (NEW)
    // ═══════════════════════════════════════════════════════════
    
    const captureVerificationBtn = document.getElementById('capture-verification-btn');
    if (captureVerificationBtn) {
        captureVerificationBtn.addEventListener('click', async () => {
            await captureVerificationImage();
        });
    }
    
    const viewVerificationImagesBtn = document.getElementById('view-verification-images-btn');
    if (viewVerificationImagesBtn) {
        viewVerificationImagesBtn.addEventListener('click', async () => {
            await viewVerificationImages();
        });
    }
    
    // Preview modal click handler
    const previewModal = document.getElementById('verification-image-preview-modal');
    if (previewModal) {
        previewModal.addEventListener('click', () => {
            previewModal.style.display = 'none';
        });
    }
    
    // HITL Handler
    const sendGuidanceBtn = document.getElementById('send-guidance-btn');
    if (sendGuidanceBtn) {
        sendGuidanceBtn.addEventListener('click', async () => {
            const guidance = document.getElementById('guidance-input').value.trim();
            const xInput = document.getElementById('coord-x-input').value;
            const yInput = document.getElementById('coord-y-input').value;
            const actionType = document.getElementById('action-type-select').value;
            
            if (!guidance) {
                showNotification('Please enter guidance text', 'warning');
                return;
            }
            
            let coords = null;
            if (xInput && yInput) {
                coords = [parseInt(xInput), parseInt(yInput)];
            }
            
            try {
                await sendGuidance(guidance, coords, actionType);
                document.getElementById('guidance-input').value = '';
                document.getElementById('coord-x-input').value = '';
                document.getElementById('coord-y-input').value = '';
            } catch (error) {
                console.error('Send guidance error:', error);
            }
        });
    }
    
    // RAG Management Handlers
    const indexTestsBtn = document.getElementById('index-tests-btn');
    if (indexTestsBtn) {
        indexTestsBtn.addEventListener('click', async () => {
            try {
                addLog('info', 'Indexing test cases...');
                showNotification('Test indexing started', 'info');
            } catch (error) {
                console.error('Index tests error:', error);
            }
        });
    }
    
    const searchTestsBtn = document.getElementById('search-tests-btn');
    if (searchTestsBtn) {
        searchTestsBtn.addEventListener('click', async () => {
            const query = document.getElementById('search-tests-input').value.trim();
            
            if (!query) {
                showNotification('Please enter a search query', 'warning');
                return;
            }
            
            try {
                addLog('info', `Searching tests: ${query}`);
                showNotification('Search results will appear in logs', 'info');
            } catch (error) {
                console.error('Search tests error:', error);
            }
        });
    }
    
    const viewLearnedBtn = document.getElementById('view-learned-btn');
    if (viewLearnedBtn) {
        viewLearnedBtn.addEventListener('click', async () => {
            try {
                addLog('info', 'Fetching learned solutions...');
                showNotification('Learned solutions will appear in logs', 'info');
            } catch (error) {
                console.error('View learned error:', error);
            }
        });
    }
    
    // Log Control Handlers
    const clearLogsBtn = document.getElementById('clear-logs-btn');
    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', () => {
            clearLogs();
        });
    }
    
    const exportLogsBtn = document.getElementById('export-logs-btn');
    if (exportLogsBtn) {
        exportLogsBtn.addEventListener('click', () => {
            exportLogs();
        });
    }
    
    const logFilterSelect = document.getElementById('log-filter-select');
    if (logFilterSelect) {
        logFilterSelect.addEventListener('change', () => {
            filterLogs();
        });
    }
    
    // Stream Control
    const toggleStreamBtn = document.getElementById('toggle-stream-btn');
    if (toggleStreamBtn) {
        toggleStreamBtn.addEventListener('click', () => {
            if (state.streamActive) {
                disconnectWebSockets();
                showNotification('Stream stopped', 'info');
            } else {
                connectWebSockets();
                showNotification('Stream started', 'info');
            }
        });
    }
    
    // Modal Handlers
    const openSettingsBtn = document.getElementById('open-settings-btn');
    if (openSettingsBtn) {
        openSettingsBtn.addEventListener('click', () => {
            openModal('settings-modal');
        });
    }
    
    const openAboutBtn = document.getElementById('open-about-btn');
    if (openAboutBtn) {
        openAboutBtn.addEventListener('click', () => {
            openModal('about-modal');
        });
    }
    
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', () => {
            const apiUrl = document.getElementById('api-url-input').value;
            const streamFps = parseInt(document.getElementById('stream-fps-input').value);
            const autoScrollLogs = document.getElementById('auto-scroll-logs-checkbox').checked;
            const showCoordinates = document.getElementById('show-coordinates-checkbox').checked;
            
            state.settings.apiUrl = apiUrl;
            state.settings.streamFps = streamFps;
            state.settings.autoScrollLogs = autoScrollLogs;
            state.settings.showCoordinates = showCoordinates;
            
            saveSettings();
            
            closeModal('settings-modal');
        });
    }
    
    document.querySelectorAll('.modal-close, [data-modal]').forEach(element => {
        element.addEventListener('click', () => {
            const modalId = element.getAttribute('data-modal');
            if (modalId) {
                closeModal(modalId);
            }
        });
    });
    
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
    
    console.log('✅ Event listeners set up successfully');
}

/* ─────────────────────────────────────────────────────────────── */
/* Application Entry Point */
/* ─────────────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOM Content Loaded');
    
    try {
        await initApp();
        connectWebSockets();
        startStatusPolling();
        setupEventListeners();
        
        await fetchCurrentVIOModel();
        
        const modelSelect = document.getElementById('vioModelSelect');
        if (modelSelect) {
            modelSelect.addEventListener('change', (e) => {
                updateVIOModelInfo(e.target.value);
            });
        }
    } catch (error) {
        console.error('Failed to start application:', error);
        showNotification('Application startup failed', 'error');
    }
});