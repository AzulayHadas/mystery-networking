/**
 * Participant App Logic
 * Handles QR scanning, scoring, and user interactions
 */

console.log('🚀 Participant app script loading...');

let currentUser = null;
let html5QrcodeScanner = null;
let isScanning = false;
let lastScanResult = null;
let pendingConversationBonus = false; // guard: only true after a successful scan

console.log('✅ Participant app variables initialized');

// Check if QR library is loaded
window.addEventListener('load', function() {
    console.log('📱 Page loaded, checking QR library...');
    if (typeof Html5Qrcode !== 'undefined') {
        console.log('✅ Html5Qrcode library loaded successfully');
    } else {
        console.error('❌ Html5Qrcode library failed to load');
    }
});

// ==================== LOGIN ====================

async function login() {
    console.log('🔐 Login function called');
    
    // Ensure API_URL is available
    const apiUrl = window.API_URL || 'http://localhost:5000/api';
    console.log('🌐 Using API_URL:', apiUrl);
    
    const emailInput = document.getElementById('emailInput');
    const errorDiv = document.getElementById('loginError');
    
    if (!emailInput) {
        console.error('❌ Email input not found!');
        return;
    }
    
    const email = emailInput.value.trim().toLowerCase();
    console.log('📧 Email entered:', email);
    
    if (!email) {
        const errorMsg = 'נא להזין אימייל';
        if (errorDiv) {
            errorDiv.textContent = errorMsg;
            errorDiv.style.display = 'block';
        }
        console.log('❌ No email provided');
        return;
    }
    
    // Clear previous errors
    if (errorDiv) {
        errorDiv.style.display = 'none';
    }
    
    // Disable button during request
    const loginButton = document.getElementById('loginButton');
    if (loginButton) {
        loginButton.disabled = true;
        loginButton.textContent = 'מתחבר...';
    }
    
    try {
        console.log('🚀 Making login request to:', `${apiUrl}/auth/login`);
        
        const loginController = new AbortController();
        const loginTimeout = setTimeout(() => loginController.abort(), 10000);
        const response = await fetch(`${apiUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email }),
            signal: loginController.signal
        });
        clearTimeout(loginTimeout);
        
        console.log('📡 Response status:', response.status);
        
        const data = await response.json();
        console.log('📊 Response data:', data);
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}: Login failed`);
        }
        
        // Save user data
        currentUser = data.user;
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        
        console.log('✅ Login successful, user:', currentUser);
        
        // Show main app
        const loginScreen = document.getElementById('loginScreen');
        const mainApp = document.getElementById('mainApp');
        
        if (loginScreen && mainApp) {
            loginScreen.style.display = 'none';
            mainApp.style.display = 'block';
            
            // Initialize app
            initializeApp();
        } else {
            console.error('❌ Login/main app containers not found!');
        }
        
    } catch (error) {
        console.error('❌ Login error:', error);
        if (errorDiv) {
            errorDiv.textContent = error.message || 'שגיאה בהתחברות';
            errorDiv.style.display = 'block';
        }
    } finally {
        // Re-enable button
        if (loginButton) {
            loginButton.disabled = false;
            loginButton.textContent = 'התחבר';
        }
    }
}

// Expose login function globally immediately after definition
window.login = login;
console.log('🌍 Login function exposed globally');
console.log('🔍 Testing window.login availability:', typeof window.login);

// Additional exposure for debugging
if (typeof window.login === 'undefined') {
    console.error('❌ window.login is undefined after assignment!');
    // Force exposure
    window.login = function() {
        console.log('🆘 Fallback login function called');
        return login.apply(this, arguments);
    };
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('🌐 DOM loaded, setting up event listeners...');
    
    // Add event listener to login button as backup
    const loginButton = document.getElementById('loginButton');
    if (loginButton) {
        loginButton.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('🔘 Login button clicked via event listener');
            login();
        });
        console.log('✅ Login button event listener added');
    } else {
        console.error('❌ Login button not found!');
    }
    
    // Add enter key support for email input
    const emailInput = document.getElementById('emailInput');
    if (emailInput) {
        emailInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                console.log('⏎ Enter key pressed');
                login();
            }
        });
        console.log('✅ Email input event listener added');
    }
});

