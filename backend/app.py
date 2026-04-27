"""
Mystery Networking System - Main Backend
Flask API with Firebase Integration
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from collections import deque
import os
import json
import pandas as pd
from scoring import ScoringEngine
from models import User, Scan  # noqa: F401

# Initialize Flask
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Load participant data for demo mode
participants_data = {}
qr_mapping = {}
email_to_userid = {}  # New mapping for email to user_id lookup
target_assignments = {}  # scanner_id -> target_id
target_assignments_df = None  # Full target assignments DataFrame (multi-target)
user_stats = {}  # user_id -> stats
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_STATS_FILE = os.path.join(BASE_DIR, 'data', 'user_stats.json')

# Web logging system
web_logs = deque(maxlen=1000)


def web_log(level, message, data=None):
    """Add a log entry to the web log system"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'message': message,
        'data': data
    }
    web_logs.append(log_entry)
    print(f"[{level}] {message}" + (f" | Data: {data}" if data else ""))


def save_user_stats():
    """Save user stats to JSON file"""
    try:
        os.makedirs(os.path.dirname(USER_STATS_FILE), exist_ok=True)
        with open(USER_STATS_FILE, 'w') as f:
            json.dump(user_stats, f, indent=2)
    except Exception as e:
        web_log('ERROR', f'Error saving user stats: {e}')


def load_participant_data():
    """Load participant data from CSV files for demo mode"""
    global participants_data, qr_mapping, email_to_userid, target_assignments, target_assignments_df  # noqa: F824

    try:
        # Load enhanced QR mapping with genre and job title
        qr_file = os.path.join(BASE_DIR, 'qr_codes', 'qr_mapping.csv')
        if os.path.exists(qr_file):
            qr_df = pd.read_csv(qr_file)
            qr_mapping = dict(zip(qr_df['user_id'], qr_df['email']))
            email_to_userid = dict(zip(qr_df['email'], qr_df['user_id']))  # Create reverse mapping
            print(f"✅ Loaded {len(qr_mapping)} QR mappings with enhanced data")

        # Load target assignments from CSV
        target_file = os.path.join(BASE_DIR, 'qr_codes', 'target_assignments.csv')
        if os.path.exists(target_file):
            target_assignments_df = pd.read_csv(target_file)
            # Keep backward-compatible dict (last target per scanner)
            target_assignments = dict(zip(target_assignments_df['scanner_id'], target_assignments_df['target_id']))
            print(f"🎯 Loaded {len(target_assignments_df)} target assignments from CSV")
        else:
            # Fallback: Create target assignments (simple round-robin for demo)
            user_ids = list(qr_mapping.keys())
            for i, user_id in enumerate(user_ids):
                target_id = user_ids[(i + 1) % len(user_ids)]
                target_assignments[user_id] = target_id
            print(f"🎯 Created {len(target_assignments)} fallback target assignments")

        # Initialize user stats
        for user_id in qr_mapping.keys():
            user_stats[user_id] = {
                'total_score': 0,
                'scanned_users': [],
                'found_target': False,
                'completed_targets': []
            }

        # Load participant details
        participants_file = os.path.join(BASE_DIR, 'data', 'participants.csv')
        if os.path.exists(participants_file):
            df = pd.read_csv(participants_file)
            df['email'] = df['email'].str.lower().str.strip()

            for _, row in df.iterrows():
                email = row['email']
                participants_data[email] = {
                    'full_name': row['full_name'],
                    'email': email,
                    'linkedin_url': row.get('linkedin_url', ''),
                    'genre_color': row.get('genre_color', 'blue'),
                    'convo_tip': row.get('convo_tip', '')
                }
            print(f"✅ Loaded {len(participants_data)} participant profiles")
            print(f"🎯 Created {len(target_assignments)} target assignments")

    except Exception as e:
        print(f"⚠️ Could not load participant data: {e}")


# Load participant data on startup
load_participant_data()

# Initialize Firebase
try:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase initialized successfully")
except Exception as e:
    print(f"⚠️  Firebase initialization failed: {e}")
    print("🔧 Running in demo mode without Firebase")
    db = None

# Initialize scoring engine
if db:
    scorer = ScoringEngine(db)
else:
    scorer = None

# ==================== HEALTH CHECK ====================


@app.route('/api/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({
        "status": "ok",
        "firebase_connected": db is not None,
        "timestamp": datetime.now().isoformat()
    })

