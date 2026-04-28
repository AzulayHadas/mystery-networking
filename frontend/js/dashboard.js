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

    const ALLOWED_COLORS = ['red','blue','green','yellow','purple','orange','pink','gray','black','white'];

    progressContainer.textContent = '';

    for (const team of teamsData) {
        const stats = colorStats[team.color] || { total: 0, active: 0 };
        const percentage = stats.total > 0 ? Math.round((stats.active / stats.total) * 100) : 0;
        const safeColor = ALLOWED_COLORS.includes(team.color) ? team.color : 'gray';

        const row = document.createElement('div');
        row.className = 'color-progress';
        row.style.borderLeft = `4px solid ${safeColor}`;

        const info = document.createElement('div');
        info.className = 'color-info';

        const nameSpan = document.createElement('span');
        nameSpan.className = 'color-name';
        nameSpan.textContent = `${team.emoji} ${team.name}`;

        const statsSpan = document.createElement('span');
        statsSpan.className = 'color-stats';
        statsSpan.textContent = `${stats.active}/${stats.total} active`;

        info.appendChild(nameSpan);
        info.appendChild(statsSpan);

        const barWrap = document.createElement('div');
        barWrap.className = 'progress-bar';
        const fill = document.createElement('div');
        fill.className = 'progress-fill';
        fill.style.width = `${percentage}%`;
        fill.style.backgroundColor = safeColor;
        barWrap.appendChild(fill);

        const pctSpan = document.createElement('span');
        pctSpan.className = 'percentage';
        pctSpan.textContent = `${percentage}%`;

        row.appendChild(info);
        row.appendChild(barWrap);
        row.appendChild(pctSpan);
        progressContainer.appendChild(row);
    }
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

    leaderboardContainer.textContent = '';

    if (leaderboardData.length === 0) {
        const msg = document.createElement('div');
        msg.className = 'no-data';
        msg.textContent = 'No activity yet... Start networking! 🚀';
        leaderboardContainer.appendChild(msg);
        return;
    }

    const ALLOWED_COLORS = ['red','blue','green','yellow','purple','orange','pink','gray'];
    const list = document.createElement('div');
    list.className = 'leaderboard-list';

    leaderboardData.forEach((player, index) => {
        const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `${index + 1}.`;
        const safeColor = ALLOWED_COLORS.includes(player.color) ? player.color : 'gray';

        const item = document.createElement('div');
        item.className = `leaderboard-item${index < 3 ? ' top-three' : ''}`;

        const rankDiv = document.createElement('div');
        rankDiv.className = 'rank';
        rankDiv.textContent = medal;

        const infoDiv = document.createElement('div');
        infoDiv.className = 'player-info';

        const nameDiv = document.createElement('div');
        nameDiv.className = 'player-name';
        nameDiv.textContent = player.name || 'Anonymous';
        if (player.found_target) {
            const icon = document.createElement('span');
            icon.setAttribute('aria-label', 'Target found');
            icon.textContent = ' 🎯';
            nameDiv.appendChild(icon);
        }

        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'player-details';

        const scoreSpan = document.createElement('span');
        scoreSpan.className = 'score';
        scoreSpan.textContent = `${parseInt(player.score) || 0} points`;

        const scansSpan = document.createElement('span');
        scansSpan.className = 'scans';
        scansSpan.textContent = `${parseInt(player.scanned_count) || 0} scans`;

        detailsDiv.appendChild(scoreSpan);
        detailsDiv.appendChild(scansSpan);

        if (player.found_target) {
            const foundSpan = document.createElement('span');
            foundSpan.className = 'target-found';
            foundSpan.textContent = 'Target Found!';
            detailsDiv.appendChild(foundSpan);
        }

        infoDiv.appendChild(nameDiv);
        infoDiv.appendChild(detailsDiv);

        const colorDot = document.createElement('div');
        colorDot.className = 'player-color';
        colorDot.style.backgroundColor = safeColor;

        item.appendChild(rankDiv);
        item.appendChild(infoDiv);
        item.appendChild(colorDot);
        list.appendChild(item);
    });

    leaderboardContainer.appendChild(list);
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
    leaderboardContainer.textContent = '';
    const errDiv = document.createElement('div');
    errDiv.className = 'error';
    errDiv.textContent = `⚠️ ${message}`;
    const small = document.createElement('small');
    small.textContent = 'Retrying in 10 seconds...';
    errDiv.appendChild(document.createElement('br'));
    errDiv.appendChild(small);
    leaderboardContainer.appendChild(errDiv);
}

// Expose functions for debugging
window.dashboardDebug = {
    loadData: loadInitialData,
    statsData,
    leaderboardData
};

console.log('🎯 Dashboard script loaded');