// Also ensure it's available after window loads
window.addEventListener('load', function() {
    console.log('🚀 Window loaded, ensuring login function is available');
    window.login = login;
});

// ==================== APP INITIALIZATION ====================

function initializeApp() {
    // Update UI with user data
    document.getElementById('userName').textContent = `${currentUser.full_name} (ID: ${currentUser.id})`;
    updateScore(currentUser.current_score);
    updateColorProgress(currentUser.color_scanned);
    
    // Load mission
    loadMission();
    
    // Listen for real-time score updates if Firebase is available
    if (typeof db !== 'undefined' && db !== null) {
        listenToScoreUpdates();
    }
}

async function loadMission() {
    console.log('📋 Loading all missions for user:', currentUser.id);
    const missionContent = document.getElementById('missionContent');

    const ALLOWED_BG_COLORS = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'gray'];

    try {
        const response = await fetch(`${API_URL}/user/${currentUser.id}/targets`);
        const data = await response.json();
        const targets = data.targets || [];

        // Clear previous content safely
        missionContent.textContent = '';

        if (targets.length === 0) {
            const noMissions = document.createElement('div');
            noMissions.className = 'no-missions';
            const h3 = document.createElement('h3');
            h3.textContent = '📝 אין משימות זמינות';
            const p = document.createElement('p');
            p.textContent = 'לא נמצאו יעדים עבור המשתתף הזה';
            noMissions.appendChild(h3);
            noMissions.appendChild(p);
            missionContent.appendChild(noMissions);
            return;
        }

        const list = document.createElement('div');
        list.className = 'missions-list';

        const listTitle = document.createElement('h3');
        listTitle.textContent = '🎯 רשימת המשימות שלך';
        list.appendChild(listTitle);

        const intro = document.createElement('p');
        intro.className = 'missions-intro';
        intro.textContent = 'מצא את האנשים הבאים וסרוק את הקודים שלהם:';
        list.appendChild(intro);

        targets.forEach((target) => {
            const statusIcon = target.found ? '✅' : '🔍';
            const statusClass = target.found ? 'completed-mission' : 'pending-mission';
            const statusText = target.found ? 'הושלמה!' : 'ממתין';

            const item = document.createElement('div');
            item.className = `mission-item ${statusClass}`;

            // Header row
            const header = document.createElement('div');
            header.className = 'mission-header';

            const statusSpan = document.createElement('span');
            statusSpan.className = 'mission-status';
            statusSpan.textContent = `${statusIcon} ${statusText}`;

            const pointsSpan = document.createElement('span');
            pointsSpan.className = 'mission-points';
            pointsSpan.textContent = `${parseInt(target.points) || 0} נקודות`;

            header.appendChild(statusSpan);
            header.appendChild(pointsSpan);

            // Detail rows
            const details = document.createElement('div');
            details.className = 'mission-details';

            const nameEl = document.createElement('h4');
            nameEl.className = 'target-name';
            nameEl.textContent = target.target_name;

            const jobEl = document.createElement('p');
            jobEl.className = 'target-job';
            jobEl.textContent = target.target_job;

            const colorEl = document.createElement('p');
            colorEl.className = 'target-color';
            colorEl.textContent = 'צבע תג: ';

            const badge = document.createElement('span');
            badge.className = 'color-badge';
            const safeColor = ALLOWED_BG_COLORS.includes(target.target_color) ? target.target_color : 'gray';
            badge.style.backgroundColor = safeColor;
            badge.style.color = 'white';
            badge.style.padding = '2px 6px';
            badge.style.borderRadius = '8px';
            badge.style.fontSize = '0.8em';
            badge.textContent = getColorName(safeColor);
            colorEl.appendChild(badge);

            details.appendChild(nameEl);
            details.appendChild(jobEl);
            details.appendChild(colorEl);

            if (!target.found && target.convo_tip) {
                const tip = document.createElement('div');
                tip.className = 'conversation-tip';
                const tipTitle = document.createElement('h5');
                tipTitle.textContent = '💡 רמז שיחה:';
                const tipText = document.createElement('p');
                tipText.textContent = target.convo_tip;
                tip.appendChild(tipTitle);
                tip.appendChild(tipText);
                details.appendChild(tip);
            }

            item.appendChild(header);
            item.appendChild(details);
            list.appendChild(item);
        });

        missionContent.appendChild(list);

        const instructions = document.createElement('div');
        instructions.className = 'scan-instructions';
        const p1 = document.createElement('p');
        p1.textContent = '📱 איך לסרוק: לחץ על "התחל סריקה" ופנה המצלמה לקוד QR';
        const p2 = document.createElement('p');
        p2.textContent = '🎉 תקבל נקודות על כל יעד שתמצא!';
        instructions.appendChild(p1);
        instructions.appendChild(p2);
        missionContent.appendChild(instructions);

    } catch (error) {
        console.error('Error loading missions:', error);
        missionContent.textContent = '';
        const errDiv = document.createElement('div');
        errDiv.className = 'error-message';
        const errTitle = document.createElement('p');
        errTitle.style.cssText = 'color:#ef4444;font-weight:bold;';
        errTitle.textContent = '❌ שגיאה בטעינת המשימות';
        const errDetail = document.createElement('p');
        errDetail.style.cssText = 'font-size:0.9em;color:#2d3748;';
        errDetail.textContent = 'בדוק את החיבור לאינטרנט';
        errDiv.appendChild(errTitle);
        errDiv.appendChild(errDetail);
        missionContent.appendChild(errDiv);
    }
}