# ==================== AUTHENTICATION ====================


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Login endpoint - verifies user exists in database
    Body: { "email": "user@example.com" }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()

        if not email:
            return jsonify({"error": "Email is required"}), 400

        # Demo mode fallback if Firebase is not available
        if db is None:
            # Find the actual participant by email
            if email in participants_data and email in email_to_userid:
                participant = participants_data[email]
                user_id = email_to_userid[email]

                return jsonify({
                    "success": True,
                    "user": {
                        "id": user_id,
                        "email": email,
                        "full_name": participant['full_name'],
                        "linkedin_url": participant.get('linkedin_url', ''),
                        "genre_color": participant.get('genre_color', 'blue'),
                        "convo_tip": participant.get('convo_tip', ''),
                        "current_score": user_stats.get(user_id, {}).get('total_score', 0)
                    }
                }), 200

            # Fallback for unknown emails - still allow login but with demo data
            return jsonify({
                "success": True,
                "user": {
                    "id": "demo_user_123",
                    "email": email,
                    "full_name": f"Demo User ({email})",
                    "linkedin_url": "https://linkedin.com/in/demo",
                    "genre_color": "blue",
                    "convo_tip": "Use a participant email for accurate testing: john.doe@email.com, jane.smith@email.com, etc.",
                    "current_score": 0
                }
            }), 200

        # Check if user exists in Firestore
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).limit(1)
        results = list(query.stream())

        if not results:
            return jsonify({"error": "User not found. Please contact admin."}), 404

        user_doc = results[0]
        user_data = user_doc.to_dict()
        user_data['id'] = user_doc.id

        return jsonify({
            "success": True,
            "user": user_data
        }), 200

    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({"error": "Login failed"}), 500

# ==================== PARTICIPANTS EMAILS ====================


@app.route('/api/participants/emails', methods=['GET'])
def get_participant_emails():
    """Return list of participant emails for login autocomplete."""
    try:
        emails = sorted(participants_data.keys())
        return jsonify({"emails": emails}), 200
    except Exception as e:
        print(f"Get emails error: {str(e)}")
        return jsonify({"emails": []}), 200

# ==================== USER ENDPOINTS ====================


