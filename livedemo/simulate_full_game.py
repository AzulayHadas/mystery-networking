"""Full game simulation against livedemo server — all 6 players play a complete event."""
import requests

BASE = 'http://localhost:5000/api'

# Reset event first
requests.post(f'{BASE}/admin/reset-event')

PLAYERS = {
    'a1b2c3d4': 'Alice Cohen',
    'e5f6a7b8': 'Bob Levy',
    'c9d0e1f2': 'Carol Shapira',
    'a3b4c5d6': 'Dan Mizrahi',
    'e7f8a9b0': 'Eva Katz',
    'c1d2e3f4': 'Frank Peretz',
}

EMAILS = {
    'a1b2c3d4': 'alice@demo.com',
    'e5f6a7b8': 'bob@demo.com',
    'c9d0e1f2': 'carol@demo.com',
    'a3b4c5d6': 'dan@demo.com',
    'e7f8a9b0': 'eva@demo.com',
    'c1d2e3f4': 'frank@demo.com',
}

print('=' * 60)
print('  MYSTERY NETWORKING - FULL GAME SIMULATION')
print('=' * 60)

# Phase 1: Everyone logs in
print('\n--- PHASE 1: LOGIN ---')
for uid, name in PLAYERS.items():
    r = requests.post(f'{BASE}/auth/login', json={'email': EMAILS[uid]})
    d = r.json()
    print(f'  {name} logged in (id={d["user"]["id"]})')

# Phase 2: Check everyone's targets
print('\n--- PHASE 2: TARGET ASSIGNMENTS ---')
player_targets = {}
for uid, name in PLAYERS.items():
    r = requests.get(f'{BASE}/user/{uid}/targets')
    targets = r.json()['targets']
    player_targets[uid] = [t['target_id'] for t in targets]
    target_names = [t['target_name'] for t in targets]
    print(f'  {name} must find: {", ".join(target_names)}')

# Phase 3: Event simulation - players scan each other
print('\n--- PHASE 3: SCANNING ROUND 1 ---')
scan_actions = [
    ('a1b2c3d4', 'e5f6a7b8', 'Alice scans Bob'),
    ('e5f6a7b8', 'a3b4c5d6', 'Bob scans Dan'),
    ('c9d0e1f2', 'e7f8a9b0', 'Carol scans Eva'),
    ('a3b4c5d6', 'a1b2c3d4', 'Dan scans Alice'),
    ('e7f8a9b0', 'c9d0e1f2', 'Eva scans Carol'),
    ('c1d2e3f4', 'e5f6a7b8', 'Frank scans Bob'),
]

for scanner, scanned, desc in scan_actions:
    r = requests.post(f'{BASE}/scan', json={'scanner_id': scanner, 'scanned_id': scanned})
    d = r.json()
    target_str = 'TARGET!' if d.get('is_target') else 'not target'
    print(f'  {desc}: {target_str} +{d.get("points_earned", 0)}pts (total: {d.get("total_score", 0)})')

# Phase 4: Some conversations completed
print('\n--- PHASE 4: CONVERSATIONS ---')
for uid in ['a1b2c3d4', 'e5f6a7b8', 'c9d0e1f2']:
    r = requests.post(f'{BASE}/conversation/complete', json={'user_id': uid})
    d = r.json()
    print(f'  {PLAYERS[uid]} completed conversation: +{d["points_earned"]}pts (total: {d["new_score"]})')

# Phase 5: More scanning
print('\n--- PHASE 5: SCANNING ROUND 2 ---')
scan_actions_2 = [
    ('a1b2c3d4', 'c1d2e3f4', 'Alice scans Frank'),
    ('a1b2c3d4', 'a3b4c5d6', 'Alice scans Dan'),
    ('e5f6a7b8', 'c1d2e3f4', 'Bob scans Frank'),
    ('c9d0e1f2', 'a1b2c3d4', 'Carol scans Alice'),
    ('a3b4c5d6', 'e7f8a9b0', 'Dan scans Eva'),
    ('e7f8a9b0', 'a1b2c3d4', 'Eva scans Alice'),
    ('c1d2e3f4', 'a1b2c3d4', 'Frank scans Alice'),
]

for scanner, scanned, desc in scan_actions_2:
    r = requests.post(f'{BASE}/scan', json={'scanner_id': scanner, 'scanned_id': scanned})
    d = r.json()
    if r.status_code == 200:
        target_str = 'TARGET!' if d.get('is_target') else 'not target'
        print(f'  {desc}: {target_str} +{d.get("points_earned", 0)}pts (total: {d.get("total_score", 0)})')
    else:
        print(f'  {desc}: BLOCKED - {d.get("error", "unknown")}')

# Phase 6: More conversations
print('\n--- PHASE 6: MORE CONVERSATIONS ---')
for uid in ['a1b2c3d4', 'a3b4c5d6', 'e7f8a9b0', 'c1d2e3f4']:
    r = requests.post(f'{BASE}/conversation/complete', json={'user_id': uid})
    d = r.json()
    print(f'  {PLAYERS[uid]}: +{d["points_earned"]}pts (total: {d["new_score"]})')

# Phase 7: Final leaderboard
print('\n--- PHASE 7: FINAL LEADERBOARD ---')
r = requests.get(f'{BASE}/leaderboard')
lb = r.json()
print(f'{"Rank":<6} {"Name":<20} {"Score":<8} {"Scans":<8} {"Color":<8}')
print('-' * 50)
for i, e in enumerate(lb):
    print(f'#{i+1:<5} {e["name"]:<20} {e["score"]:<8} {e["scanned_count"]:<8} {e["color"]:<8}')

# Phase 8: Event stats
print('\n--- PHASE 8: EVENT STATISTICS ---')
r = requests.get(f'{BASE}/stats')
s = r.json()
print(f'  Total Participants: {s["total_participants"]}')
print(f'  Active Users:       {s["active_users"]}')
print(f'  Total Scans:        {s["total_scans"]}')
print(f'  Targets Found:      {s["targets_found"]}')
print(f'  Completion Rate:    {s["completion_rate"]}%')

# Phase 9: Team breakdown
print('\n--- PHASE 9: TEAM SCORES ---')
r = requests.get(f'{BASE}/teams')
teams = r.json()['teams']
team_scores = {}
for e in lb:
    color = e['color']
    team_scores[color] = team_scores.get(color, 0) + e['score']
for t in teams:
    score = team_scores.get(t['color'], 0)
    print(f'  {t["name"]} ({t["color"]}): {score}pts')

# Winner announcement
print('\n' + '=' * 60)
winner = lb[0]
print(f'  WINNER: {winner["name"]} with {winner["score"]} points!')
print(f'  {winner["scanned_count"]} people scanned, team {winner["color"]}')
print('=' * 60)
