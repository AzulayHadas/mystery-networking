"""Full game flow E2E test against running backend.
Run with: pytest test_full_game.py -m e2e
Requires: Server running on localhost:5000
"""
import requests
import json
import pytest

BASE = 'http://localhost:5000/api'

@pytest.mark.e2e
def test_full_game():
    print('=== 1. HEALTH CHECK ===')
    r = requests.get(f'{BASE}/health')
    print(f'  Status: {r.status_code}')
    print(f'  Body: {r.json()}')
    assert r.status_code == 200

    print('\n=== 2. UPLOAD CONFIG ===')
    payload = {
        'participants': [
            {'user_id': 'test_001', 'email': 'alice@test.com', 'full_name': 'Alice Cohen',
             'job_title': 'Developer', 'genre_color': 'blue', 'linkedin_url': 'https://linkedin.com/in/alice'},
            {'user_id': 'test_002', 'email': 'bob@test.com', 'full_name': 'Bob Levi',
             'job_title': 'Designer', 'genre_color': 'red', 'linkedin_url': 'https://linkedin.com/in/bob'},
            {'user_id': 'test_003', 'email': 'charlie@test.com', 'full_name': 'Charlie Dahan',
             'job_title': 'PM', 'genre_color': 'green', 'linkedin_url': 'https://linkedin.com/in/charlie'}
        ],
        'targets': [
            {'scanner_id': 'test_001', 'target_id': 'test_002', 'target_name': 'Bob Levi',
             'target_color': 'red', 'target_job_title': 'Designer', 'convo_tip': 'Ask about design trends'},
            {'scanner_id': 'test_002', 'target_id': 'test_003', 'target_name': 'Charlie Dahan',
             'target_color': 'green', 'target_job_title': 'PM', 'convo_tip': 'Ask about project mgmt'},
            {'scanner_id': 'test_003', 'target_id': 'test_001', 'target_name': 'Alice Cohen',
             'target_color': 'blue', 'target_job_title': 'Developer', 'convo_tip': 'Ask about coding'}
        ],
        'teams': [
            {'color': 'blue', 'name': 'Tech Wizards', 'emoji': '\U0001f4bb', 'description': 'Tech Team'},
            {'color': 'red', 'name': 'Creative Minds', 'emoji': '\U0001f3a8', 'description': 'Design Team'},
            {'color': 'green', 'name': 'Leaders', 'emoji': '\U0001f31f', 'description': 'PM Team'}
        ]
    }
    r = requests.post(f'{BASE}/admin/upload-config', json=payload)
    print(f'  Status: {r.status_code}')
    result = r.json()
    print(f'  Updated: {result.get("updated_memory")}')
    print(f'  Participants count: {result.get("participants_count")}')
    assert r.status_code == 200
    assert result['status'] == 'success'

    print('\n=== 3. GET PARTICIPANT EMAILS (autocomplete) ===')
    r = requests.get(f'{BASE}/participants/emails')
    print(f'  Status: {r.status_code}')
    emails = r.json()['emails']
    print(f'  Emails: {emails}')
    assert 'alice@test.com' in emails
    assert 'bob@test.com' in emails

    print('\n=== 4. LOGIN as Alice ===')
    r = requests.post(f'{BASE}/auth/login', json={'email': 'alice@test.com'})
    print(f'  Status: {r.status_code}')
    data = r.json()
    user = data.get('user', {})
    print(f'  User: {user.get("full_name")} (ID: {user.get("id")})')
    assert r.status_code == 200
    assert data['success'] is True

    print('\n=== 5. GET ALICE TARGETS ===')
    r = requests.get(f'{BASE}/user/test_001/targets')
    print(f'  Status: {r.status_code}')
    targets = r.json().get('targets', [])
    print(f'  Targets count: {len(targets)}')
    for t in targets:
        print(f'    -> {t["target_name"]} ({t["target_color"]})')
    assert r.status_code == 200

    print('\n=== 6. ALICE SCANS BOB (her target!) ===')
    r = requests.post(f'{BASE}/scan', json={'scanner_id': 'test_001', 'scanned_id': 'test_002'})
    print(f'  Status: {r.status_code}')
    scan = r.json()
    print(f'  Is target: {scan.get("is_target")}')
    print(f'  Points: {scan.get("points_earned")}')
    print(f'  Message: {scan.get("message")}')
    print(f'  Total score: {scan.get("total_score")}')
    assert r.status_code == 200
    assert scan['success'] is True
    assert scan['points_earned'] >= 10

    print('\n=== 7. ALICE COMPLETES CONVERSATION ===')
    r = requests.post(f'{BASE}/conversation/complete', json={'user_id': 'test_001'})
    print(f'  Status: {r.status_code}')
    convo = r.json()
    print(f'  Points earned: {convo.get("points_earned")}')
    print(f'  New score: {convo.get("new_score")}')
    assert r.status_code == 200
    assert convo['points_earned'] == 5

    print('\n=== 8. ALICE SCANS CHARLIE (not her target) ===')
    r = requests.post(f'{BASE}/scan', json={'scanner_id': 'test_001', 'scanned_id': 'test_003'})
    print(f'  Status: {r.status_code}')
    scan = r.json()
    print(f'  Is target: {scan.get("is_target")}')
    print(f'  Points: {scan.get("points_earned")}')
    print(f'  Total score: {scan.get("total_score")}')
    assert r.status_code == 200

    print('\n=== 9. BOB SCANS CHARLIE (his target) ===')
    r = requests.post(f'{BASE}/scan', json={'scanner_id': 'test_002', 'scanned_id': 'test_003'})
    print(f'  Status: {r.status_code}')
    scan = r.json()
    print(f'  Is target: {scan.get("is_target")}')
    print(f'  Points: {scan.get("points_earned")}')
    assert r.status_code == 200

    print('\n=== 10. DUPLICATE SCAN (should fail) ===')
    r = requests.post(f'{BASE}/scan', json={'scanner_id': 'test_001', 'scanned_id': 'test_002'})
    print(f'  Status: {r.status_code}')
    print(f'  Error: {r.json().get("error")}')
    assert r.status_code == 400

    print('\n=== 11. LEADERBOARD ===')
    r = requests.get(f'{BASE}/leaderboard')
    print(f'  Status: {r.status_code}')
    for entry in r.json():
        print(f'  {entry.get("name")}: {entry.get("score")} pts ({entry.get("scanned_count")} scans)')
    assert r.status_code == 200

    print('\n=== 12. STATS ===')
    r = requests.get(f'{BASE}/stats')
    print(f'  Status: {r.status_code}')
    stats = r.json()
    print(f'  Total participants: {stats["total_participants"]}')
    print(f'  Total scans: {stats["total_scans"]}')
    print(f'  Active users: {stats["active_users"]}')
    assert r.status_code == 200
    assert stats['total_scans'] >= 3

    print('\n=== 13. TEAMS ===')
    r = requests.get(f'{BASE}/teams')
    print(f'  Status: {r.status_code}')
    teams = r.json().get('teams', [])
    print(f'  Teams count: {len(teams)}')
    assert r.status_code == 200

    print('\n=== 14. GENERATE TARGETS ===')
    r = requests.post(f'{BASE}/admin/generate-targets', json={
        'participants': payload['participants'],
        'targets_per_person': 2
    })
    print(f'  Status: {r.status_code}')
    gen = r.json()
    print(f'  Generated: {gen.get("count")} assignments')
    assert r.status_code == 200
    assert gen['count'] == 6  # 3 participants x 2 targets each

    print('\n=== 15. RESET EVENT ===')
    r = requests.post(f'{BASE}/admin/reset-event')
    print(f'  Status: {r.status_code}')
    print(f'  Message: {r.json().get("message")}')
    assert r.status_code == 200

    print('\n=== 16. LEADERBOARD AFTER RESET ===')
    r = requests.get(f'{BASE}/leaderboard')
    print(f'  Status: {r.status_code}')
    print(f'  Entries: {len(r.json())}')
    assert r.status_code == 200

    print('\n' + '='*50)
    print('ALL 16 STEPS PASSED! Full game flow works.')
    print('='*50)

if __name__ == '__main__':
    test_full_game()