@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user details by ID"""
    try:
        # Demo mode fallback if Firebase is not available
        if db is None:
            return jsonify({
                "id": user_id,
                "email": "demo@example.com",
                "full_name": "Demo User",
                "linkedin_url": "https://linkedin.com/in/demo",
                "genre_color": "blue",
                "convo_tip": "This is demo mode - Firebase not configured"
            }), 200

        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()

        if not user.exists:
            return jsonify({"error": "User not found"}), 404

        user_data = user.to_dict()
        user_data['id'] = user.id

        return jsonify(user_data), 200

    except Exception as e:
        print(f"Get user error: {str(e)}")
        return jsonify({"error": "Failed to fetch user"}), 500


@app.route('/api/user/<user_id>/targets', methods=['GET'])
def get_user_targets(user_id):
    """Get ALL target user details for a participant"""
    try:
        # Demo mode fallback if Firebase is not available
        if db is None:
            targets_list = []

            # Read target assignments to get all targets for this user
            try:
                if target_assignments_df is not None:
                    user_targets = target_assignments_df[target_assignments_df['scanner_id'] == user_id]
                else:
                    user_targets = pd.DataFrame()  # empty

                for _, target_row in user_targets.iterrows():
                    target_id = target_row['target_id']

                    # Check if this specific target has been completed
                    completed_targets = user_stats.get(user_id, {}).get('completed_targets', [])
                    found = target_id in completed_targets

                    # Get conversation tip directly from CSV if available
                    convo_tip = target_row.get('convo_tip', 'התחל שיחה על העבודה שלכם')

                    targets_list.append({
                        "target_id": target_id,
                        "target_name": target_row['target_name'],
                        "target_color": target_row['target_color'],
                        "target_job": target_row['target_job_title'],
                        "convo_tip": convo_tip,
                        "points": 10,  # Default points
                        "found": found
                    })

            except Exception as e:
                print(f"Error reading assignments: {e}")
                return jsonify({"targets": []}), 200

            return jsonify({"targets": targets_list}), 200

        # Firebase implementation (if needed)
        return jsonify({"targets": []}), 200

    except Exception as e:
        print(f"Get targets error: {str(e)}")
        return jsonify({"error": "Failed to fetch targets"}), 500


@app.route('/api/user/<user_id>/target', methods=['GET'])
def get_user_target(user_id):
    """Get the target user details for a participant"""
    try:
        # Demo mode fallback if Firebase is not available
        if db is None:
            target_id = target_assignments.get(user_id)
            if target_id:
                target_email = qr_mapping.get(target_id)
                if target_email and target_email in participants_data:
                    target = participants_data[target_email]
                    found = user_stats.get(user_id, {}).get('found_target', False)

                    # Get job title from enhanced QR mapping
                    job_title = "Unknown Role"
                    try:
                        qr_df = pd.read_csv(os.path.join(BASE_DIR, 'qr_codes', 'qr_mapping.csv'))
                        target_row = qr_df[qr_df['user_id'] == target_id]
                        if not target_row.empty:
                            job_title = target_row['job_title'].iloc[0]
                    except Exception:
                        pass

                    return jsonify({
                        "target_name": target['full_name'],
                        "target_color": target.get('genre_color', 'blue'),
                        "target_job_title": job_title,
                        "target_id": target_id,
                        "found": found
                    }), 200

            return jsonify({
                "target_name": "לא נמצא יעד",
                "target_color": "gray",
                "found": False
            }), 200

        # Get current user
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()

        if not user.exists:
            return jsonify({"error": "User not found"}), 404

        user_data = user.to_dict()
        target_id = user_data.get('target_id')

        if not target_id:
            return jsonify({"error": "No target assigned"}), 404

        # Get target user
        target_ref = db.collection('users').document(target_id)
        target = target_ref.get()

        if not target.exists:
            return jsonify({"error": "Target not found"}), 404

        target_data = target.to_dict()

        return jsonify({
            "target_name": target_data.get('full_name'),
            "target_color": target_data.get('genre_color'),
            "found": user_data.get('found_target', False)
        }), 200

    except Exception as e:
        print(f"Get target error: {str(e)}")
        return jsonify({"error": "Failed to fetch target"}), 500

# ==================== QR SCAN ENDPOINT ====================


@app.route('/api/scan', methods=['POST'])
def process_scan():
    """
    Process QR code scan
    Body: {
        "scanner_id": "user_id_1",
        "scanned_id": "user_id_2"
    }
    """
    try:
        data = request.get_json()
        scanner_id = data.get('scanner_id')
        scanned_id = data.get('scanned_id')

        if not scanner_id or not scanned_id:
            return jsonify({"error": "Missing scanner_id or scanned_id"}), 400

        # Prevent self-scan
        if scanner_id == scanned_id:
            return jsonify({
                "error": "You cannot scan yourself!",
                "is_target": False,
                "points": 0
            }), 400

        # Demo mode fallback if Firebase is not available
        if db is None:
            # Check if this is a valid scan
            scanned_email = qr_mapping.get(scanned_id)
            if scanned_email and scanned_email in participants_data:
                participant = participants_data[scanned_email]

                # Check if scanned person is in the scanner's target list
                try:
                    is_target = False
                    convo_tip = "התחל בשיחה נעימה!"
                    if target_assignments_df is not None:
                        user_targets = target_assignments_df[target_assignments_df['scanner_id'] == scanner_id]
                        target_ids = user_targets['target_id'].tolist()
                        is_target = scanned_id in target_ids
                        if is_target:
                            target_row = user_targets[user_targets['target_id'] == scanned_id]
                            if not target_row.empty:
                                convo_tip = target_row['convo_tip'].iloc[0]
                    else:
                        # Fallback to simple dict
                        is_target = target_assignments.get(scanner_id) == scanned_id
                except Exception:
                    is_target = False
                    convo_tip = "התחל בשיחה נעימה!"

                # Update user stats
                if scanner_id not in user_stats:
                    user_stats[scanner_id] = {
                        'total_score': 0, 'scanned_users': [],
                        'found_target': False, 'completed_targets': []
                    }

                # Check if already scanned this person
                already_scanned = scanned_id in user_stats[scanner_id]['scanned_users']

                if already_scanned:
                    return jsonify({
                        "error": "כבר סרקת את המשתתף הזה!",
                        "is_target": is_target,
                        "points_earned": 0
                    }), 400

                # Calculate points
                if is_target:
                    points = 100  # 100 points per valid target
                    message = "🎯 מצאת יעד!"
                    bonuses = ["🎉 יעד נכון!", "⭐ +100 נקודות!", "✅ משימה הושלמה!"]
                    user_stats[scanner_id]['found_target'] = True

                    # Mark this specific target as found
                    if 'completed_targets' not in user_stats[scanner_id]:
                        user_stats[scanner_id]['completed_targets'] = []
                    user_stats[scanner_id]['completed_targets'].append(scanned_id)
                else:
                    points = 10  # 10 points for any scan
                    message = "👥 פגשת משתתף חדש!"
                    bonuses = ["🤝 משתתף חדש", "📈 +10 נקודות"]
                    # Don't show conversation tip for wrong targets
                    convo_tip = "זה לא אחד מהיעדים שלך. בדוק את רשימת המשימות."

                # Get job title from enhanced QR mapping
                job_title = "Unknown Role"
                try:
                    qr_df = pd.read_csv(os.path.join(BASE_DIR, 'qr_codes', 'qr_mapping.csv'))
                    scanned_row = qr_df[qr_df['user_id'] == scanned_id]
                    if not scanned_row.empty:
                        job_title = scanned_row['job_title'].iloc[0]
                except Exception:
                    pass

                # Update stats
                user_stats[scanner_id]['scanned_users'].append(scanned_id)
                user_stats[scanner_id]['total_score'] += points

                return jsonify({
                    "success": True,
                    "is_target": is_target,
                    "points_earned": points,
                    "total_score": user_stats[scanner_id]['total_score'],
                    "message": message,
                    "bonuses": bonuses,
                    "conversation_tip": convo_tip if is_target else "",
                    "scanned_user": {
                        "name": participant['full_name'],
                        "full_name": participant['full_name'],
                        "job_title": job_title,
                        "linkedin": participant.get('linkedin_url', ''),
                        "linkedin_url": participant.get('linkedin_url', ''),
                        "email": participant['email'],
                        "genre_color": participant.get('genre_color', 'blue')
                    },
                    "show_conversation_tip": is_target
                }), 200
            else:
                # Fallback for unknown QR codes — still award points
                if scanner_id not in user_stats:
                    user_stats[scanner_id] = {
                        'total_score': 0, 'scanned_users': [],
                        'found_target': False, 'completed_targets': []
                    }
                user_stats[scanner_id]['scanned_users'].append(scanned_id)
                user_stats[scanner_id]['total_score'] += 10
                return jsonify({
                    "success": True,
                    "is_target": False,
                    "points_earned": 10,
                    "total_score": user_stats[scanner_id]['total_score'],
                    "message": "👥 משתתף לא מזוהה",
                    "bonuses": ["🔍 משתתף לא זוהה", "📈 +10 נקודות"],
                    "conversation_tip": "",
                    "scanned_user": {
                        "name": f"משתתף {scanned_id}",
                        "full_name": f"משתתף {scanned_id}",
                        "linkedin": "",
                        "linkedin_url": "",
                        "email": ""
                    }
                }), 200

        # Get scanner user
        scanner_ref = db.collection('users').document(scanner_id)
        scanner = scanner_ref.get()

        if not scanner.exists:
            return jsonify({"error": "Scanner not found"}), 404

        scanner_data = scanner.to_dict()

        # Get scanned user
        scanned_ref = db.collection('users').document(scanned_id)
        scanned = scanned_ref.get()

        if not scanned.exists:
            return jsonify({"error": "Scanned user not found"}), 404

        scanned_data = scanned.to_dict()

        # Check if already scanned
        scanned_users = scanner_data.get('scanned_users', [])
        if scanned_id in scanned_users:
            return jsonify({
                "error": "You already scanned this person!",
                "is_target": False,
                "points": 0,
                "scanned_user": {
                    "name": scanned_data.get('full_name'),
                    "linkedin": scanned_data.get('linkedin_url')
                }
            }), 400

        # Process the scan
        result = scorer.process_scan(
            scanner_id=scanner_id,
            scanned_id=scanned_id,
            scanner_data=scanner_data,
            scanned_data=scanned_data
        )

        return jsonify(result), 200

    except Exception as e:
        print(f"Scan error: {str(e)}")
        return jsonify({"error": "Failed to process scan"}), 500

# ==================== CONVERSATION COMPLETE ====================


@app.route('/api/conversation/complete', methods=['POST'])
def complete_conversation():
    """
    Mark conversation as complete and award bonus points
    Body: { "user_id": "user_id_1" }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        # Demo mode fallback if Firebase is not available
        if db is None:
            # Validate user is a registered participant
            if user_id not in qr_mapping:
                return jsonify({"error": "User not registered in event"}), 404

            if user_id not in user_stats:
                user_stats[user_id] = {
                    'total_score': 0, 'scanned_users': [],
                    'found_target': False, 'completed_targets': []
                }

            user_stats[user_id]['total_score'] += 5
            new_score = user_stats[user_id]['total_score']

            return jsonify({
                "success": True,
                "points_earned": 5,
                "new_score": new_score
            }), 200

        # Award conversation completion bonus
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()

        if not user.exists:
            return jsonify({"error": "User not found"}), 404

        user_data = user.to_dict()
        current_score = user_data.get('current_score', 0)
        new_score = current_score + 5  # 5 points for completing conversation

        user_ref.update({
            'current_score': new_score
        })

        return jsonify({
            "success": True,
            "points_earned": 5,
            "new_score": new_score
        }), 200

    except Exception as e:
        print(f"Complete conversation error: {str(e)}")
        return jsonify({"error": "Failed to complete conversation"}), 500

