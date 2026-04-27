#!/usr/bin/env python3
"""
Full game simulation with 6 trial participants.
Starts the Flask app, plays a complete event, and prints a final report.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from unittest.mock import patch
import json

# Boot app in demo mode
with patch('firebase_admin.credentials.Certificate', side_effect=Exception("no creds")), \
     patch('firebase_admin.initialize_app'):
    if 'app' in sys.modules:
        del sys.modules['app']
    import app as app_module

# Wire up trial data
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
qr_df = pd.read_csv(os.path.join(BASE, 'qr_codes_trial', 'qr_mapping.csv'))
assign_df = pd.read_csv(os.path.join(BASE, 'qr_codes_trial', 'target_assignments.csv'))
parts_df = pd.read_csv(os.path.join(BASE, 'data', 'participants_trial.csv'))

app_module.db = None
app_module.scorer = None
app_module.qr_mapping = dict(zip(qr_df['user_id'], qr_df['email']))
app_module.email_to_userid = dict(zip(qr_df['email'], qr_df['user_id']))
app_module.target_assignments = dict(zip(assign_df['scanner_id'], assign_df['target_id']))
app_module.target_assignments_df = assign_df

participants = {}
for _, row in parts_df.iterrows():
    email = row['email'].lower().strip()
    participants[email] = {
        'full_name': row['full_name'],
        'email': email,
        'linkedin_url': row.get('linkedin_url', ''),
        'genre_color': row.get('genre_color', 'blue'),
        'convo_tip': row.get('convo_tip', ''),
    }
app_module.participants_data = participants

# Init user stats
app_module.user_stats = {}
for uid in app_module.qr_mapping:
    app_module.user_stats[uid] = {'total_score': 0, 'scanned_users': [], 'found_target': False}

client = app_module.app.test_client()

# ── Helpers ──
def login(email):
    r = client.post('/api/auth/login', json={'email': email})
    d = r.get_json()
    assert d['success'], f"Login failed for {email}: {d}"
    return d['user']

def scan(scanner_id, scanned_id):
    r = client.post('/api/scan', json={'scanner_id': scanner_id, 'scanned_id': scanned_id})
    return r.status_code, r.get_json()

def convo(user_id):
    r = client.post('/api/conversation/complete', json={'user_id': user_id})
    return r.get_json()

# ── Build player roster ──
PLAYERS = {}
for _, row in qr_df.iterrows():
    uid = row['user_id']
    PLAYERS[uid] = {'id': uid, 'name': row['full_name'], 'email': row['email']}

# Get each player's targets
PLAYER_TARGETS = {}
for uid in PLAYERS:
    targets = assign_df[assign_df['scanner_id'] == uid]
    PLAYER_TARGETS[uid] = list(targets.itertuples(index=False))

# ═══════════════════════════════════════════
#  GAME SIMULATION
# ═══════════════════════════════════════════
print("=" * 60)
print("  🎯 MYSTERY NETWORKING — FULL GAME SIMULATION")
print("=" * 60)

# Phase 1: All players login
print("\n📋 PHASE 1: Player Login")
print("-" * 40)
for uid, p in PLAYERS.items():
    user = login(p['email'])
    print(f"  ✅ {user['full_name']} logged in (score: {user.get('current_score', 0)})")

# Phase 2: Show assignments
print("\n🎯 PHASE 2: Target Assignments")
print("-" * 40)
for uid, p in PLAYERS.items():
    targets = PLAYER_TARGETS[uid]
    target_names = [t.target_name for t in targets]
    print(f"  {p['name']} → must find: {', '.join(target_names)}")

# Phase 3: Game play — simulate realistic event behavior
print("\n🎮 PHASE 3: Event Gameplay")
print("-" * 40)

# Round 1: Alice is aggressive — finds all 3 targets fast
alice = '7963d4da'
for t in PLAYER_TARGETS[alice]:
    code, data = scan(alice, t.target_id)
    status = "🎯 TARGET!" if data.get('is_target') else "👥 met"
    print(f"  Alice scans {t.target_name}: {status} (+{data.get('points_earned', 0)} pts)")
# Alice also completes conversations
for _ in range(3):
    convo(alice)
print(f"  Alice completes 3 conversations (+15 pts)")

# Round 2: Bob finds 2 of 3 targets and has 1 conversation
bob = '647d03d2'
for t in PLAYER_TARGETS[bob][:2]:
    code, data = scan(bob, t.target_id)
    print(f"  Bob scans {t.target_name}: 🎯 TARGET! (+{data.get('points_earned', 0)} pts)")
convo(bob)
print(f"  Bob completes 1 conversation (+5 pts)")

# Round 3: Carol finds 1 target, scans 1 non-target
carol = 'a93eb187'
t = PLAYER_TARGETS[carol][0]
code, data = scan(carol, t.target_id)
print(f"  Carol scans {t.target_name}: 🎯 TARGET! (+{data.get('points_earned', 0)} pts)")
# Carol scans Eva (not her target)
code, data = scan(carol, '107914b0')
print(f"  Carol scans Eva Katz: 👥 non-target (+{data.get('points_earned', 0)} pts)")
convo(carol)
print(f"  Carol completes 1 conversation (+5 pts)")

# Round 4: Dan finds 1 target
dan = '1c5e4799'
t = PLAYER_TARGETS[dan][0]
code, data = scan(dan, t.target_id)
print(f"  Dan scans {t.target_name}: 🎯 TARGET! (+{data.get('points_earned', 0)} pts)")

# Round 5: Eva scans 2 people but neither is her target
eva = '107914b0'
code, data = scan(eva, carol)  # Carol is not Eva's target
print(f"  Eva scans Carol Shapira: 👥 non-target (+{data.get('points_earned', 0)} pts)")
code, data = scan(eva, bob)
print(f"  Eva scans Bob Levy: 👥 non-target (+{data.get('points_earned', 0)} pts)")

# Round 6: Frank finds all 3 targets + convos
frank = '7b4d256b'
for t in PLAYER_TARGETS[frank]:
    code, data = scan(frank, t.target_id)
    print(f"  Frank scans {t.target_name}: 🎯 TARGET! (+{data.get('points_earned', 0)} pts)")
for _ in range(2):
    convo(frank)
print(f"  Frank completes 2 conversations (+10 pts)")

# ── Phase 4: Final Results ──
print("\n" + "=" * 60)
print("  🏆 FINAL RESULTS")
print("=" * 60)

r = client.get('/api/leaderboard')
lb = r.get_json()

print("\n  LEADERBOARD")
print("  " + "-" * 50)
medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣']
for i, entry in enumerate(lb):
    medal = medals[i] if i < len(medals) else f"{i+1}."
    target_icon = " 🎯" if entry.get('found_target') else ""
    scans = entry.get('scanned_count', 0)
    print(f"  {medal} {entry['name']:20s}  {entry['score']:>4d} pts  ({scans} scans){target_icon}")

# Stats
r = client.get('/api/stats')
stats = r.get_json()

print(f"\n  EVENT STATISTICS")
print("  " + "-" * 50)
print(f"  Total participants:  {stats['total_participants']}")
print(f"  Active players:      {stats['active_users']}")
print(f"  Total scans:         {stats['total_scans']}")
print(f"  Targets found:       {stats['targets_found']}")
print(f"  Completion rate:     {stats['completion_rate']}%")

# Color breakdown
if 'color_stats' in stats:
    print(f"\n  TEAM BREAKDOWN")
    print("  " + "-" * 50)
    team_names = {'blue': '💻 Tech Wizards', 'red': '🎨 Creative Minds', 'green': '🌟 Leaders'}
    for color, s in stats['color_stats'].items():
        name = team_names.get(color, color)
        print(f"  {name:25s}  {s['total']} members, {s['active']} active")

# Per-player summary
print(f"\n  PLAYER DETAILS")
print("  " + "-" * 50)
for uid, p in PLAYERS.items():
    s = app_module.user_stats.get(uid, {})
    targets = PLAYER_TARGETS[uid]
    completed = s.get('completed_targets', [])
    n_found = len(completed)
    n_total = len(targets)
    print(f"  {p['name']:20s}  Score: {s.get('total_score', 0):>4d}  "
          f"Targets: {n_found}/{n_total}  Scans: {len(s.get('scanned_users', []))}")

# Winner
winner = lb[0]
print(f"\n  {'=' * 50}")
print(f"  🏆 WINNER: {winner['name']} with {winner['score']} points!")
print(f"  {'=' * 50}")