function getColorName(color) {
    const colorNames = {
        'blue': 'כחול',
        'red': 'אדום', 
        'green': 'ירוק',
        'yellow': 'צהוב',
        'purple': 'סגול'
    };
    return colorNames[color] || color;
}

// Test camera permissions
async function testCameraPermissions() {
    try {
        console.log('🔍 Testing camera permissions...');
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        console.log('✅ Camera access granted');
        
        // Stop the test stream
        stream.getTracks().forEach(track => track.stop());
        
        return true;
    } catch (error) {
        console.error('❌ Camera access denied:', error);
        alert('נדרשת הרשאה למצלמה כדי לסרוק QR. אנא אפשר גישה למצלמה ונסה שוב.');
        return false;
    }
}

// ==================== QR SCANNING ====================

async function startScanning() {
    const qrReader = document.getElementById('qr-reader');
    
    if (isScanning) {
        stopScanning();
        return;
    }
    
    // Test camera permissions first
    const hasPermission = await testCameraPermissions();
    if (!hasPermission) {
        return;
    }
    
    console.log('📷 Starting QR scanner...');
    qrReader.style.display = 'block';
    isScanning = true;
    _scanErrorCount = 0;
    
    // Check if Html5Qrcode is available
    if (typeof Html5Qrcode === 'undefined') {
        console.error('❌ Html5Qrcode library not loaded');
        alert('שגיאה: ספריית הסריקה לא נטענה');
        stopScanning();
        return;
    }
    
    // Initialize scanner
    try {
        html5QrcodeScanner = new Html5Qrcode("qr-reader");
    } catch (error) {
        console.error('❌ Failed to create scanner:', error);
        alert('שגיאה ביצירת הסרוק');
        stopScanning();
        return;
    }
    
    const config = {
        fps: 10,
        qrbox: { width: 250, height: 250 },
        aspectRatio: 1.0,
        supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA]
    };
    
    // Try to get camera permissions first
    html5QrcodeScanner.start(
        { facingMode: "environment" }, // Use back camera
        config,
        onScanSuccess,
        onScanError
    ).catch(err => {
        console.error("❌ Failed to start scanner:", err);
        
        // Try with front camera if back camera fails
        html5QrcodeScanner.start(
            { facingMode: "user" }, // Front camera
            config,
            onScanSuccess,
            onScanError
        ).catch(err2 => {
            console.error("❌ Failed to start scanner with front camera:", err2);
            alert('שגיאה בפתיחת המצלמה. נא לאשר הרשאות מצלמה.');
            stopScanning();
        });
    });
    
    // Update button text
    const button = document.querySelector('.scan-button');
    if (button) {
        button.textContent = '⏹️ עצור סריקה';
    }
}