# ==================== TEAMS ENDPOINT ====================


@app.route('/api/teams', methods=['GET'])
def get_teams():
    """Get team configuration from CSV file"""
    try:
        teams_file = os.path.join(BASE_DIR, 'data', 'teams.csv')
        if os.path.exists(teams_file):
            teams_df = pd.read_csv(teams_file)
            teams_list = []

            for _, row in teams_df.iterrows():
                teams_list.append({
                    "color": row['color'],
                    "name": row['name'],
                    "emoji": row['emoji'],
                    "description": row.get('description', '')
                })

            return jsonify({"teams": teams_list}), 200
        else:
            # Default teams if CSV doesn't exist
            default_teams = [
                {"color": "blue", "name": "Blue Team", "emoji": "💼", "description": "Default Blue Team"},
                {"color": "red", "name": "Red Team", "emoji": "❤️", "description": "Default Red Team"},
                {"color": "green", "name": "Green Team", "emoji": "💚", "description": "Default Green Team"},
                {"color": "yellow", "name": "Yellow Team", "emoji": "💛", "description": "Default Yellow Team"},
                {"color": "purple", "name": "Purple Team", "emoji": "💜", "description": "Default Purple Team"}
            ]
            return jsonify({"teams": default_teams}), 200

    except Exception as e:
        print(f"Teams error: {str(e)}")
        return jsonify({"error": "Failed to fetch teams"}), 500

