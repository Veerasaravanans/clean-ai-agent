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
    isPaused: false,
    
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
    verificationImages: [],

    // Excel Batch Test IDs
    excelFiles: [],
    excelTestIds: [],
    selectedExcelTestIds: []
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

    // Enable pause button when test starts
    updatePauseResumeButtons(true, false);

    const result = await apiRequest('/api/run-tests', 'POST', {
        test_ids: [testId],
        use_learned: useLearned,
        max_retries: maxRetries,
        verify_each_step: true
    });

    // Disable pause button when test ends
    updatePauseResumeButtons(false, false);

    if (result.success) {
        state.currentTest = testId;
        addLog('success', `Test completed: ${testId}`);
        showNotification('Test execution completed', 'success');
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
        state.isPaused = false;
        addLog('info', 'Execution stopped');
        showNotification('Execution stopped', 'info');
        updatePauseResumeButtons(false, false);
    }

    return result;
}

async function pauseExecution() {
    addLog('info', 'Pausing execution...');

    const result = await apiRequest('/api/pause', 'POST');

    if (result.success) {
        state.isPaused = true;
        addLog('warning', 'Execution paused');
        showNotification('Execution paused', 'warning');
        updatePauseResumeButtons(true, true);
    } else {
        showNotification(result.message || 'Cannot pause', 'error');
    }

    return result;
}

async function resumeExecution() {
    addLog('info', 'Resuming execution...');

    const result = await apiRequest('/api/resume', 'POST');

    if (result.success) {
        state.isPaused = false;
        addLog('success', 'Execution resumed');
        showNotification('Execution resumed', 'success');
        updatePauseResumeButtons(true, false);
    } else {
        showNotification(result.message || 'Cannot resume', 'error');
    }

    return result;
}