function stopScanning() {
    if (html5QrcodeScanner) {
        html5QrcodeScanner.stop().then(() => {
            console.log('✅ Scanner stopped successfully');
            const qrReader = document.getElementById('qr-reader');
            if (qrReader) {
                qrReader.style.display = 'none';
            }
            isScanning = false;
            const button = document.querySelector('.scan-button');
            if (button) {
                button.textContent = '📸 סרוק תג QR';
            }
            html5QrcodeScanner = null;
        }).catch(err => {
            console.error("❌ Failed to stop scanner:", err);
            // Force reset even if stop fails
            isScanning = false;
            const qrReader = document.getElementById('qr-reader');
            if (qrReader) {
                qrReader.style.display = 'none';
            }
            const button = document.querySelector('.scan-button');
            if (button) {
                button.textContent = '📸 סרוק תג QR';
            }
            html5QrcodeScanner = null;
        });
    } else {
        // Reset state even if no scanner
        isScanning = false;
        const qrReader = document.getElementById('qr-reader');
        if (qrReader) {
            qrReader.style.display = 'none';
        }
        const button = document.querySelector('.scan-button');
        if (button) {
            button.textContent = '📸 סרוק תג QR';
        }
    }
}

async function onScanSuccess(decodedText) {
    console.log('🎯 QR Code scanned:', decodedText);
    
    // Prevent duplicate scans
    if (decodedText === lastScanResult) {
        console.log('⚠️ Duplicate scan ignored');
        return;
    }
    
    lastScanResult = decodedText;
    
    // Stop scanning
    stopScanning();
    
    // Vibrate if supported
    if (navigator.vibrate) {
        navigator.vibrate(200);
    }
    
    // Process the scan
    try {
        await processScan(decodedText);
    } catch (error) {
        console.error('❌ Error processing scan:', error);
        alert('שגיאה בעיבוד הסריקה');
    }
    
    // Reset after 3 seconds
    setTimeout(() => {
        lastScanResult = null;
    }, 3000);
}

let _scanErrorCount = 0;
function onScanError(errorMessage) {
    // Most errors are transient frame-decode noise — only surface persistent failures
    _scanErrorCount++;
    if (_scanErrorCount === 60) { // ~6 seconds at 10fps with no successful decode
        showNotification('📷 לא מצליח לזהות קוד — ודא שהקוד ממורכז ומואר');
    }
}

// Manual QR testing function
async function testManualScan() {
    const input = document.getElementById('manualQrInput');
    const qrValue = input.value.trim();
    
    if (!qrValue) {
        alert('נא להזין QR ID');
        return;
    }
    
    console.log('🧪 Testing manual QR:', qrValue);
    
    try {
        await processScan(qrValue);
        input.value = ''; // Clear input after successful scan
    } catch (error) {
        console.error('❌ Manual scan error:', error);
        alert('שגיאה בבדיקה ידנית');
    }
}

// ==================== SCAN PROCESSING ====================