# ==================== LEADERBOARD ====================


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get top 10 users by score"""
    try:
        # Demo mode fallback if Firebase is not available
        if db is None:
            leaderboard = []

            # Create leaderboard from user_stats and participants_data
            for user_id, stats in user_stats.items():
                user_email = qr_mapping.get(user_id)
                if user_email and user_email in participants_data:
                    participant = participants_data[user_email]
                    leaderboard.append({
                        'id': user_id,
                        'name': participant['full_name'],
                        'score': stats['total_score'],
                        'color': participant.get('genre_color', 'blue'),
                        'linkedin': participant.get('linkedin_url', ''),
                        'found_target': stats.get('found_target', False),
                        'scanned_count': len(stats.get('scanned_users', []))
                    })

            # Only show users who have actually played
            leaderboard = [e for e in leaderboard if e['score'] > 0]
            # Sort: score DESC, then most scans (tiebreaker), then name (stable)
            leaderboard.sort(key=lambda x: (-x['score'], -x['scanned_count'], x['name']))
            return jsonify(leaderboard[:10]), 200

        users_ref = db.collection('users')
        query = users_ref.order_by('current_score', direction=firestore.Query.DESCENDING).limit(10)

        leaderboard = []
        for doc in query.stream():
            user_data = doc.to_dict()
            leaderboard.append({
                'id': doc.id,
                'name': user_data.get('full_name'),
                'score': user_data.get('current_score', 0),
                'color': user_data.get('genre_color'),
                'linkedin': user_data.get('linkedin_url')
            })

        return jsonify(leaderboard), 200

    except Exception as e:
        print(f"Leaderboard error: {str(e)}")
        return jsonify({"error": "Failed to fetch leaderboard"}), 500

# ==================== EVENT STATS ====================


@app.route('/api/stats', methods=['GET'])
def get_event_stats():
    """Get real-time event statistics"""
    try:
        # Demo mode fallback if Firebase is not available
        if db is None:
            total_participants = len(participants_data)
            active_users = len([u for u in user_stats.values() if u['total_score'] > 0])
            total_scans = sum(len(u.get('scanned_users', [])) for u in user_stats.values())
            targets_found = len([u for u in user_stats.values() if u.get('found_target', False)])

            color_stats = {}
            for email, participant in participants_data.items():
                color = participant.get('genre_color', 'blue')
                if color not in color_stats:
                    color_stats[color] = {'total': 0, 'active': 0}
                color_stats[color]['total'] += 1

                # Check if this color has active users
                user_id = None
                for uid, uemail in qr_mapping.items():
                    if uemail == email:
                        user_id = uid
                        break

                if user_id and user_id in user_stats and user_stats[user_id]['total_score'] > 0:
                    color_stats[color]['active'] += 1

            return jsonify({
                "total_participants": total_participants,
                "active_users": active_users,
                "total_scans": total_scans,
                "targets_found": targets_found,
                "completion_rate": round((targets_found / total_participants * 100) if total_participants > 0 else 0, 1),
                "color_stats": color_stats,
                "top_scanners": [
                    {
                        "name": participants_data[qr_mapping[uid]]['full_name'],
                        "scans": len(stats.get('scanned_users', []))
                    }
                    for uid, stats in sorted(user_stats.items(),
                                             key=lambda x: len(x[1].get('scanned_users', [])),
                                             reverse=True)[:3]
                    if qr_mapping.get(uid) in participants_data
                ]
            }), 200

        # Original Firebase implementation
        # Total scans
        scans_ref = db.collection('scans')
        total_scans = len(list(scans_ref.stream()))

        # Active users (users with at least 1 scan)
        users_ref = db.collection('users')
        active_users = 0

        color_stats = {
            'red': 0,
            'blue': 0,
            'green': 0,
            'yellow': 0
        }

        for doc in users_ref.stream():
            user_data = doc.to_dict()
            scanned = user_data.get('scanned_users', [])
            if len(scanned) > 0:
                active_users += 1
                color = user_data.get('genre_color', 'red')
                if color in color_stats:
                    color_stats[color] += len(scanned)

        return jsonify({
            'total_scans': total_scans,
            'active_users': active_users,
            'color_heatmap': color_stats
        }), 200

    except Exception as e:
        print(f"Stats error: {str(e)}")
        return jsonify({"error": "Failed to fetch stats"}), 500

# ==================== ALL MISSIONS ====================


@app.route('/api/missions', methods=['GET'])
def get_all_missions():
    """Get all participant missions/targets"""
    try:
        # Demo mode fallback if Firebase is not available
        if db is None:
            missions = []

            # Load QR mapping for additional data like job titles
            qr_data = {}
            qr_file = os.path.join(BASE_DIR, 'qr_codes', 'qr_mapping.csv')
            if os.path.exists(qr_file):
                qr_df = pd.read_csv(qr_file)
                for _, row in qr_df.iterrows():
                    qr_data[row['user_id']] = {
                        'job_title': row.get('job_title', 'Unknown'),
                        'genre_color': row.get('genre_color', 'blue'),
                        'full_name': row.get('full_name', 'Unknown')
                    }

            # Create missions list from target assignments and participant data
            for scanner_id, target_id in target_assignments.items():
                scanner_email = qr_mapping.get(scanner_id)
                target_email = qr_mapping.get(target_id)

                if scanner_email and target_email and scanner_email in participants_data and target_email in participants_data:
                    scanner = participants_data[scanner_email]
                    target = participants_data[target_email]
                    scanner_qr = qr_data.get(scanner_id, {})
                    target_qr = qr_data.get(target_id, {})

                    # Check if target was found
                    found = user_stats.get(scanner_id, {}).get('found_target', False)

                    missions.append({
                        "scanner_id": scanner_id,
                        "scanner_name": scanner['full_name'],
                        "scanner_color": scanner_qr.get('genre_color', scanner.get('genre_color', 'blue')),
                        "scanner_job": scanner_qr.get('job_title', 'Unknown'),
                        "target_id": target_id,
                        "target_name": target['full_name'],
                        "target_color": target_qr.get('genre_color', target.get('genre_color', 'blue')),
                        "target_job": target_qr.get('job_title', 'Unknown'),
                        "found": found,
                        "convo_tip": target.get('convo_tip', 'Start a conversation!')
                    })

            return jsonify(missions), 200

        # Original Firebase implementation would go here
        return jsonify([]), 200

    except Exception as e:
        print(f"Missions error: {str(e)}")
        return jsonify({"error": "Failed to fetch missions"}), 500

# ==================== FRONTEND ROUTES ====================


from flask import send_from_directory


@app.route('/frontend/<path:filename>')
def serve_frontend(filename):
    """Serve frontend files"""
    try:
        frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
        return send_from_directory(frontend_path, filename)
    except Exception:
        return jsonify({"error": f"File not found: {filename}"}), 404


@app.route('/')
def index():
    """Root route - redirect to participant app"""
    return '''
    <h1>🎯 Mystery Networking System</h1>
    <h2>Available Apps:</h2>
    <ul>
        <li><a href="/frontend/participant.html">🎯 Participant App</a></li>
        <li><a href="/frontend/dashboard.html">📊 Live Dashboard</a></li>
        <li><a href="/frontend/admin.html">👥 Admin Panel</a></li>
    </ul>
    '''

# ==================== ADMIN ENDPOINTS ====================


@app.route('/api/admin/upload-config', methods=['POST', 'OPTIONS'])
def upload_config():
    """Upload and save configuration files (teams, participants, targets)"""
    global participants_data, qr_mapping, email_to_userid, target_assignments  # noqa: F824

    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200

    try:
        import uuid
        data = request.json
        saved_files = []
        errors = []
        updated_memory = []

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if os.environ.get('K_SERVICE'):
            base_dir = '/tmp'

        # Process participants
        if 'participants' in data and data['participants']:
            try:
                new_qr_mapping = {}
                new_email_to_userid = {}
                new_participants = {}

                for p in data['participants']:
                    user_id = p.get('user_id') or str(uuid.uuid4())[:8]
                    email = p.get('email', '').lower().strip()
                    new_qr_mapping[user_id] = email
                    new_email_to_userid[email] = user_id
                    new_participants[email] = {
                        'full_name': p.get('full_name', ''),
                        'email': email,
                        'job_title': p.get('job_title', ''),
                        'genre_color': p.get('genre_color', ''),
                        'linkedin_url': p.get('linkedin_url', ''),
                        'convo_tip': p.get('convo_tip', 'Start a conversation!')
                    }

                qr_mapping.update(new_qr_mapping)
                email_to_userid.update(new_email_to_userid)
                participants_data.update(new_participants)
                updated_memory.append(f'participants ({len(data["participants"])})')
                web_log('SUCCESS', f'Updated in-memory data with {len(data["participants"])} participants')

                try:
                    qr_file = os.path.join(base_dir, 'qr_codes', 'qr_mapping.csv')
                    os.makedirs(os.path.dirname(qr_file), exist_ok=True)
                    participants_df = pd.DataFrame(data['participants'])
                    if 'user_id' not in participants_df.columns:
                        participants_df['user_id'] = [p.get('user_id') or str(uuid.uuid4())[:8] for p in data['participants']]
                    participants_df.to_csv(qr_file, index=False)
                    saved_files.append('qr_codes/qr_mapping.csv')
                except Exception as file_err:
                    web_log('WARNING', f'Could not write qr_mapping.csv: {str(file_err)}')

            except Exception as e:
                errors.append(f'participants: {str(e)}')

        # Process targets
        if 'targets' in data and data['targets']:
            try:
                for t in data['targets']:
                    scanner_id = t.get('scanner_id', '')
                    if scanner_id:
                        if scanner_id not in target_assignments or not isinstance(target_assignments[scanner_id], list):
                            target_assignments[scanner_id] = []
                        target_assignments[scanner_id].append({
                            'target_id': t.get('target_id', ''),
                            'target_name': t.get('target_name', ''),
                            'target_color': t.get('target_color', ''),
                            'target_job_title': t.get('target_job_title', ''),
                            'convo_tip': t.get('convo_tip', '')
                        })

                updated_memory.append(f'targets ({len(data["targets"])})')
                web_log('SUCCESS', f'Updated in-memory data with {len(data["targets"])} target assignments')

                try:
                    targets_file = os.path.join(base_dir, 'qr_codes', 'target_assignments.csv')
                    os.makedirs(os.path.dirname(targets_file), exist_ok=True)
                    targets_df = pd.DataFrame(data['targets'])
                    targets_df.to_csv(targets_file, index=False)
                    saved_files.append('qr_codes/target_assignments.csv')
                except Exception as file_err:
                    web_log('WARNING', f'Could not write target_assignments.csv: {str(file_err)}')

            except Exception as e:
                errors.append(f'targets: {str(e)}')

        # Process teams
        if 'teams' in data and data['teams']:
            try:
                teams_file = os.path.join(base_dir, 'data', 'teams.csv')
                os.makedirs(os.path.dirname(teams_file), exist_ok=True)
                teams_df = pd.DataFrame(data['teams'])
                teams_df.to_csv(teams_file, index=False)
                saved_files.append('data/teams.csv')
                updated_memory.append(f'teams ({len(data["teams"])})')
                web_log('SUCCESS', f'Saved teams.csv with {len(data["teams"])} teams')
            except Exception as e:
                errors.append(f'teams: {str(e)}')

        response_data = {
            "status": "success" if not errors else "partial",
            "message": f"Updated: {', '.join(updated_memory)}" if updated_memory else "No data to update",
            "updated_memory": updated_memory,
            "saved_files": saved_files,
            "participants_count": len(participants_data),
            "qr_mappings_count": len(qr_mapping)
        }

        if errors:
            response_data["errors"] = errors
            return jsonify(response_data), 207

        return jsonify(response_data), 200

    except Exception as e:
        web_log('ERROR', f'Config upload failed: {str(e)}')
        return jsonify({"status": "error", "message": "Failed to upload configuration"}), 500


@app.route('/api/admin/generate-targets', methods=['POST', 'OPTIONS'])
def generate_targets():
    """Generate target assignments for all participants"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200

    try:
        import random
        data = request.json
        participants = data.get('participants', [])
        targets_per_person = data.get('targets_per_person', 3)

        if not participants:
            return jsonify({"error": "No participants provided"}), 400

        assignments = []
        for p in participants:
            p_id = p.get('user_id') or p.get('email', '').split('@')[0]
            potential_targets = [t for t in participants if t.get('email') != p.get('email')]
            random.shuffle(potential_targets)
            selected_targets = potential_targets[:targets_per_person]

            for target in selected_targets:
                t_id = target.get('user_id') or target.get('email', '').split('@')[0]
                assignments.append({
                    'scanner_id': p_id,
                    'target_id': t_id,
                    'target_name': target.get('full_name', ''),
                    'target_color': target.get('genre_color', ''),
                    'target_job_title': target.get('job_title', ''),
                    'convo_tip': f"Ask about their role as {target.get('job_title', 'professional')}"
                })

        return jsonify({
            "status": "success",
            "assignments": assignments,
            "count": len(assignments)
        }), 200

    except Exception as e:
        web_log('ERROR', f'Target generation failed: {str(e)}')
        return jsonify({"error": "Failed to generate targets"}), 500


