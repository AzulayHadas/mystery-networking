"""Quick smoke test for the livedemo server."""
import requests

BASE = 'http://localhost:5000/api'
results = []

def check(name, passed):
    results.append((name, passed))
    status = 'PASS' if passed else 'FAIL'
    print(f'  [{status}] {name}')

print('=== LIVEDEMO API SMOKE TEST ===\n')

# 1. Health
r = requests.get(f'{BASE}/health')
check('Health check', r.status_code == 200 and r.json()['status'] == 'ok')

# 2. Emails
r = requests.get(f'{BASE}/participants/emails')
emails = r.json()['emails']
check(f'Emails ({len(emails)} found)', len(emails) == 6)

# 3. Login
r = requests.post(f'{BASE}/auth/login', json={'email': 'alice@demo.com'})
d = r.json()
alice_id = d['user']['id']
check(f'Login Alice (id={alice_id})', d['success'] and d['user']['full_name'] == 'Alice Cohen')

# 4. Targets
r = requests.get(f'{BASE}/user/{alice_id}/targets')
targets = r.json()['targets']
check(f'Alice has {len(targets)} targets', len(targets) == 3)

# 5. Scan target
r = requests.post(f'{BASE}/scan', json={'scanner_id': alice_id, 'scanned_id': 'e5f6a7b8'})
d = r.json()
check(f'Scan target: is_target={d.get("is_target")} pts={d.get("points_earned")}',
      d.get('is_target') == True and d.get('points_earned') == 100)

# 6. Scan non-target
r = requests.post(f'{BASE}/scan', json={'scanner_id': alice_id, 'scanned_id': 'c9d0e1f2'})
d = r.json()
check(f'Scan non-target: is_target={d.get("is_target")} pts={d.get("points_earned")}',
      d.get('is_target') == False and d.get('points_earned') == 10)

# 7. Duplicate scan
r = requests.post(f'{BASE}/scan', json={'scanner_id': alice_id, 'scanned_id': 'e5f6a7b8'})
check('Duplicate scan blocked', r.status_code == 400)

# 8. Self scan
r = requests.post(f'{BASE}/scan', json={'scanner_id': alice_id, 'scanned_id': alice_id})
check('Self-scan blocked', r.status_code == 400)

# 9. Conversation
r = requests.post(f'{BASE}/conversation/complete', json={'user_id': alice_id})
d = r.json()
check(f'Conversation: +{d["points_earned"]}pts total={d["new_score"]}',
      d['points_earned'] == 5 and d['new_score'] == 115)

# 10. Leaderboard
r = requests.get(f'{BASE}/leaderboard')
lb = r.json()
check(f'Leaderboard: {len(lb)} entries, top={lb[0]["name"]} {lb[0]["score"]}pts',
      len(lb) >= 1 and lb[0]['score'] == 115)

# 11. Stats
r = requests.get(f'{BASE}/stats')
s = r.json()
check(f'Stats: {s["total_participants"]}p {s["active_users"]}a {s["total_scans"]}s',
      s['total_participants'] == 6 and s['total_scans'] == 2)

# 12. Teams
r = requests.get(f'{BASE}/teams')
teams = r.json()['teams']
check(f'Teams: {len(teams)}', len(teams) == 3)

# 13. Missions
r = requests.get(f'{BASE}/missions')
missions = r.json()
check(f'Missions: {len(missions)}', len(missions) >= 6)

# 14. Frontend served
r = requests.get('http://localhost:5000/frontend/participant.html')
check('Frontend HTML served', r.status_code == 200 and '<html' in r.text.lower())

# 15. Multi-player game
print('\n--- Multi-player round ---')
# Bob scans his target Dan
r = requests.post(f'{BASE}/scan', json={'scanner_id': 'e5f6a7b8', 'scanned_id': 'a3b4c5d6'})
d = r.json()
check(f'Bob scans Dan (target): pts={d.get("points_earned")}', d.get('is_target') == True)

# Carol scans Eva
r = requests.post(f'{BASE}/scan', json={'scanner_id': 'c9d0e1f2', 'scanned_id': 'e7f8a9b0'})
d = r.json()
check(f'Carol scans Eva: pts={d.get("points_earned")}', r.status_code == 200)

# Final leaderboard
r = requests.get(f'{BASE}/leaderboard')
lb = r.json()
print('\n--- Final Leaderboard ---')
for i, e in enumerate(lb):
    print(f'  #{i+1} {e["name"]}: {e["score"]}pts ({e["scanned_count"]} scans)')

# 16. Reset
r = requests.post(f'{BASE}/admin/reset-event')
check('Event reset', r.status_code == 200)

r = requests.get(f'{BASE}/leaderboard')
check('Leaderboard empty after reset', len(r.json()) == 0)

# Summary
print(f'\n{"="*50}')
passed = sum(1 for _, p in results if p)
total = len(results)
print(f'RESULTS: {passed}/{total} passed')
if passed == total:
    print('ALL TESTS PASSED!')
else:
    for name, p in results:
        if not p:
            print(f'  FAILED: {name}')
