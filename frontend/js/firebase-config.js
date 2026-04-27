/**
 * Firebase Configuration
 * 
 * DEMO MODE (Current): Uses mock Firebase config for local development
 * FIREBASE MODE: Replace with your real Firebase config for production
 */

// TO ENABLE REAL FIREBASE:
// 1. Replace the config below with your real Firebase project config
// 2. Ensure your backend serviceAccountKey.json is properly configured
// 3. Update the backend Firebase initialization

// Current: Demo Firebase config (for local development without Firebase)
const firebaseConfig = {
  // DEMO CONFIG - Replace with your real Firebase config
  apiKey: "demo-api-key",
  authDomain: "demo-project.firebaseapp.com", 
  projectId: "demo-project",
  storageBucket: "demo-project.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:demo123"
  
  // EXAMPLE REAL CONFIG (uncomment and modify):
  // apiKey: "AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  // authDomain: "your-project.firebaseapp.com",
  // projectId: "your-project-id",
  // storageBucket: "your-project.appspot.com", 
  // messagingSenderId: "123456789012",
  // appId: "1:123456789012:web:abcd1234567890"
};

// Initialize Firebase in demo mode (will fail gracefully)
try {
  firebase.initializeApp(firebaseConfig);
  const db = firebase.firestore();
  window.firebaseApp = firebase;
  window.db = db;
  console.log('🔥 Firebase initialized (demo mode)');
} catch (error) {
  console.log('🔧 Firebase unavailable - running in demo mode');
  window.firebaseApp = null;
  window.db = null;
}

// Auto-detect API URL based on current hostname
let API_URL;
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  API_URL = 'http://localhost:5000/api';
} else {
  // When deployed, use same-origin backend or override here
  API_URL = window.location.origin + '/api';
}
window.API_URL = API_URL;

console.log('✅ Frontend configuration loaded');