function updatePauseResumeButtons(isRunning, isPaused) {
    const pauseBtn = document.getElementById('pause-test-btn');
    const resumeBtn = document.getElementById('resume-test-btn');

    if (pauseBtn && resumeBtn) {
        if (!isRunning) {
            // Not running - hide both, disable pause
            pauseBtn.disabled = true;
            pauseBtn.style.display = '';
            resumeBtn.style.display = 'none';
        } else if (isPaused) {
            // Running and paused - show resume, hide pause
            pauseBtn.style.display = 'none';
            resumeBtn.style.display = '';
        } else {
            // Running and not paused - show pause, hide resume
            pauseBtn.disabled = false;
            pauseBtn.style.display = '';
            resumeBtn.style.display = 'none';
        }
    }
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
/* Utility Functions */
/* ─────────────────────────────────────────────────────────────── */

// Debounce utility for search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
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

async function fetchRAGStats() {
    try {
        const result = await apiRequest('/api/rag/stats');
        if (result.success && result.data) {
            state.ragStats.testCases = result.data.test_cases_count || 0;
            state.ragStats.learnedSolutions = result.data.learned_solutions_count || 0;

            // Update UI
            const testCountEl = document.getElementById('rag-test-count');
            const learnedCountEl = document.getElementById('rag-learned-count');

            if (testCountEl) {
                testCountEl.textContent = state.ragStats.testCases;
            }
            if (learnedCountEl) {
                learnedCountEl.textContent = state.ragStats.learnedSolutions;
            }

            console.log(`RAG Stats: ${state.ragStats.testCases} test cases, ${state.ragStats.learnedSolutions} learned solutions`);
        }
        return result;
    } catch (error) {
        console.error('Failed to fetch RAG stats:', error);
        return { success: false };
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

        // Load RAG stats
        await fetchRAGStats();

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

    // Pause button handler
    const pauseTestBtn = document.getElementById('pause-test-btn');
    if (pauseTestBtn) {
        pauseTestBtn.addEventListener('click', async () => {
            try {
                await pauseExecution();
            } catch (error) {
                console.error('Pause execution error:', error);
            }
        });
    }

    // Resume button handler
    const resumeTestBtn = document.getElementById('resume-test-btn');
    if (resumeTestBtn) {
        resumeTestBtn.addEventListener('click', async () => {
            try {
                await resumeExecution();
            } catch (error) {
                console.error('Resume execution error:', error);
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
                indexTestsBtn.disabled = true;
                indexTestsBtn.textContent = 'Indexing...';
                addLog('info', 'Indexing test cases from Excel files...');

                const response = await apiRequest('/api/rag/index', 'POST');
                if (response.success) {
                    addLog('success', `Indexed ${response.data.added} test cases from ${response.data.files} files`);
                    showNotification(response.message, 'success');
                    // Refresh stats
                    await fetchRAGStats();
                } else {
                    addLog('error', 'Failed to index test cases');
                    showNotification('Indexing failed', 'error');
                }
            } catch (error) {
                console.error('Index tests error:', error);
                addLog('error', `Indexing error: ${error.message}`);
            } finally {
                indexTestsBtn.disabled = false;
                indexTestsBtn.textContent = '📥 Index Test Cases';
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
                searchTestsBtn.disabled = true;
                addLog('info', `Searching for: ${query}`);

                // First try exact ID match, then semantic search
                const response = await apiRequest(`/api/rag/search?query=${encodeURIComponent(query)}&limit=10`);
                if (response.success && response.data) {
                    const results = response.data.results || [];
                    const exactMatch = response.data.exact_match;

                    if (exactMatch) {
                        // Show exact match in modal
                        showTestCaseModal(exactMatch);
                    } else if (results.length > 0) {
                        // Show search results in modal
                        showSearchResultsModal(results, query);
                    } else {
                        showNotification('No test cases found', 'warning');
                    }
                }
            } catch (error) {
                console.error('Search tests error:', error);
                addLog('error', `Search error: ${error.message}`);
            } finally {
                searchTestsBtn.disabled = false;
            }
        });
    }

    const viewLearnedBtn = document.getElementById('view-learned-btn');
    if (viewLearnedBtn) {
        viewLearnedBtn.addEventListener('click', async () => {
            try {
                viewLearnedBtn.disabled = true;

                const response = await apiRequest('/api/rag/learned');
                if (response.success && response.data.solutions) {
                    const solutions = response.data.solutions;
                    if (solutions.length === 0) {
                        showNotification('No learned solutions yet', 'warning');
                    } else {
                        // Show in modal
                        showLearnedSolutionsModal(solutions);
                    }
                }
            } catch (error) {
                console.error('View learned error:', error);
                addLog('error', `Error: ${error.message}`);
            } finally {
                viewLearnedBtn.disabled = false;
            }
        });
    }

    // ═══════════════════════════════════════════════════════════
    // Test History Dashboard Event Listeners (NEW)
    // ═══════════════════════════════════════════════════════════

    const openHistoryDashboardBtn = document.getElementById('open-history-dashboard-btn');
    if (openHistoryDashboardBtn) {
        openHistoryDashboardBtn.addEventListener('click', openHistoryDashboard);
    }

    const refreshHistoryBtn = document.getElementById('refresh-history-btn');
    if (refreshHistoryBtn) {
        refreshHistoryBtn.addEventListener('click', fetchHistorySummary);
    }

    const dashRefreshBtn = document.getElementById('dash-refresh-btn');
    if (dashRefreshBtn) {
        dashRefreshBtn.addEventListener('click', loadDashboardData);
    }

    const dashStatusFilter = document.getElementById('dash-status-filter');
    if (dashStatusFilter) {
        dashStatusFilter.addEventListener('change', (e) => {
            dashboardState.statusFilter = e.target.value;
            dashboardState.currentPage = 1;
            loadExecutionsTable();
        });
    }

    const dashTestFilter = document.getElementById('dash-test-filter');
    if (dashTestFilter) {
        dashTestFilter.addEventListener('input', debounce((e) => {
            dashboardState.testFilter = e.target.value;
            dashboardState.currentPage = 1;
            loadExecutionsTable();
        }, 500));
    }

    const dashPrevPage = document.getElementById('dash-prev-page');
    if (dashPrevPage) {
        dashPrevPage.addEventListener('click', () => {
            if (dashboardState.currentPage > 1) {
                dashboardState.currentPage--;
                loadExecutionsTable();
            }
        });
    }

    const dashNextPage = document.getElementById('dash-next-page');
    if (dashNextPage) {
        dashNextPage.addEventListener('click', () => {
            if (dashboardState.currentPage < dashboardState.totalPages) {
                dashboardState.currentPage++;
                loadExecutionsTable();
            }
        });
    }

    const deleteExecutionBtn = document.getElementById('delete-execution-btn');
    if (deleteExecutionBtn) {
        deleteExecutionBtn.addEventListener('click', () => {
            const executionId = deleteExecutionBtn.dataset.executionId;
            if (executionId) {
                deleteExecution(executionId);
            }
        });
    }

    // ═══════════════════════════════════════════════════════════
    // Reports Event Listeners (NEW)
    // ═══════════════════════════════════════════════════════════

    const reportFormatExcel = document.getElementById('report-format-excel');
    const reportFormatPdf = document.getElementById('report-format-pdf');

    if (reportFormatExcel) {
        reportFormatExcel.addEventListener('click', () => {
            reportsState.selectedFormat = 'excel';
            reportFormatExcel.classList.add('format-btn-active');
            if (reportFormatPdf) reportFormatPdf.classList.remove('format-btn-active');
        });
    }

    if (reportFormatPdf) {
        reportFormatPdf.addEventListener('click', () => {
            reportsState.selectedFormat = 'pdf';
            reportFormatPdf.classList.add('format-btn-active');
            if (reportFormatExcel) reportFormatExcel.classList.remove('format-btn-active');
        });
    }

    const generateReportBtn = document.getElementById('generate-report-btn');
    if (generateReportBtn) {
        generateReportBtn.addEventListener('click', generateReport);
    }

    const viewReportsBtn = document.getElementById('view-reports-btn');
    if (viewReportsBtn) {
        viewReportsBtn.addEventListener('click', openReportsList);
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

    // ═══════════════════════════════════════════════════════════
    // SSIM Verification Buttons Event Listeners
    // ═══════════════════════════════════════════════════════════

    const viewSSIMSuccessBtn = document.getElementById('view-ssim-success-btn');
    if (viewSSIMSuccessBtn) {
        viewSSIMSuccessBtn.addEventListener('click', viewSSIMSuccess);
    }

    const viewSSIMFailedBtn = document.getElementById('view-ssim-failed-btn');
    if (viewSSIMFailedBtn) {
        viewSSIMFailedBtn.addEventListener('click', viewSSIMFailed);
    }

    const viewSSIMComparisonsBtn = document.getElementById('view-ssim-comparisons-btn');
    if (viewSSIMComparisonsBtn) {
        viewSSIMComparisonsBtn.addEventListener('click', viewSSIMComparisons);
    }

    console.log('✅ Event listeners set up successfully');
}

/* ═══════════════════════════════════════════════════════════════ */
/* TEST HISTORY DASHBOARD FUNCTIONS */
/* ═══════════════════════════════════════════════════════════════ */

// Dashboard state
const dashboardState = {
    currentPage: 1,
    pageSize: 20,
    totalPages: 1,
    statusFilter: '',
    testFilter: '',
    trendChart: null,
    distributionChart: null
};

// Fetch history summary for sidebar panel
async function fetchHistorySummary() {
    try {
        const response = await apiRequest('/api/history/summary');
        if (response.success && response.data) {
            const data = response.data;

            // Update sidebar stats
            document.getElementById('history-total').textContent = data.total_executions || 0;
            document.getElementById('history-passed').textContent = data.total_passed || 0;
            document.getElementById('history-failed').textContent = data.total_failed || 0;

            const passRate = data.pass_rate || 0;
            document.getElementById('history-pass-rate-fill').style.width = `${passRate}%`;
            document.getElementById('history-pass-rate-text').textContent = `${passRate.toFixed(1)}%`;
        }
    } catch (error) {
        console.error('Error fetching history summary:', error);
    }
}

// Open dashboard modal and load data
async function openHistoryDashboard() {
    openModal('history-dashboard-modal');
    await loadDashboardData();
}

// Load all dashboard data
async function loadDashboardData() {
    try {
        // Fetch analytics
        const analyticsResponse = await apiRequest('/api/history/analytics');
        if (analyticsResponse.success && analyticsResponse.data) {
            updateDashboardSummary(analyticsResponse.data);
            updateDashboardCharts(analyticsResponse.data);
        }

        // Fetch executions table
        await loadExecutionsTable();

    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showNotification('Failed to load dashboard data', 'error');
    }
}

// Update dashboard summary cards
function updateDashboardSummary(analytics) {
    document.getElementById('dash-total-executions').textContent = analytics.total_executions || 0;
    document.getElementById('dash-total-passed').textContent = analytics.total_passed || 0;
    document.getElementById('dash-total-failed').textContent = analytics.total_failed || 0;
    document.getElementById('dash-pass-rate').textContent = `${(analytics.overall_pass_rate || 0).toFixed(1)}%`;
    document.getElementById('dash-ssim-rate').textContent = `${(analytics.ssim_pass_rate || 0).toFixed(1)}%`;
}

// Update dashboard charts
function updateDashboardCharts(analytics) {
    const dailyStats = analytics.daily_stats || [];

    // Prepare data for trend chart (reverse for chronological order)
    const reversedStats = [...dailyStats].reverse();
    const labels = reversedStats.map(d => d.date.substring(5)); // MM-DD format
    const passedData = reversedStats.map(d => d.passed);
    const failedData = reversedStats.map(d => d.failed);

    // Trend chart
    const trendCtx = document.getElementById('trend-chart');
    if (trendCtx) {
        if (dashboardState.trendChart) {
            dashboardState.trendChart.destroy();
        }

        dashboardState.trendChart = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Passed',
                        data: passedData,
                        borderColor: '#00ff88',
                        backgroundColor: 'rgba(0, 255, 136, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Failed',
                        data: failedData,
                        borderColor: '#ff4444',
                        backgroundColor: 'rgba(255, 68, 68, 0.1)',
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#b0b0b0' }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#7a7a8c' },
                        grid: { color: '#2a2a3e' }
                    },
                    y: {
                        ticks: { color: '#7a7a8c' },
                        grid: { color: '#2a2a3e' },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // Distribution chart
    const distCtx = document.getElementById('distribution-chart');
    if (distCtx) {
        if (dashboardState.distributionChart) {
            dashboardState.distributionChart.destroy();
        }

        dashboardState.distributionChart = new Chart(distCtx, {
            type: 'doughnut',
            data: {
                labels: ['Passed', 'Failed'],
                datasets: [{
                    data: [analytics.total_passed || 0, analytics.total_failed || 0],
                    backgroundColor: ['#00ff88', '#ff4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#b0b0b0' }
                    }
                }
            }
        });
    }
}

// Load executions table
async function loadExecutionsTable() {
    try {
        let endpoint = `/api/history/executions?page=${dashboardState.currentPage}&page_size=${dashboardState.pageSize}`;

        if (dashboardState.statusFilter) {
            endpoint += `&status=${dashboardState.statusFilter}`;
        }
        if (dashboardState.testFilter) {
            endpoint += `&test_id=${dashboardState.testFilter}`;
        }

        const response = await apiRequest(endpoint);

        if (response.success && response.data) {
            const data = response.data;
            dashboardState.totalPages = data.total_pages || 1;

            renderExecutionsTable(data.executions || []);
            updatePagination();
        }
    } catch (error) {
        console.error('Error loading executions table:', error);
    }
}

// Render executions table
function renderExecutionsTable(executions) {
    const tbody = document.getElementById('executions-table-body');
    if (!tbody) return;

    if (executions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state">
                    <div class="empty-state-icon">📋</div>
                    <div class="empty-state-text">No executions found</div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = executions.map(exec => {
        const duration = exec.duration_ms ? `${(exec.duration_ms / 1000).toFixed(1)}s` : '-';
        const steps = `${exec.passed_steps || 0}/${exec.total_steps || 0}`;
        const passRate = exec.pass_rate ? `${exec.pass_rate.toFixed(0)}%` : '-';
        const ssimRate = exec.ssim_pass_rate ? `${exec.ssim_pass_rate.toFixed(0)}%` : '-';
        const startTime = new Date(exec.started_at).toLocaleString();

        return `
            <tr>
                <td>${exec.test_id || '-'}</td>
                <td><span class="status-badge ${exec.status}">${exec.status}</span></td>
                <td>${startTime}</td>
                <td>${duration}</td>
                <td>${steps}</td>
                <td>${passRate}</td>
                <td>${ssimRate}</td>
                <td>
                    <button class="btn btn-small" onclick="viewExecutionDetail('${exec.execution_id}')">View</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Update pagination controls
function updatePagination() {
    const pageInfo = document.getElementById('dash-page-info');
    const prevBtn = document.getElementById('dash-prev-page');
    const nextBtn = document.getElementById('dash-next-page');

    if (pageInfo) {
        pageInfo.textContent = `Page ${dashboardState.currentPage} of ${dashboardState.totalPages}`;
    }

    if (prevBtn) {
        prevBtn.disabled = dashboardState.currentPage <= 1;
    }

    if (nextBtn) {
        nextBtn.disabled = dashboardState.currentPage >= dashboardState.totalPages;
    }
}

// View execution detail
async function viewExecutionDetail(executionId) {
    try {
        const response = await apiRequest(`/api/history/execution/${executionId}`);

        if (response.success && response.data) {
            renderExecutionDetail(response.data);
            openModal('execution-detail-modal');

            // Store current execution ID for delete
            document.getElementById('delete-execution-btn').dataset.executionId = executionId;
        }
    } catch (error) {
        console.error('Error loading execution detail:', error);
        showNotification('Failed to load execution details', 'error');
    }
}

// Render execution detail modal
function renderExecutionDetail(exec) {
    const content = document.getElementById('execution-detail-content');
    if (!content) return;

    const duration = exec.duration_ms ? `${(exec.duration_ms / 1000).toFixed(1)}s` : '-';
    const startTime = exec.started_at ? new Date(exec.started_at).toLocaleString() : '-';
    const endTime = exec.completed_at ? new Date(exec.completed_at).toLocaleString() : '-';

    let stepsHtml = '';
    if (exec.steps && exec.steps.length > 0) {
        stepsHtml = `
            <div class="steps-list">
                <h4>Steps</h4>
                ${exec.steps.map(step => `
                    <div class="step-item">
                        <div class="step-number">${step.step_number}</div>
                        <div class="step-content">
                            <div class="step-description">${step.description || step.action_type || 'Step'}</div>
                            <div class="step-meta">
                                Status: <span class="status-badge ${step.status}">${step.status}</span>
                                ${step.ssim_score ? ` | SSIM: ${step.ssim_score.toFixed(4)}` : ''}
                                ${step.duration_ms ? ` | ${step.duration_ms}ms` : ''}
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    content.innerHTML = `
        <div class="execution-detail-grid">
            <div class="detail-item">
                <div class="detail-label">Test ID</div>
                <div class="detail-value">${exec.test_id || '-'}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Status</div>
                <div class="detail-value"><span class="status-badge ${exec.status}">${exec.status}</span></div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Started</div>
                <div class="detail-value">${startTime}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Completed</div>
                <div class="detail-value">${endTime}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Duration</div>
                <div class="detail-value">${duration}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Steps</div>
                <div class="detail-value">${exec.passed_steps || 0} / ${exec.total_steps || 0}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">SSIM Verifications</div>
                <div class="detail-value">${exec.ssim_passed || 0} / ${exec.ssim_verifications || 0}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Average SSIM</div>
                <div class="detail-value">${exec.average_ssim ? exec.average_ssim.toFixed(4) : '-'}</div>
            </div>
        </div>
        ${stepsHtml}
        ${exec.errors && exec.errors.length > 0 ? `
            <div class="errors-section">
                <h4>Errors</h4>
                <ul>${exec.errors.map(e => `<li>${e}</li>`).join('')}</ul>
            </div>
        ` : ''}
    `;
}

// Delete execution
async function deleteExecution(executionId) {
    if (!confirm('Are you sure you want to delete this execution record?')) {
        return;
    }

    try {
        const response = await apiRequest(`/api/history/execution/${executionId}`, 'DELETE');

        if (response.success) {
            showNotification('Execution deleted', 'success');
            closeModal('execution-detail-modal');
            await loadExecutionsTable();
            await fetchHistorySummary();
        }
    } catch (error) {
        console.error('Error deleting execution:', error);
        showNotification('Failed to delete execution', 'error');
    }
}


/* ═══════════════════════════════════════════════════════════════ */
/* REPORTS GENERATION FUNCTIONS */
/* ═══════════════════════════════════════════════════════════════ */

// Reports state
const reportsState = {
    selectedFormat: 'excel',
    reports: []
};

// Generate report
async function generateReport() {
    const format = reportsState.selectedFormat;
    const includeSSIM = document.getElementById('report-include-ssim')?.checked || true;
    const includeCharts = document.getElementById('report-include-charts')?.checked || true;
    const includeScreenshots = document.getElementById('report-include-screenshots')?.checked || false;
    const dateFrom = document.getElementById('report-date-from')?.value || null;
    const dateTo = document.getElementById('report-date-to')?.value || null;

    try {
        showNotification('Generating report...', 'info');

        const response = await apiRequest('/api/reports/generate', 'POST', {
            format: format,
            include_ssim_details: includeSSIM,
            include_charts: includeCharts,
            include_screenshots: includeScreenshots,
            date_from: dateFrom,
            date_to: dateTo
        });

        if (response.success && response.data) {
            showNotification(`${format.toUpperCase()} report generated!`, 'success');

            // Refresh reports count
            await fetchReportsList();

            // Open report in new tab
            if (response.data.view_url) {
                window.open(state.settings.apiUrl + response.data.view_url, '_blank');
            }
        }
    } catch (error) {
        console.error('Error generating report:', error);
        showNotification('Failed to generate report', 'error');
    }
}

// Fetch reports list
async function fetchReportsList() {
    try {
        const response = await apiRequest('/api/reports/list');

        if (response.success && response.data) {
            reportsState.reports = response.data.reports || [];

            // Update count
            const countContainer = document.getElementById('reports-count-container');
            const countSpan = document.getElementById('reports-count');

            if (countContainer && countSpan) {
                countSpan.textContent = reportsState.reports.length;
                countContainer.style.display = reportsState.reports.length > 0 ? 'block' : 'none';
            }
        }
    } catch (error) {
        console.error('Error fetching reports list:', error);
    }
}

// Open reports list modal
async function openReportsList() {
    await fetchReportsList();
    renderReportsList();
    openModal('reports-list-modal');
}

// Render reports list
function renderReportsList() {
    const container = document.getElementById('reports-list');
    if (!container) return;

    if (reportsState.reports.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📄</div>
                <div class="empty-state-text">No reports generated yet</div>
            </div>
        `;
        return;
    }

    container.innerHTML = reportsState.reports.map(report => {
        const formatClass = report.format === 'excel' ? 'report-item-excel' : 'report-item-pdf';
        const formatIcon = report.format === 'excel' ? '📊' : '📑';
        const date = new Date(report.generated_at).toLocaleString();
        const size = report.file_size_bytes ? `${(report.file_size_bytes / 1024).toFixed(1)} KB` : '-';

        return `
            <div class="report-item ${formatClass}">
                <div class="report-info">
                    <div class="report-title">${formatIcon} ${report.title || 'Test Execution Report'}</div>
                    <div class="report-meta">
                        ${date} | ${report.executions_included} executions | ${size}
                    </div>
                </div>
                <div class="report-actions">
                    <button class="btn btn-small btn-primary" onclick="viewReport('${report.report_id}')">View</button>
                    <button class="btn btn-small" onclick="downloadReport('${report.report_id}')">Download</button>
                    <button class="btn btn-small btn-danger" onclick="deleteReport('${report.report_id}')">Delete</button>
                </div>
            </div>
        `;
    }).join('');
}

// View report
function viewReport(reportId) {
    window.open(`${state.settings.apiUrl}/api/reports/view/${reportId}`, '_blank');
}

// Download report
function downloadReport(reportId) {
    window.open(`${state.settings.apiUrl}/api/reports/download/${reportId}`, '_blank');
}

// Delete report
async function deleteReport(reportId) {
    if (!confirm('Are you sure you want to delete this report?')) {
        return;
    }

    try {
        const response = await apiRequest(`/api/reports/${reportId}`, 'DELETE');

        if (response.success) {
            showNotification('Report deleted', 'success');
            await fetchReportsList();
            renderReportsList();
        }
    } catch (error) {
        console.error('Error deleting report:', error);
        showNotification('Failed to delete report', 'error');
    }
}


/* ═══════════════════════════════════════════════════════════════ */
/* SSIM VERIFICATION RESULTS FUNCTIONS */
/* ═══════════════════════════════════════════════════════════════ */

// SSIM results state
const ssimResultsState = {
    activeTab: 'success',
    results: { success: [], error: [] }
};

// Fetch SSIM results
async function fetchSSIMResults() {
    try {
        const response = await apiRequest('/api/verification/results');

        if (response.success && response.data) {
            ssimResultsState.results = response.data.results || { success: [], error: [] };
            renderSSIMResults();
        }
    } catch (error) {
        console.error('Error fetching SSIM results:', error);
    }
}

// Render SSIM results in verification panel
function renderSSIMResults() {
    const container = document.getElementById('verification-results-list');
    if (!container) return;

    const results = ssimResultsState.results[ssimResultsState.activeTab] || [];

    if (results.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="padding: 20px;">
                <div class="empty-state-text">No ${ssimResultsState.activeTab} results</div>
            </div>
        `;
        return;
    }

    container.innerHTML = results.map(result => {
        const scoreClass = result.ssim_score >= 0.85 ? 'score-pass' : 'score-fail';
        const itemClass = ssimResultsState.activeTab === 'success' ? 'result-success' : 'result-error';
        const date = new Date(result.timestamp).toLocaleString();

        return `
            <div class="verification-result-item ${itemClass}" onclick="viewSSIMResult('${result.result_id}')">
                <div class="result-item-header">
                    <span class="result-test-id">${result.test_id}</span>
                    <span class="result-ssim-score ${scoreClass}">${result.ssim_score.toFixed(4)}</span>
                </div>
                <div class="result-item-meta">
                    Step ${result.step_number} | ${date}
                </div>
            </div>
        `;
    }).join('');
}

// View SSIM result detail
async function viewSSIMResult(resultId) {
    try {
        const response = await apiRequest(`/api/verification/result/${resultId}`);

        if (response.success && response.data) {
            renderSSIMComparison(response.data);
            openModal('ssim-comparison-modal');
        }
    } catch (error) {
        console.error('Error loading SSIM result:', error);
        showNotification('Failed to load result details', 'error');
    }
}

// Render SSIM comparison modal
function renderSSIMComparison(result) {
    const header = document.getElementById('ssim-result-header');
    const imageContainer = document.getElementById('comparison-image-container');
    const details = document.getElementById('ssim-result-details');

    if (header) {
        const scoreClass = result.passed ? 'ssim-score-pass' : 'ssim-score-fail';
        header.innerHTML = `
            <div class="ssim-header-item">
                <div class="ssim-header-label">Test ID</div>
                <div class="ssim-header-value">${result.test_id}</div>
            </div>
            <div class="ssim-header-item">
                <div class="ssim-header-label">Step</div>
                <div class="ssim-header-value">${result.step_number}</div>
            </div>
            <div class="ssim-header-item">
                <div class="ssim-header-label">SSIM Score</div>
                <div class="ssim-header-value ${scoreClass}">${result.ssim_score.toFixed(4)}</div>
            </div>
            <div class="ssim-header-item">
                <div class="ssim-header-label">Threshold</div>
                <div class="ssim-header-value">${result.threshold || 0.85}</div>
            </div>
            <div class="ssim-header-item">
                <div class="ssim-header-label">Result</div>
                <div class="ssim-header-value ${scoreClass}">${result.passed ? 'PASS' : 'FAIL'}</div>
            </div>
        `;
    }

    if (imageContainer) {
        const img = document.getElementById('ssim-comparison-image');
        if (img && result.comparison_image) {
            img.src = `${state.settings.apiUrl}/api/verification/comparison/${result.result_id}`;
            img.style.display = 'block';
        } else if (img) {
            img.style.display = 'none';
            imageContainer.innerHTML = '<div class="empty-state"><div class="empty-state-text">No comparison image available</div></div>';
        }
    }

    if (details) {
        details.innerHTML = `
            <p><strong>Description:</strong> ${result.step_description || '-'}</p>
            <p><strong>Timestamp:</strong> ${new Date(result.timestamp).toLocaleString()}</p>
            <p><strong>Device:</strong> ${result.device_id || '-'}</p>
        `;
    }
}


/* ═══════════════════════════════════════════════════════════════ */
/* UI ENHANCEMENTS - PHASE 15-16 */
/* Sidebar Toggle, Panel Collapse, Keyboard Shortcuts, Animations */
/* ═══════════════════════════════════════════════════════════════ */

// UI State
const uiState = {
    sidebarCollapsed: false,
    collapsedPanels: new Set(),
    connectionStartTime: Date.now()
};

// ═══════════════════════════════════════════════════════════════
// Sidebar Toggle Functionality
// ═══════════════════════════════════════════════════════════════

function initSidebarToggle() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');
    const toggleIcon = document.getElementById('sidebar-toggle-icon');

    if (!sidebar || !toggleBtn) return;

    // Load saved state
    const savedState = localStorage.getItem('sidebarCollapsed');
    if (savedState === 'true') {
        sidebar.classList.add('collapsed');
        uiState.sidebarCollapsed = true;
        if (toggleIcon) toggleIcon.textContent = '☰';
    }

    toggleBtn.addEventListener('click', () => {
        toggleSidebar();
    });
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleIcon = document.getElementById('sidebar-toggle-icon');

    if (!sidebar) return;

    sidebar.classList.toggle('collapsed');
    uiState.sidebarCollapsed = sidebar.classList.contains('collapsed');

    if (toggleIcon) {
        toggleIcon.textContent = uiState.sidebarCollapsed ? '☰' : '✕';
    }

    // Save state
    localStorage.setItem('sidebarCollapsed', uiState.sidebarCollapsed);
}

// ═══════════════════════════════════════════════════════════════
// Panel Accordion Functionality
// ═══════════════════════════════════════════════════════════════

function initPanelCollapse() {
    const panels = document.querySelectorAll('.panel[data-panel]');

    // Load saved collapsed panels
    const savedPanels = localStorage.getItem('collapsedPanels');
    if (savedPanels) {
        try {
            const parsed = JSON.parse(savedPanels);
            uiState.collapsedPanels = new Set(parsed);
        } catch (e) {
            console.error('Error loading collapsed panels:', e);
        }
    }

    panels.forEach(panel => {
        const header = panel.querySelector('.panel-header');
        const panelId = panel.getAttribute('data-panel');

        if (!header || !panelId) return;

        // Apply saved collapsed state
        if (uiState.collapsedPanels.has(panelId)) {
            panel.classList.add('collapsed');
        }

        header.addEventListener('click', (e) => {
            // Don't toggle if clicking on buttons inside header
            if (e.target.closest('button')) return;

            togglePanel(panel, panelId);
        });
    });
}

function togglePanel(panel, panelId) {
    panel.classList.toggle('collapsed');

    if (panel.classList.contains('collapsed')) {
        uiState.collapsedPanels.add(panelId);
    } else {
        uiState.collapsedPanels.delete(panelId);
    }

    // Save state
    localStorage.setItem('collapsedPanels', JSON.stringify([...uiState.collapsedPanels]));
}

// ═══════════════════════════════════════════════════════════════
// Keyboard Shortcuts
// ═══════════════════════════════════════════════════════════════

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl+B: Toggle sidebar
        if (e.ctrlKey && e.key === 'b') {
            e.preventDefault();
            toggleSidebar();
        }

        // Ctrl+L: Clear logs
        if (e.ctrlKey && e.key === 'l') {
            e.preventDefault();
            clearLogs();
        }

        // Escape: Close modals
        if (e.key === 'Escape') {
            const activeModal = document.querySelector('.modal.active');
            if (activeModal) {
                activeModal.classList.remove('active');
            }
        }
    });
}

// Clear logs function
function clearLogs() {
    const logContainer = document.getElementById('execution-log');
    if (logContainer) {
        logContainer.innerHTML = `
            <div class="log-entry log-info" data-category="system">
                <span class="log-time">${formatTime(new Date())}</span>
                <span class="log-level">INFO</span>
                <span class="log-message">Logs cleared. System ready.</span>
            </div>
        `;
        state.logs = [];
        showNotification('Logs cleared', 'info');
    }
}

// ═══════════════════════════════════════════════════════════════
// Number Animation for Stats
// ═══════════════════════════════════════════════════════════════

function animateNumber(element, targetValue, duration = 500) {
    if (!element) return;

    const startValue = parseInt(element.textContent) || 0;
    const startTime = performance.now();
    const isPercentage = element.textContent.includes('%');

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function (ease-out)
        const easeOut = 1 - Math.pow(1 - progress, 3);

        const currentValue = Math.round(startValue + (targetValue - startValue) * easeOut);
        element.textContent = isPercentage ? `${currentValue}%` : currentValue;

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            // Add pop animation
            element.classList.add('animating');
            setTimeout(() => element.classList.remove('animating'), 300);
        }
    }

    requestAnimationFrame(update);
}

// Update stat with animation
function updateStatWithAnimation(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        const numValue = typeof value === 'string' ? parseInt(value) : value;
        if (!isNaN(numValue)) {
            animateNumber(element, numValue);
        } else {
            element.textContent = value;
        }
    }
}

// ═══════════════════════════════════════════════════════════════
// Enhanced Notifications with Auto-dismiss
// ═══════════════════════════════════════════════════════════════

function showEnhancedNotification(message, type = 'info', duration = 5000) {
    const container = document.getElementById('notification-container');
    if (!container) return;

    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <span class="notification-icon">${icons[type] || icons.info}</span>
        <div class="notification-content">
            <div class="notification-message">${message}</div>
        </div>
        <button class="notification-close">&times;</button>
        <div class="notification-progress">
            <div class="notification-progress-fill"></div>
        </div>
    `;

    container.appendChild(notification);

    // Close button handler
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        notification.style.animation = 'slideOutRight 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    });

    // Auto-dismiss
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease forwards';
            setTimeout(() => notification.remove(), 300);
        }
    }, duration);
}

// ═══════════════════════════════════════════════════════════════
// Log Entry Click to Copy
// ═══════════════════════════════════════════════════════════════

function initLogCopy() {
    const logContainer = document.getElementById('execution-log');
    if (!logContainer) return;

    logContainer.addEventListener('click', (e) => {
        const logEntry = e.target.closest('.log-entry');
        if (logEntry) {
            const message = logEntry.querySelector('.log-message')?.textContent || '';
            const time = logEntry.querySelector('.log-time')?.textContent || '';
            const level = logEntry.querySelector('.log-level')?.textContent || '';

            const fullLog = `[${time}] [${level}] ${message}`;

            navigator.clipboard.writeText(fullLog).then(() => {
                showNotification('Log copied to clipboard', 'success');
            }).catch(err => {
                console.error('Failed to copy:', err);
            });
        }
    });
}

// ═══════════════════════════════════════════════════════════════
// Report Format Selector
// ═══════════════════════════════════════════════════════════════

function initReportFormatSelector() {
    const excelBtn = document.getElementById('report-format-excel');
    const pdfBtn = document.getElementById('report-format-pdf');

    if (excelBtn && pdfBtn) {
        excelBtn.addEventListener('click', () => {
            excelBtn.classList.add('format-btn-active');
            pdfBtn.classList.remove('format-btn-active');
            reportsState.selectedFormat = 'excel';
        });

        pdfBtn.addEventListener('click', () => {
            pdfBtn.classList.add('format-btn-active');
            excelBtn.classList.remove('format-btn-active');
            reportsState.selectedFormat = 'pdf';
        });
    }
}

// ═══════════════════════════════════════════════════════════════
// Connection Time Tracker
// ═══════════════════════════════════════════════════════════════

function initConnectionTimer() {
    const connectionTimeEl = document.getElementById('connection-time');
    if (!connectionTimeEl) return;

    uiState.connectionStartTime = Date.now();

    setInterval(() => {
        const elapsed = Math.floor((Date.now() - uiState.connectionStartTime) / 1000);
        const hours = Math.floor(elapsed / 3600);
        const minutes = Math.floor((elapsed % 3600) / 60);
        const seconds = elapsed % 60;

        let timeStr = '';
        if (hours > 0) {
            timeStr = `${hours}h ${minutes}m`;
        } else if (minutes > 0) {
            timeStr = `${minutes}m ${seconds}s`;
        } else {
            timeStr = `${seconds}s`;
        }

        connectionTimeEl.textContent = `Connected: ${timeStr}`;
    }, 1000);
}

// ═══════════════════════════════════════════════════════════════
// Fullscreen Toggle for Canvas
// ═══════════════════════════════════════════════════════════════

function initFullscreenToggle() {
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    const canvasContainer = document.querySelector('.canvas-container');

    if (fullscreenBtn && canvasContainer) {
        fullscreenBtn.addEventListener('click', () => {
            if (!document.fullscreenElement) {
                canvasContainer.requestFullscreen().catch(err => {
                    console.error('Fullscreen error:', err);
                });
            } else {
                document.exitFullscreen();
            }
        });
    }
}

// ═══════════════════════════════════════════════════════════════
// Initialize All UI Enhancements
// ═══════════════════════════════════════════════════════════════

function initUIEnhancements() {
    console.log('Initializing UI enhancements...');

    initSidebarToggle();
    initPanelCollapse();
    initKeyboardShortcuts();
    initLogCopy();
    initReportFormatSelector();
    initConnectionTimer();
    initFullscreenToggle();

    console.log('✅ UI enhancements initialized');
}

/* ═══════════════════════════════════════════════════════════════ */
/* SSIM VERIFICATION RESULTS FUNCTIONS */
/* ═══════════════════════════════════════════════════════════════ */

// View Success SSIM Results
async function viewSSIMSuccess() {
    const btn = document.getElementById('view-ssim-success-btn');
    const container = document.getElementById('ssim-results-container');

    // Toggle active state
    document.querySelectorAll('.ssim-buttons-group .btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    container.style.display = 'block';

    // Fetch results
    const response = await apiRequest('/api/verification/results?category=success');
    if (response.success) {
        renderSSIMResultsList(response.data.results.success || [], 'success');
    }
}

// View Failed SSIM Results
async function viewSSIMFailed() {
    const btn = document.getElementById('view-ssim-failed-btn');
    const container = document.getElementById('ssim-results-container');

    document.querySelectorAll('.ssim-buttons-group .btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    container.style.display = 'block';

    const response = await apiRequest('/api/verification/results?category=error');
    if (response.success) {
        renderSSIMResultsList(response.data.results.error || [], 'failed');
    }
}

// View All Comparisons (from data/verification_comparisons/ folder)
async function viewSSIMComparisons() {
    const btn = document.getElementById('view-ssim-comparisons-btn');
    const container = document.getElementById('ssim-results-container');

    document.querySelectorAll('.ssim-buttons-group .btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    container.style.display = 'block';

    // Fetch comparison images from the folder
    const response = await apiRequest('/api/verification/comparisons');
    if (response.success) {
        renderComparisonImagesList(response.data.images || []);
    }
}

// Render comparison images list (from folder)
function renderComparisonImagesList(images) {
    const list = document.getElementById('ssim-results-list');

    if (images.length === 0) {
        list.innerHTML = `<div style="padding: 20px; text-align: center; color: var(--text-muted);">
            No comparison images found
        </div>`;
        return;
    }

    list.innerHTML = images.map(img => {
        return `
            <div class="ssim-result-item comparison-item" onclick="viewComparisonImageFromFolder('${img.filename}')">
                <div class="ssim-result-header">
                    <span class="ssim-result-test-id">📷 ${img.filename}</span>
                    <span class="ssim-result-score">${img.size_kb} KB</span>
                </div>
                <div class="ssim-result-meta">${img.timestamp}</div>
            </div>
        `;
    }).join('');
}

// View comparison image from folder
async function viewComparisonImageFromFolder(filename) {
    const modal = document.getElementById('verification-image-preview-modal');
    const img = document.getElementById('verification-preview-image');
    const name = document.getElementById('verification-preview-name');

    img.src = `${state.settings.apiUrl}/api/verification/comparisons/${filename}`;
    name.textContent = filename;
    modal.style.display = 'flex';
}

// Render SSIM Results List with step info
function renderSSIMResultsList(results, type) {
    const list = document.getElementById('ssim-results-list');

    if (results.length === 0) {
        list.innerHTML = `<div style="padding: 20px; text-align: center; color: var(--text-muted);">
            No ${type === 'all' ? 'comparison' : type} results found
        </div>`;
        return;
    }

    list.innerHTML = results.map(r => {
        const passed = r.ssim_score >= 0.85;
        const statusClass = passed ? 'success' : 'failed';
        const scoreClass = passed ? 'pass' : 'fail';
        const icon = passed ? '✅' : '❌';
        const date = new Date(r.timestamp).toLocaleString();

        return `
            <div class="ssim-result-item ${statusClass}" onclick="viewSSIMComparison('${r.result_id}')">
                <div class="ssim-result-header">
                    <span class="ssim-result-test-id">${icon} ${r.test_id}</span>
                    <span class="ssim-result-score ${scoreClass}">${r.ssim_score.toFixed(4)}</span>
                </div>
                <div class="ssim-result-step">Step ${r.step_number}${r.step_description ? ': ' + r.step_description : ''}</div>
                <div class="ssim-result-meta">${date}</div>
            </div>
        `;
    }).join('');
}

// View individual comparison image (use existing modal)
async function viewSSIMComparison(resultId) {
    const response = await apiRequest(`/api/verification/result/${resultId}`);
    if (response.success && response.data) {
        const result = response.data;
        // Display in preview modal similar to verification images
        const modal = document.getElementById('verification-image-preview-modal');
        const img = document.getElementById('verification-preview-image');
        const name = document.getElementById('verification-preview-name');

        img.src = `/api/verification/comparison/${resultId}`;
        name.textContent = `Step ${result.step_number}: ${result.step_description || result.test_id} (SSIM: ${result.ssim_score.toFixed(4)})`;
        modal.style.display = 'flex';
    }
}

/* ═══════════════════════════════════════════════════════════════ */
/* RAG MODAL FUNCTIONS */
/* ═══════════════════════════════════════════════════════════════ */

// Close RAG modal
function closeRAGModal() {
    const modal = document.getElementById('rag-results-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Show learned solutions in modal
function showLearnedSolutionsModal(solutions) {
    const modal = document.getElementById('rag-results-modal');
    const title = document.getElementById('rag-modal-title');
    const body = document.getElementById('rag-modal-body');

    if (!modal || !title || !body) return;

    title.textContent = `Learned Solutions (${solutions.length})`;

    if (solutions.length === 0) {
        body.innerHTML = `
            <div class="rag-empty-state">
                <div class="rag-empty-state-icon">📚</div>
                <p>No learned solutions yet</p>
                <p style="font-size: 12px;">Run tests to build the knowledge base</p>
            </div>
        `;
    } else {
        body.innerHTML = solutions.map(s => `
            <div class="rag-result-item" onclick="viewLearnedSolutionDetail('${s.test_id}')">
                <div class="rag-result-header">
                    <span class="rag-result-id">${s.test_id}</span>
                    <span class="rag-result-badge success">${(s.success_rate * 100).toFixed(0)}% Success</span>
                </div>
                <div class="rag-result-title">${s.title || 'No title'}</div>
                <div class="rag-result-meta">
                    <span>📋 ${s.step_count} steps</span>
                    <span>🔄 ${s.execution_count} runs</span>
                    <span>🏷️ ${s.component || 'N/A'}</span>
                    ${s.last_execution ? `<span>🕐 ${new Date(s.last_execution).toLocaleDateString()}</span>` : ''}
                </div>
            </div>
        `).join('');
    }

    modal.style.display = 'flex';
}

// Show test case details in modal
function showTestCaseModal(testCase) {
    const modal = document.getElementById('rag-results-modal');
    const title = document.getElementById('rag-modal-title');
    const body = document.getElementById('rag-modal-body');

    if (!modal || !title || !body) return;

    title.textContent = `Test Case: ${testCase.test_id}`;

    const steps = testCase.steps || [];

    body.innerHTML = `
        <div class="rag-result-item">
            <div class="rag-result-header">
                <span class="rag-result-id">${testCase.test_id}</span>
                <span class="rag-result-badge match">Exact Match</span>
            </div>
            <div class="rag-result-title">${testCase.title || 'No title'}</div>
            <div class="rag-result-meta">
                <span>🏷️ ${testCase.component || 'N/A'}</span>
                <span>📋 ${steps.length} steps</span>
            </div>
            ${testCase.description ? `<p style="margin-top: 12px; color: var(--text-muted); font-size: 13px;">${testCase.description}</p>` : ''}
            ${steps.length > 0 ? `
                <div class="rag-result-steps">
                    <div class="rag-result-steps-title">Test Steps:</div>
                    ${steps.map((step, i) => `<div class="rag-result-step" data-step="${i + 1}.">${step}</div>`).join('')}
                </div>
            ` : ''}
            ${testCase.expected ? `
                <div class="rag-result-steps" style="margin-top: 12px;">
                    <div class="rag-result-steps-title">Expected Result:</div>
                    <p style="color: var(--text-muted); font-size: 13px; margin: 0;">${testCase.expected}</p>
                </div>
            ` : ''}
        </div>
    `;

    modal.style.display = 'flex';
}

// Show search results in modal
function showSearchResultsModal(results, query) {
    const modal = document.getElementById('rag-results-modal');
    const title = document.getElementById('rag-modal-title');
    const body = document.getElementById('rag-modal-body');

    if (!modal || !title || !body) return;

    title.textContent = `Search Results for "${query}" (${results.length})`;

    if (results.length === 0) {
        body.innerHTML = `
            <div class="rag-empty-state">
                <div class="rag-empty-state-icon">🔍</div>
                <p>No matching test cases found</p>
            </div>
        `;
    } else {
        body.innerHTML = results.map(r => `
            <div class="rag-result-item" onclick="showTestCaseModal(${JSON.stringify(r).replace(/"/g, '&quot;')})">
                <div class="rag-result-header">
                    <span class="rag-result-id">${r.test_id}</span>
                    <span class="rag-result-badge match">${(r.similarity * 100).toFixed(0)}% Match</span>
                </div>
                <div class="rag-result-title">${r.title || 'No title'}</div>
                <div class="rag-result-meta">
                    <span>🏷️ ${r.component || 'N/A'}</span>
                    <span>📋 ${(r.steps || []).length} steps</span>
                </div>
            </div>
        `).join('');
    }

    modal.style.display = 'flex';
}

// View learned solution detail
async function viewLearnedSolutionDetail(testId) {
    try {
        const response = await apiRequest(`/api/rag/learned/${testId}`);
        if (response.success && response.data) {
            const solution = response.data;
            const modal = document.getElementById('rag-results-modal');
            const title = document.getElementById('rag-modal-title');
            const body = document.getElementById('rag-modal-body');

            title.textContent = `Learned Solution: ${testId}`;

            const steps = solution.steps || [];

            body.innerHTML = `
                <div class="rag-result-item">
                    <div class="rag-result-header">
                        <span class="rag-result-id">${solution.test_id}</span>
                        <span class="rag-result-badge success">${(solution.success_rate * 100).toFixed(0)}% Success</span>
                    </div>
                    <div class="rag-result-title">${solution.title || 'No title'}</div>
                    <div class="rag-result-meta">
                        <span>🏷️ ${solution.component || 'N/A'}</span>
                        <span>📋 ${steps.length} steps</span>
                        <span>🔄 ${solution.execution_count || 0} runs</span>
                    </div>
                    ${steps.length > 0 ? `
                        <div class="rag-result-steps">
                            <div class="rag-result-steps-title">Learned Steps (with coordinates):</div>
                            ${steps.map((step, i) => `
                                <div class="rag-result-step" data-step="${i + 1}.">
                                    ${step.action || 'action'} on "${step.target || 'target'}"
                                    ${step.coordinates ? ` at (${step.coordinates[0]}, ${step.coordinates[1]})` : ''}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                    <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--glass-border);">
                        <button class="btn btn-primary" onclick="document.getElementById('test-id-input').value='${testId}'; closeRAGModal(); showNotification('Test ID loaded', 'success');">
                            📥 Load Test ID
                        </button>
                    </div>
                </div>
            `;

            modal.style.display = 'flex';
        }
    } catch (error) {
        console.error('Failed to load learned solution:', error);
        showNotification('Failed to load solution details', 'error');
    }
}

// Close modal on background click
document.addEventListener('click', (e) => {
    const modal = document.getElementById('rag-results-modal');
    if (modal && e.target === modal) {
        closeRAGModal();
    }
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeRAGModal();
    }
});

// Expose functions globally
window.toggleSidebar = toggleSidebar;
window.clearLogs = clearLogs;
window.viewExecutionDetail = viewExecutionDetail;
window.viewSSIMResult = viewSSIMResult;
window.viewSSIMComparison = viewSSIMComparison;
window.viewComparisonImageFromFolder = viewComparisonImageFromFolder;
window.closeRAGModal = closeRAGModal;
window.showLearnedSolutionsModal = showLearnedSolutionsModal;
window.showTestCaseModal = showTestCaseModal;
window.showSearchResultsModal = showSearchResultsModal;
window.viewLearnedSolutionDetail = viewLearnedSolutionDetail;

/* ─────────────────────────────────────────────────────────────── */
/* Excel Batch Functions */
/* ─────────────────────────────────────────────────────────────── */

async function loadExcelFiles() {
    try {
        const result = await apiRequest('/api/excel/files', 'GET');

        if (result.success) {
            state.excelFiles = result.files || [];
            updateExcelFileSelect();
            addLog('info', `Loaded ${state.excelFiles.length} Excel files`);
        }

        return result;
    } catch (error) {
        console.error('Load Excel files error:', error);
        showNotification('Failed to load Excel files', 'error');
        throw error;
    }
}

function updateExcelFileSelect() {
    const select = document.getElementById('excel-file-select');
    if (!select) return;

    select.innerHTML = '';

    if (state.excelFiles.length === 0) {
        const option = document.createElement('option');
        option.textContent = 'No Excel files found';
        option.disabled = true;
        select.appendChild(option);
        return;
    }

    state.excelFiles.forEach(file => {
        const option = document.createElement('option');
        option.value = file.file_name;
        const sizeKB = Math.round(file.file_size / 1024);
        option.textContent = `${file.file_name} (${sizeKB} KB)`;
        option.title = `Modified: ${file.modified_date}`;
        select.appendChild(option);
    });
}

async function loadTestIdsFromExcel() {
    const select = document.getElementById('excel-file-select');
    if (!select) return;

    const selectedFiles = Array.from(select.selectedOptions).map(opt => opt.value);

    if (selectedFiles.length === 0) {
        showNotification('Please select at least one Excel file', 'warning');
        return;
    }

    try {
        addLog('info', `Loading test IDs from ${selectedFiles.length} file(s)...`);

        const result = await apiRequest('/api/excel/extract-ids', 'POST', {
            file_names: selectedFiles
        });

        if (result.success) {
            state.excelTestIds = result.all_test_ids || [];
            updateExcelPreview();
            updateRunExcelButton();

            addLog('success', `Loaded ${state.excelTestIds.length} test IDs from ${selectedFiles.length} file(s)`);
            showNotification(`Loaded ${state.excelTestIds.length} test IDs`, 'success');
        }

        return result;
    } catch (error) {
        console.error('Load test IDs error:', error);
        showNotification('Failed to load test IDs', 'error');
        throw error;
    }
}

function updateExcelPreview() {
    const container = document.getElementById('excel-preview-container');
    const countEl = document.getElementById('excel-preview-count');
    const listEl = document.getElementById('excel-preview-list');

    if (!container || !countEl || !listEl) return;

    if (state.excelTestIds.length === 0) {
        container.style.display = 'none';
        state.selectedExcelTestIds = [];
        updateExcelSelectionCount();
        return;
    }

    container.style.display = 'block';
    countEl.textContent = `${state.excelTestIds.length} test IDs loaded`;

    listEl.innerHTML = '';
    state.excelTestIds.forEach((testId, index) => {
        const item = document.createElement('label');
        item.className = 'excel-preview-item';
        item.setAttribute('data-test-id', testId);

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `excel-test-${index}`;
        checkbox.value = testId;
        checkbox.checked = state.selectedExcelTestIds.includes(testId);
        checkbox.addEventListener('change', () => handleExcelTestIdToggle(testId, checkbox.checked));

        const span = document.createElement('span');
        span.textContent = testId;

        item.appendChild(checkbox);
        item.appendChild(span);
        listEl.appendChild(item);
    });

    // Select all by default on first load
    if (state.selectedExcelTestIds.length === 0) {
        selectAllExcelTestIds();
    }

    updateExcelSelectionCount();
}

function handleExcelTestIdToggle(testId, isChecked) {
    if (isChecked) {
        if (!state.selectedExcelTestIds.includes(testId)) {
            state.selectedExcelTestIds.push(testId);
        }
    } else {
        state.selectedExcelTestIds = state.selectedExcelTestIds.filter(id => id !== testId);
    }
    updateExcelSelectionCount();
    updateRunExcelButtons();
}

function selectAllExcelTestIds() {
    state.selectedExcelTestIds = [...state.excelTestIds];
    const checkboxes = document.querySelectorAll('#excel-preview-list input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = true);
    updateExcelSelectionCount();
    updateRunExcelButtons();
}

function deselectAllExcelTestIds() {
    state.selectedExcelTestIds = [];
    const checkboxes = document.querySelectorAll('#excel-preview-list input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);
    updateExcelSelectionCount();
    updateRunExcelButtons();
}

function updateExcelSelectionCount() {
    const countEl = document.getElementById('excel-selected-count');
    if (countEl) {
        countEl.textContent = `${state.selectedExcelTestIds.length} selected`;
    }
}

function updateRunExcelButton() {
    updateRunExcelButtons();
}

function updateRunExcelButtons() {
    const runAllBtn = document.getElementById('run-excel-tests-btn');
    const runSelectedBtn = document.getElementById('run-excel-selected-btn');

    if (runAllBtn) {
        runAllBtn.disabled = state.excelTestIds.length === 0;
        runAllBtn.textContent = state.excelTestIds.length > 0
            ? `Run All (${state.excelTestIds.length})`
            : 'Run All';
    }

    if (runSelectedBtn) {
        runSelectedBtn.disabled = state.selectedExcelTestIds.length === 0;
        runSelectedBtn.textContent = state.selectedExcelTestIds.length > 0
            ? `Run Selected (${state.selectedExcelTestIds.length})`
            : 'Run Selected';
    }
}

function clearExcelPreview() {
    state.excelTestIds = [];
    state.selectedExcelTestIds = [];
    updateExcelPreview();
    updateRunExcelButtons();
    addLog('info', 'Cleared Excel test IDs');
}

async function runExcelTests() {
    if (state.excelTestIds.length === 0) {
        showNotification('No test IDs loaded', 'warning');
        return;
    }

    await executeExcelTests(state.excelTestIds, 'all');
}

async function runSelectedExcelTests() {
    if (state.selectedExcelTestIds.length === 0) {
        showNotification('No test IDs selected', 'warning');
        return;
    }

    await executeExcelTests(state.selectedExcelTestIds, 'selected');
}

async function executeExcelTests(testIds, mode) {
    try {
        const useLearned = document.getElementById('use-learned-checkbox')?.checked ?? true;
        const maxRetries = parseInt(document.getElementById('max-retries-input')?.value) || 3;

        const modeLabel = mode === 'selected' ? 'selected' : 'all';
        addLog('info', `Starting batch execution of ${testIds.length} ${modeLabel} tests...`);
        showNotification(`Running ${testIds.length} ${modeLabel} tests...`, 'info');

        // Enable pause button
        updatePauseResumeButtons(true, false);

        const result = await apiRequest('/api/run-tests', 'POST', {
            test_ids: testIds,
            use_learned: useLearned,
            max_retries: maxRetries,
            verify_each_step: true
        });

        // Disable pause button
        updatePauseResumeButtons(false, false);

        if (result.success) {
            addLog('success', `Batch execution completed: ${result.data?.passed || 0}/${testIds.length} passed`);
            showNotification(`Batch complete: ${result.data?.passed || 0} passed`, 'success');
        } else {
            addLog('warning', `Batch execution completed with failures: ${result.message}`);
            showNotification(result.message || 'Batch execution had failures', 'warning');
        }

        return result;
    } catch (error) {
        console.error('Run Excel tests error:', error);
        addLog('error', `Batch execution failed: ${error.message}`);
        showNotification('Batch execution failed', 'error');
        updatePauseResumeButtons(false, false);
        throw error;
    }
}

function selectAllExcelFiles() {
    const select = document.getElementById('excel-file-select');
    if (!select) return;

    Array.from(select.options).forEach(opt => {
        opt.selected = true;
    });
}

function setupExcelBatchListeners() {
    // Load Excel files button
    const refreshBtn = document.getElementById('excel-refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadExcelFiles);
    }

    // Select all files button
    const selectAllBtn = document.getElementById('excel-select-all-btn');
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', selectAllExcelFiles);
    }

    // Load test IDs button
    const loadIdsBtn = document.getElementById('load-excel-ids-btn');
    if (loadIdsBtn) {
        loadIdsBtn.addEventListener('click', loadTestIdsFromExcel);
    }

    // Clear preview button
    const clearBtn = document.getElementById('excel-clear-preview-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearExcelPreview);
    }

    // Select all test IDs button
    const selectAllIdsBtn = document.getElementById('excel-select-all-ids-btn');
    if (selectAllIdsBtn) {
        selectAllIdsBtn.addEventListener('click', selectAllExcelTestIds);
    }

    // Deselect all test IDs button
    const deselectAllIdsBtn = document.getElementById('excel-deselect-all-ids-btn');
    if (deselectAllIdsBtn) {
        deselectAllIdsBtn.addEventListener('click', deselectAllExcelTestIds);
    }

    // Run all tests button
    const runAllBtn = document.getElementById('run-excel-tests-btn');
    if (runAllBtn) {
        runAllBtn.addEventListener('click', runExcelTests);
    }

    // Run selected tests button
    const runSelectedBtn = document.getElementById('run-excel-selected-btn');
    if (runSelectedBtn) {
        runSelectedBtn.addEventListener('click', runSelectedExcelTests);
    }
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

        // Initialize UI enhancements
        initUIEnhancements();

        await fetchCurrentVIOModel();

        // Initialize new features
        await fetchHistorySummary();
        await fetchReportsList();

        // Initialize Excel batch feature
        setupExcelBatchListeners();
        await loadExcelFiles();

        const modelSelect = document.getElementById('vioModelSelect');
        if (modelSelect) {
            modelSelect.addEventListener('change', (e) => {
                updateVIOModelInfo(e.target.value);
            });
        }

        console.log('🚀 AI Agent Framework v2.0.0 ready');
    } catch (error) {
        console.error('Failed to start application:', error);
        showNotification('Application startup failed', 'error');
    }
});