async function processScan(scannedId) {
    try {
        // Show loading
        showLoading();
        
        // Send to backend
        const scanController = new AbortController();
        const scanTimeout = setTimeout(() => scanController.abort(), 10000);
        const response = await fetch(`${API_URL}/scan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scanner_id: currentUser.id,
                scanned_id: scannedId
            }),
            signal: scanController.signal
        });
        clearTimeout(scanTimeout);
        
        const data = await response.json();
        
        if (!response.ok) {
            // Show error
            alert(data.error || 'שגיאה בסריקה');
            return;
        }
        
        // Update local score
        currentUser.current_score = data.total_score;
        updateScore(data.total_score);
        
        // Show result modal
        pendingConversationBonus = true;
        showResult(data);
        
        // Reload mission if target found
        if (data.is_target) {
            setTimeout(() => {
                loadMission();
            }, 2000);
        }
        
    } catch (error) {
        console.error('Scan processing error:', error);
        alert('שגיאה בעיבוד הסריקה');
    } finally {
        hideLoading();
    }
}

// ==================== UI UPDATES ====================

function showResult(data) {
    const modal = document.getElementById('resultModal');
    const icon = document.getElementById('resultIcon');
    const title = document.getElementById('resultTitle');
    const message = document.getElementById('resultMessage');
    const points = document.getElementById('pointsEarned');
    const preview = document.getElementById('linkedinPreview');
    const scannedName = document.getElementById('scannedName');
    const conversationTip = document.getElementById('conversationTip');
    
    // Set icon and title
    if (data.is_target) {
        icon.textContent = '🎯';
        title.textContent = 'מצאת את היעד שלך!';
    } else {
        icon.textContent = '👋';
        title.textContent = 'נעים להכיר!';
    }
    
    // Set message with bonuses
    message.textContent = '';
    if (data.bonuses) {
        data.bonuses.forEach(b => {
            const p = document.createElement('p');
            p.textContent = b;
            message.appendChild(p);
        });
    }
    
    // Set points
    points.textContent = `+${data.points_earned} נקודות`;
    
    // Set scanned user info with job title
    scannedName.textContent = data.scanned_user.name;
    if (data.scanned_user.job_title) {
        scannedName.textContent += ` - ${data.scanned_user.job_title}`;
    }
    
    // Set conversation tip only for valid targets
    if (data.show_conversation_tip && data.conversation_tip) {
        conversationTip.textContent = `💡 טיפ לשיחה: ${data.conversation_tip}`;
        conversationTip.style.display = 'block';
    } else {
        conversationTip.style.display = 'none';
    }
    
    // Set LinkedIn link for all scans (both valid and invalid targets)
    const linkedinLink = document.getElementById('linkedinLink');
    const linkedinUrl = document.getElementById('linkedinUrl');
    
    if (data.scanned_user.linkedin && data.scanned_user.linkedin.trim() !== '') {
        linkedinUrl.href = data.scanned_user.linkedin;
        linkedinLink.style.display = 'block';
    } else {
        linkedinLink.style.display = 'none';
    }
    
    // Show modal
    modal.classList.add('show');
}

function closeResult() {
    const modal = document.getElementById('resultModal');
    modal.classList.remove('show');
    
    // Refresh the mission list to show updated completion status
    loadMission();
    
    // Award conversation completion bonus only once per scan
    if (pendingConversationBonus) {
        pendingConversationBonus = false;
        awardConversationBonus();
    }
}

async function awardConversationBonus() {
    try {
        const response = await fetch(`${API_URL}/conversation/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser.id })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentUser.current_score = data.new_score;
            updateScore(data.new_score);
            
            // Show small notification
            showNotification(`+${data.points_earned} על השלמת שיחה!`);
        }
    } catch (error) {
        console.error('Failed to award conversation bonus:', error);
    }
}

function updateScore(score) {
    document.getElementById('scoreDisplay').textContent = score;
}

function updateColorProgress(colorScanned) {
    if (!colorScanned) return;
    const colors = ['red', 'blue', 'green', 'yellow'];
    
    colors.forEach(color => {
        const circle = document.getElementById(`${color}Circle`);
        if (circle && colorScanned[color]) {
            circle.classList.add('scanned');
        }
    });
}

function showLoading() {
    // You can add a loading overlay here
}

function hideLoading() {
    // Hide loading overlay
}

function showNotification(message) {
    // Simple notification
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #10b981;
        color: white;
        padding: 15px 25px;
        border-radius: 10px;
        z-index: 2000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// ==================== REAL-TIME UPDATES ====================

function listenToScoreUpdates() {
    // Listen to user document changes
    db.collection('users').doc(currentUser.id)
        .onSnapshot((doc) => {
            if (doc.exists) {
                const data = doc.data();
                currentUser.current_score = data.current_score;
                updateScore(data.current_score);
                updateColorProgress(data.color_scanned);
            }
        });
}

// ==================== HELPER FUNCTIONS ====================

function getColorName(color) {
    const names = {
        red: 'אדום',
        blue: 'כחול',
        green: 'ירוק',
        yellow: 'צהוב'
    };
    return names[color] || color;
}

// ==================== INITIALIZATION ====================

// Check if user is already logged in
window.addEventListener('DOMContentLoaded', () => {
    const savedUser = localStorage.getItem('currentUser');
    
    if (savedUser) {
        currentUser = JSON.parse(savedUser);
        document.getElementById('loginScreen').style.display = 'none';
        document.getElementById('mainApp').style.display = 'block';
        initializeApp();
    }
});
