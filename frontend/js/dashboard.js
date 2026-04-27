/**
 * Dashboard JavaScript - Firebase + API Fallback
 * Real-time dashboard for mystery networking event
 */

let statsData = {
    totalParticipants: 0,
    totalScans: 0,
    activeNow: 0,
    avgScore: 0
};

let leaderboardData = [];
let teamsData = []; // Store teams from CSV
let useFirebase = false;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Dashboard initializing...');
    
    // Check if Firebase is available and configured
    if (typeof firebase !== 'undefined' && typeof db !== 'undefined') {
        console.log('🔥 Firebase detected - using real-time listeners');
        useFirebase = true;
        setupFirebaseListeners();
    } else {
        console.log('🔧 Firebase not available - using REST API fallback');
        useFirebase = false;
    }
    
    loadInitialData();
    
    // Refresh every 10 seconds for API mode, real-time for Firebase
    if (!useFirebase) {
        setInterval(loadInitialData, 10000);
    }
    
    console.log('✅ Dashboard ready');
});

function setupFirebaseListeners() {
    // Listen for new scans
    db.collection('scans').onSnapshot((snapshot) => {
        updateStats();
    });
    
    // Listen for user updates
    db.collection('users').onSnapshot((snapshot) => {
        updateStats();
        updateLeaderboard();
    });
}

async function loadInitialData() {
    try {
        console.log('📊 Loading dashboard data...');
        
        // Load teams configuration first
        await loadTeams();
        
        // Load stats and leaderboard
        await updateStats();
        await updateLeaderboard();
        
        console.log('✅ Dashboard data loaded');
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showError('Failed to load data');
    }
}

