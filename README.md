# 🎯 Mystery Networking System

## Quick Start

### 1. Setup Firebase
- Go to https://console.firebase.google.com
- Create project: mystery-networking
- Enable Firestore Database (test mode)
- Enable Authentication (Email/Password)
- Download serviceAccountKey.json → place in backend/

### 2. Install Dependencies
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Mac/Linux
# OR: venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. Configure Frontend
Edit `frontend/js/firebase-config.js` with YOUR Firebase config

### 4. Import Participants
```bash
python admin.py
# Choose 1: Import from CSV
# Path: ../data/participants.csv
```

### 5. Generate QR Codes
```bash
python admin.py
# Choose 2: Generate QR codes
```

### 6. Run Backend
```bash
python app.py
```

### 7. Open Apps
- Participant: Open frontend/participant.html in mobile browser
- Dashboard: Open frontend/dashboard.html on projector

## Need Complete Frontend Files?

The frontend HTML/JS files are too large for auto-generation.
Download them from the Claude conversation artifacts:
- participant.html
- participant.js
- dashboard.html
- dashboard.js

Or copy them manually from the code provided.

## Support
Check README files and troubleshooting guide in documentation.