def _reinitialize_user_stats():
    """Re-initialize user_stats for all known participants."""
    user_stats.clear()
    for user_id in qr_mapping.keys():
        user_stats[user_id] = {
            'total_score': 0,
            'scanned_users': [],
            'found_target': False,
            'completed_targets': []
        }


@app.route('/api/admin/reset-stats', methods=['POST'])
def reset_stats():
    """Reset all user stats"""
    _reinitialize_user_stats()
    save_user_stats()
    web_log('INFO', f'All user stats reset ({len(user_stats)} users re-initialized)')
    return jsonify({"message": "Stats reset successfully"}), 200


@app.route('/api/admin/reset-event', methods=['POST'])
def reset_event():
    """Complete Event Reset - Re-initialize all user stats for new event"""
    try:
        _reinitialize_user_stats()
        save_user_stats()
        web_logs.clear()
        web_log('INFO', f'COMPLETE EVENT RESET - Re-initialized {len(user_stats)} users')

        return jsonify({
            "message": f"Event reset complete! Initialized {len(user_stats)} users.",
            "status": "success",
            "reset_time": str(datetime.now()),
            "users_initialized": len(user_stats)
        }), 200

    except Exception as e:
        web_log('ERROR', f'Event reset failed: {str(e)}')
        return jsonify({"error": str(e)}), 500

# ==================== RUN SERVER ====================


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🚀 Mystery Networking Backend Running on http://localhost:{port}")
    print("📊 Admin Panel: Open frontend/admin.html in browser")
    print("🎯 Participant App: Open frontend/participant.html in browser")
    print("📺 Dashboard: Open frontend/dashboard.html in browser\n")
    app.run(debug=True, host='0.0.0.0', port=port)