async function loadTeams() {
    try {
        console.log('🏆 Loading teams configuration...');
        const apiUrl = window.API_URL || 'http://localhost:5000/api';
        const response = await fetch(`${apiUrl}/teams`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        teamsData = data.teams;
        console.log('✅ Teams loaded:', teamsData);
        
    } catch (error) {
        console.error('❌ Error loading teams:', error);
        // Fallback to default teams
        teamsData = [
            {"color": "blue", "name": "Blue Team", "emoji": "💼", "description": "Default Blue Team"},
            {"color": "red", "name": "Red Team", "emoji": "❤️", "description": "Default Red Team"},
            {"color": "green", "name": "Green Team", "emoji": "💚", "description": "Default Green Team"},
            {"color": "yellow", "name": "Yellow Team", "emoji": "💛", "description": "Default Yellow Team"},
            {"color": "purple", "name": "Purple Team", "emoji": "💜", "description": "Default Purple Team"}
        ];
        console.log('⚠️ Using fallback teams');
    }
}

async function updateStats() {
    try {
        if (useFirebase) {
            // Firebase mode - get real-time data
            await updateStatsFromFirebase();
        } else {
            // API fallback mode
            await updateStatsFromAPI();
        }
    } catch (error) {
        console.error('Error updating stats:', error);
        showError('Failed to update statistics');
    }
}

async function updateStatsFromFirebase() {
    // Get total participants
    const usersSnapshot = await db.collection('users').get();
    statsData.totalParticipants = usersSnapshot.size;
    
    // Get total scans
    const scansSnapshot = await db.collection('scans').get();
    statsData.totalScans = scansSnapshot.size;
    
    // Calculate active users (scanned in last 30 minutes)
    const thirtyMinutesAgo = new Date(Date.now() - 30 * 60 * 1000);
    const activeScansSnapshot = await db.collection('scans')
        .where('timestamp', '>', thirtyMinutesAgo)
        .get();
    
    const activeUsers = new Set();
    activeScansSnapshot.forEach(doc => {
        const data = doc.data();
        activeUsers.add(data.scanner_id);
        activeUsers.add(data.scanned_id);
    });
    statsData.activeNow = activeUsers.size;
    
    // Calculate average score
    let totalScore = 0;
    let userCount = 0;
    usersSnapshot.forEach(doc => {
        const userData = doc.data();
        if (userData.score !== undefined) {
            totalScore += userData.score;
            userCount++;
        }
    });
    statsData.avgScore = userCount > 0 ? Math.round(totalScore / userCount) : 0;
    
    // Update display with Firebase data format
    const firebaseData = {
        total_participants: statsData.totalParticipants,
        total_scans: statsData.totalScans,
        active_users: statsData.activeNow,
        completion_rate: statsData.avgScore,
        color_stats: {} // TODO: Calculate from Firebase if needed
    };
    
    updateStatsDisplay(firebaseData);
}

async function updateStatsFromAPI() {
    console.log('🔄 Fetching stats from API...');
    const apiUrl = window.API_URL || 'http://localhost:5000/api';
    const response = await fetch(`${apiUrl}/stats`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('📊 Stats received:', data);
    
    // Update global stats data
    statsData.totalParticipants = data.total_participants;
    statsData.totalScans = data.total_scans;
    statsData.activeNow = data.active_users || 0;
    statsData.avgScore = Math.round(data.average_score || 0);
    
    updateStatsDisplay(data);
}

function updateStatsDisplay(data) {
    // Update main stats
    document.getElementById('totalParticipants').textContent = data.total_participants;
    document.getElementById('totalScans').textContent = data.total_scans;
    document.getElementById('activeNow').textContent = data.active_users;
    document.getElementById('avgScore').textContent = data.completion_rate + '%';
    
    // Update color progress
    updateColorProgress(data.color_stats || {});
}

function updateColorProgress(colorStats) {
    const progressContainer = document.getElementById('colorProgress');
    if (!progressContainer) return;
    
    let progressHTML = '';
    
    // Use teams data from CSV instead of hardcoded
    for (const team of teamsData) {
        const stats = colorStats[team.color] || { total: 0, active: 0 };
        const percentage = stats.total > 0 ? Math.round((stats.active / stats.total) * 100) : 0;
        
        progressHTML += `
            <div class="color-progress" style="border-left: 4px solid ${team.color}">
                <div class="color-info">
                    <span class="color-name">${team.emoji} ${team.name}</span>
                    <span class="color-stats">${stats.active}/${stats.total} active</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${percentage}%; background-color: ${team.color}"></div>
                </div>
                <span class="percentage">${percentage}%</span>
            </div>
        `;
    }
    
    progressContainer.innerHTML = progressHTML;
}

async function updateLeaderboard() {
    try {
        if (useFirebase) {
            await updateLeaderboardFromFirebase();
        } else {
            await updateLeaderboardFromAPI();
        }
    } catch (error) {
        console.error('Error updating leaderboard:', error);
        showError('Failed to update leaderboard');
    }
}

async function updateLeaderboardFromFirebase() {
    const usersSnapshot = await db.collection('users')
        .orderBy('score', 'desc')
        .limit(10)
        .get();
    
    leaderboardData = [];
    usersSnapshot.forEach(doc => {
        const userData = doc.data();
        leaderboardData.push({
            id: doc.id,
            name: userData.full_name || userData.name || 'Anonymous',
            score: userData.score || 0,
            color: userData.genre_color || 'blue',
            found_target: userData.found_target || false,
            scanned_count: userData.scanned_count || 0
        });
    });
    
    updateLeaderboardDisplay();
}

async function updateLeaderboardFromAPI() {
    console.log('🏆 Fetching leaderboard from API...');
    const apiUrl = window.API_URL || 'http://localhost:5000/api';
    const response = await fetch(`${apiUrl}/leaderboard`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const leaderboard = await response.json();
    console.log('📋 Leaderboard received:', leaderboard);
    leaderboardData = leaderboard;
    
    updateLeaderboardDisplay();
}

function updateLeaderboardDisplay() {
    const leaderboardContainer = document.getElementById('leaderboardContent');
    
    if (leaderboardData.length === 0) {
        leaderboardContainer.innerHTML = '<div class="no-data">No activity yet... Start networking! 🚀</div>';
        return;
    }
    
    let html = '<div class="leaderboard-list">';
    
    const allowedColors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'gray'];
    
    leaderboardData.forEach((player, index) => {
        const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}.`;
        const targetFoundIcon = player.found_target ? '🎯' : '';
        const safeName = (player.name || '').replace(/[<>&"']/g, '');
        const safeColor = allowedColors.includes(player.color) ? player.color : 'gray';
        
        html += `
            <div class="leaderboard-item ${index < 3 ? 'top-three' : ''}">
                <div class="rank">${medal}</div>
                <div class="player-info">
                    <div class="player-name">${safeName} ${targetFoundIcon}</div>
                    <div class="player-details">
                        <span class="score">${parseInt(player.score) || 0} points</span>
                        <span class="scans">${parseInt(player.scanned_count) || 0} scans</span>
                        ${player.found_target ? '<span class="target-found">Target Found!</span>' : ''}
                    </div>
                </div>
                <div class="player-color" style="background-color: ${safeColor}"></div>
            </div>
        `;
    });
    
    html += '</div>';
    leaderboardContainer.innerHTML = html;
}

function showError(message) {
    console.error('Dashboard Error:', message);
    
    // Show error in stats
    document.getElementById('totalParticipants').textContent = '--';
    document.getElementById('totalScans').textContent = '--';
    document.getElementById('activeNow').textContent = '--';
    document.getElementById('avgScore').textContent = '--';
    
    // Show error in leaderboard
    const leaderboardContainer = document.getElementById('leaderboardContent');
    leaderboardContainer.innerHTML = `
        <div class="error">
            ⚠️ ${message}
            <br><small>Retrying in 10 seconds...</small>
        </div>
    `;
}

// Expose functions for debugging
window.dashboardDebug = {
    loadData: loadInitialData,
    statsData,
    leaderboardData
};

console.log('🎯 Dashboard script loaded');