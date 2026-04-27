"""
10 full-game scenarios exercising the complete event lifecycle.

Uses the 4-user demo fixture (user_001–004, round-robin targets):
  user_001 → target user_002 (Jane Smith)
  user_002 → target user_003 (Mike Johnson)
  user_003 → target user_004 (Sarah Wilson)
  user_004 → target user_001 (John Doe)

Each scenario is independent (fresh app state per test via fixtures).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

USERS = {
    'alice': ('user_001', 'john.doe@email.com', 'John Doe'),
    'bob': ('user_002', 'jane.smith@email.com', 'Jane Smith'),
    'carol': ('user_003', 'mike.johnson@email.com', 'Mike Johnson'),
    'dan': ('user_004', 'sarah.wilson@email.com', 'Sarah Wilson'),
}

# Target mapping: scanner -> target
TARGETS = {
    'user_001': 'user_002',
    'user_002': 'user_003',
    'user_003': 'user_004',
    'user_004': 'user_001',
}


class TestScenario1_SinglePlayerFullGame:
    """Player logs in, views targets, scans target, completes conversation,
    checks leaderboard and stats — the golden path."""

    def test_golden_path(self, client, flask_app):
        uid, email, name = USERS['alice']

        # 1. Login
        r = client.post('/api/auth/login', json={'email': email})
        assert r.status_code == 200
        data = r.get_json()
        assert data['success'] is True
        assert data['user']['full_name'] == name
        assert data['user']['current_score'] == 0

        # 2. View targets
        r = client.get(f'/api/user/{uid}/targets')
        assert r.status_code == 200
        targets = r.get_json()['targets']
        assert isinstance(targets, list)

        # 3. View single target
        r = client.get(f'/api/user/{uid}/target')
        assert r.status_code == 200
        assert 'target_name' in r.get_json()

        # 4. Scan assigned target
        target_id = TARGETS[uid]
        r = client.post('/api/scan', json={'scanner_id': uid, 'scanned_id': target_id})
        assert r.status_code == 200
        scan = r.get_json()
        assert scan['success'] is True
        assert scan['is_target'] is True
        assert scan['points_earned'] == 100
        assert scan['total_score'] == 100
        assert len(scan['bonuses']) > 0

        # 5. Complete conversation
        r = client.post('/api/conversation/complete', json={'user_id': uid})
        assert r.status_code == 200
        conv = r.get_json()
        assert conv['points_earned'] == 5
        assert conv['new_score'] == 105

        # 6. Leaderboard reflects score
        r = client.get('/api/leaderboard')
        lb = r.get_json()
        entry = next(e for e in lb if e['id'] == uid)
        assert entry['score'] == 105

        # 7. Stats updated
        r = client.get('/api/stats')
        stats = r.get_json()
        assert stats['total_scans'] == 1
        assert stats['active_users'] == 1
        assert stats['targets_found'] >= 1


class TestScenario2_AllPlayersCompleteTargets:
    """All 4 players find their assigned targets — full completion."""

    def test_all_complete(self, client, flask_app):
        for uid, target_id in TARGETS.items():
            r = client.post('/api/scan', json={'scanner_id': uid, 'scanned_id': target_id})
            assert r.status_code == 200
            assert r.get_json()['is_target'] is True

        # All should be on leaderboard with 100 points
        r = client.get('/api/leaderboard')
        lb = r.get_json()
        scores = {e['id']: e['score'] for e in lb}
        for uid in TARGETS:
            assert scores.get(uid, 0) == 100

        # Stats: 4 scans, 4 active, 4 targets found
        r = client.get('/api/stats')
        stats = r.get_json()
        assert stats['total_scans'] == 4
        assert stats['active_users'] == 4
        assert stats['targets_found'] == 4
        assert stats['completion_rate'] == 100.0


class TestScenario3_NonTargetScansOnly:
    """Players only scan non-target people — lower points, no target found."""

    def test_non_target_scoring(self, client, flask_app):
        # user_001 target is user_002. Scan user_003 and user_004 instead.
        r1 = client.post('/api/scan', json={'scanner_id': 'user_001', 'scanned_id': 'user_003'})
        assert r1.status_code == 200
        assert r1.get_json()['is_target'] is False
        assert r1.get_json()['points_earned'] == 10

        r2 = client.post('/api/scan', json={'scanner_id': 'user_001', 'scanned_id': 'user_004'})
        assert r2.status_code == 200
        assert r2.get_json()['points_earned'] == 10
        assert r2.get_json()['total_score'] == 20

        # Leaderboard: no target found
        r = client.get('/api/leaderboard')
        entry = next(e for e in r.get_json() if e['id'] == 'user_001')
        assert entry['score'] == 20
        assert entry.get('found_target', False) is False


class TestScenario4_DuplicateAndSelfScanPrevention:
    """Various invalid scan attempts are rejected."""

    def test_invalid_scans(self, client, flask_app):
        # Self scan → 400
        r = client.post('/api/scan', json={'scanner_id': 'user_001', 'scanned_id': 'user_001'})
        assert r.status_code == 400

        # Valid first scan
        r = client.post('/api/scan', json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})
        assert r.status_code == 200

        # Duplicate → 400
        r = client.post('/api/scan', json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})
        assert r.status_code == 400

        # Missing fields → 400
        r = client.post('/api/scan', json={'scanner_id': 'user_001'})
        assert r.status_code == 400
        r = client.post('/api/scan', json={})
        assert r.status_code == 400

        # Score should only reflect the one valid scan
        r = client.get('/api/leaderboard')
        entry = next(e for e in r.get_json() if e['id'] == 'user_001')
        assert entry['score'] == 100  # target scan


class TestScenario5_ReverseScansBothGetPoints:
    """A scans B, then B scans A — both earn points independently."""

    def test_bidirectional_scans(self, client, flask_app):
        # user_001 scans user_002 (target hit)
        r1 = client.post('/api/scan', json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})
        assert r1.status_code == 200
        assert r1.get_json()['points_earned'] == 100

        # user_002 scans user_001 (non-target — user_002's target is user_003)
        r2 = client.post('/api/scan', json={'scanner_id': 'user_002', 'scanned_id': 'user_001'})
        assert r2.status_code == 200
        assert r2.get_json()['points_earned'] == 10

        # Both on leaderboard
        r = client.get('/api/leaderboard')
        lb = {e['id']: e['score'] for e in r.get_json()}
        assert lb['user_001'] == 100
        assert lb['user_002'] == 10


class TestScenario6_ConversationBonusStacking:
    """Multiple conversation completions stack points correctly."""

    def test_conversation_stacking(self, client, flask_app):
        uid = 'user_001'

        # Scan target → 100 pts
        client.post('/api/scan', json={'scanner_id': uid, 'scanned_id': 'user_002'})

        # Complete 3 conversations → +15 pts
        for i in range(3):
            r = client.post('/api/conversation/complete', json={'user_id': uid})
            assert r.status_code == 200
            assert r.get_json()['points_earned'] == 5
            assert r.get_json()['new_score'] == 100 + (i + 1) * 5

        # Total: 115
        r = client.get('/api/leaderboard')
        entry = next(e for e in r.get_json() if e['id'] == uid)
        assert entry['score'] == 115


class TestScenario7_LeaderboardOrderingCompetition:
    """Multiple players compete — leaderboard sorts correctly."""

    def test_leaderboard_ordering(self, client, flask_app):
        # user_001 scans target (100) + non-target (10) = 110
        client.post('/api/scan', json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})
        client.post('/api/scan', json={'scanner_id': 'user_001', 'scanned_id': 'user_003'})

        # user_002 scans target only (100)
        client.post('/api/scan', json={'scanner_id': 'user_002', 'scanned_id': 'user_003'})

        # user_003 scans non-target only (10)
        client.post('/api/scan', json={'scanner_id': 'user_003', 'scanned_id': 'user_001'})

        r = client.get('/api/leaderboard')
        lb = r.get_json()
        scores = [e['score'] for e in lb if e['score'] > 0]

        # Must be sorted descending
        assert scores == sorted(scores, reverse=True)
        assert lb[0]['id'] == 'user_001'  # 110
        assert lb[0]['score'] == 110
        assert lb[1]['score'] == 100  # user_002
        assert lb[2]['score'] == 10   # user_003


class TestScenario8_TeamsAndMissionsDataIntegrity:
    """Teams endpoint returns valid data, missions match assignments."""

    def test_teams_and_missions(self, client, flask_app):
        # Teams
        r = client.get('/api/teams')
        assert r.status_code == 200
        teams = r.get_json()['teams']
        assert len(teams) >= 1
        for team in teams:
            assert 'color' in team
            assert 'name' in team

        # Missions
        r = client.get('/api/missions')
        assert r.status_code == 200
        missions = r.get_json()
        assert isinstance(missions, list)
        for m in missions:
            assert m['scanner_id'] != m['target_id'], "Self-assignment in missions"
            assert 'found' in m

        # Participant emails
        r = client.get('/api/participants/emails')
        assert r.status_code == 200
        emails = r.get_json()['emails']
        assert len(emails) == 4
        assert emails == sorted(emails)


class TestScenario9_EventResetClearsEverything:
    """Admin resets the event — all scores and scans are wiped."""

    def test_reset_wipes_state(self, client, flask_app):
        # Play some game
        client.post('/api/scan', json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})
        client.post('/api/scan', json={'scanner_id': 'user_002', 'scanned_id': 'user_003'})
        client.post('/api/conversation/complete', json={'user_id': 'user_001'})

        # Verify scores exist
        r = client.get('/api/stats')
        assert r.get_json()['total_scans'] == 2

        # Reset
        r = client.post('/api/admin/reset-event')
        assert r.status_code == 200
        assert r.get_json()['status'] == 'success'

        # Everything zeroed
        r = client.get('/api/stats')
        stats = r.get_json()
        assert stats['total_scans'] == 0
        assert stats['active_users'] == 0

        # Leaderboard empty or all zeros
        r = client.get('/api/leaderboard')
        lb = r.get_json()
        for entry in lb:
            assert entry['score'] == 0


class TestScenario10_FullEventLifecycle:
    """Complete event: login all → play → check → reset → verify clean."""

    def test_full_lifecycle(self, client, flask_app):
        # --- Phase 1: All players login ---
        for uid, email, name in USERS.values():
            r = client.post('/api/auth/login', json={'email': email})
            assert r.status_code == 200
            assert r.get_json()['user']['full_name'] == name

        # --- Phase 2: All scan their targets ---
        for uid, target_id in TARGETS.items():
            r = client.post('/api/scan', json={'scanner_id': uid, 'scanned_id': target_id})
            assert r.status_code == 200
            assert r.get_json()['is_target'] is True

        # --- Phase 3: Some also scan non-targets ---
        client.post('/api/scan', json={'scanner_id': 'user_001', 'scanned_id': 'user_003'})
        client.post('/api/scan', json={'scanner_id': 'user_001', 'scanned_id': 'user_004'})

        # --- Phase 4: Conversations ---
        for uid in TARGETS:
            client.post('/api/conversation/complete', json={'user_id': uid})

        # --- Phase 5: Verify final state ---
        r = client.get('/api/leaderboard')
        lb = r.get_json()
        u1 = next(e for e in lb if e['id'] == 'user_001')
        assert u1['score'] == 100 + 10 + 10 + 5  # target + 2 non-targets + convo
        assert u1['scanned_count'] == 3

        r = client.get('/api/stats')
        stats = r.get_json()
        assert stats['total_scans'] == 6  # 4 targets + 2 extra
        assert stats['active_users'] == 4
        assert stats['targets_found'] == 4

        # --- Phase 6: Admin reset ---
        r = client.post('/api/admin/reset-event')
        assert r.status_code == 200

        # --- Phase 7: Verify clean state ---
        r = client.get('/api/stats')
        stats = r.get_json()
        assert stats['total_scans'] == 0
        assert stats['active_users'] == 0
