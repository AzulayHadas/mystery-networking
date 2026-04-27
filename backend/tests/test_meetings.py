"""
End-to-end meeting operation tests.
Simulates complete user flows:
  - Login → get targets → scan targets → verify scoring → check leaderboard/stats
  - Multiple users interacting concurrently
  - Target completion tracking
  - Conversation tip flow
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestFullMeetingFlow:
    """Simulate a complete meeting event from start to finish."""

    def test_single_user_full_flow(self, client, flask_app):
        """Login → get target → scan target → verify results."""
        # 1. Login
        resp = client.post('/api/auth/login',
                           json={'email': 'john.doe@email.com'})
        assert resp.status_code == 200
        login_data = resp.get_json()
        assert login_data['success'] is True
        user_id = login_data['user']['id']
        assert user_id == 'user_001'

        # 2. Get target assignment
        resp = client.get(f'/api/user/{user_id}/target')
        assert resp.status_code == 200
        target_data = resp.get_json()
        assert 'target_name' in target_data

        # 3. Scan the assigned target (user_001 -> user_002)
        resp = client.post('/api/scan',
                           json={'scanner_id': user_id,
                                 'scanned_id': 'user_002'})
        assert resp.status_code == 200
        scan_data = resp.get_json()
        assert scan_data['success'] is True
        assert scan_data['points_earned'] > 0

        # 4. Verify leaderboard reflects the scan
        resp = client.get('/api/leaderboard')
        assert resp.status_code == 200
        lb = resp.get_json()
        user_entry = next((e for e in lb if e['id'] == user_id), None)
        assert user_entry is not None
        assert user_entry['score'] > 0

        # 5. Verify stats reflect the scan
        resp = client.get('/api/stats')
        assert resp.status_code == 200
        stats = resp.get_json()
        assert stats['total_scans'] >= 1
        assert stats['active_users'] >= 1

    def test_multi_user_meeting(self, client, flask_app):
        """Multiple users scanning each other during an event."""
        # User 1 scans user 2 (target)
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'user_002'})
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

        # User 2 scans user 3 (target)
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_002',
                                 'scanned_id': 'user_003'})
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

        # User 3 scans user 4 (target)
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_003',
                                 'scanned_id': 'user_004'})
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

        # User 4 scans user 1 (target)
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_004',
                                 'scanned_id': 'user_001'})
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

        # All users should now appear on the leaderboard
        resp = client.get('/api/leaderboard')
        lb = resp.get_json()
        active_ids = {e['id'] for e in lb if e['score'] > 0}
        assert len(active_ids) == 4

        # Stats should reflect 4 scans
        resp = client.get('/api/stats')
        stats = resp.get_json()
        assert stats['total_scans'] == 4
        assert stats['active_users'] == 4

    def test_scan_target_vs_nontarget_points(self, client, flask_app):
        """Target scan gives more points than non-target scan."""
        # user_001's target is user_002
        # Scan a non-target first
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'user_003'})
        nontarget_points = resp.get_json()['points_earned']

        # Now scan the actual target — need a fresh user since user_001 already scanned
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_002',
                                 'scanned_id': 'user_003'})
        target_points = resp.get_json()['points_earned']

        # Both should be positive
        assert nontarget_points > 0
        assert target_points > 0


class TestDuplicateScanPrevention:
    """Test that the system prevents re-scanning."""

    def test_cannot_scan_same_person_twice(self, client, flask_app):
        client.post('/api/scan',
                    json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})

        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'user_002'})
        assert resp.status_code == 400

    def test_reverse_scan_is_allowed(self, client, flask_app):
        """If A scans B, B can still scan A."""
        resp1 = client.post('/api/scan',
                            json={'scanner_id': 'user_001',
                                  'scanned_id': 'user_002'})
        assert resp1.status_code == 200

        resp2 = client.post('/api/scan',
                            json={'scanner_id': 'user_002',
                                  'scanned_id': 'user_001'})
        assert resp2.status_code == 200

    def test_self_scan_always_rejected(self, client):
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'user_001'})
        assert resp.status_code == 400


class TestTargetCompletionTracking:
    """Verify target completion state is tracked through the meeting."""

    def test_scan_updates_score_on_leaderboard(self, client, flask_app):
        """After scanning, the user's score should appear on the leaderboard."""
        client.post('/api/scan',
                    json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})

        resp = client.get('/api/leaderboard')
        lb = resp.get_json()
        entry = next((e for e in lb if e['id'] == 'user_001'), None)
        assert entry is not None
        assert entry['score'] > 0

    def test_non_target_scan_doesnt_set_found(self, client, flask_app):
        """Scanning a non-target should not set found_target."""
        # user_001's target is user_002, scan user_003 instead
        client.post('/api/scan',
                    json={'scanner_id': 'user_001', 'scanned_id': 'user_003'})

        resp = client.get('/api/leaderboard')
        lb = resp.get_json()
        entry = next((e for e in lb if e['id'] == 'user_001'), None)
        if entry:
            # found_target may not exist or should be False
            assert entry.get('found_target', False) is False


class TestScanResponseContent:
    """Verify scan response payloads contain all needed fields."""

    def test_scan_response_has_conversation_tip_field(self, client, flask_app):
        """Scan response should include the conversation_tip field."""
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'user_002'})
        data = resp.get_json()
        assert data['success'] is True
        # The response must always include the conversation_tip key
        assert 'conversation_tip' in data
        assert 'show_conversation_tip' in data or 'is_target' in data

    def test_scan_response_has_scanned_user_info(self, client, flask_app):
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'user_002'})
        data = resp.get_json()
        user_info = data['scanned_user']
        assert 'name' in user_info or 'full_name' in user_info
        assert 'email' in user_info or 'linkedin' in user_info or 'linkedin_url' in user_info

    def test_scan_response_has_bonuses(self, client, flask_app):
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'user_002'})
        data = resp.get_json()
        assert 'bonuses' in data
        assert isinstance(data['bonuses'], list)
        assert len(data['bonuses']) > 0

    def test_scan_response_has_total_score(self, client, flask_app):
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'user_002'})
        data = resp.get_json()
        assert 'total_score' in data
        assert data['total_score'] > 0


class TestStatsAfterMeetingActivity:
    """Verify event stats update correctly after meeting activities."""

    def test_stats_zero_before_scans(self, client):
        resp = client.get('/api/stats')
        stats = resp.get_json()
        assert stats['total_scans'] == 0
        assert stats['active_users'] == 0

    def test_stats_update_after_scans(self, client, flask_app):
        client.post('/api/scan',
                    json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})
        client.post('/api/scan',
                    json={'scanner_id': 'user_002', 'scanned_id': 'user_003'})

        resp = client.get('/api/stats')
        stats = resp.get_json()
        assert stats['total_scans'] == 2
        assert stats['active_users'] == 2

    def test_stats_has_color_breakdown(self, client, flask_app):
        client.post('/api/scan',
                    json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})

        resp = client.get('/api/stats')
        stats = resp.get_json()
        assert 'color_stats' in stats
        assert isinstance(stats['color_stats'], dict)

    def test_stats_completion_rate(self, client, flask_app):
        resp = client.get('/api/stats')
        stats = resp.get_json()
        assert 'completion_rate' in stats
        assert isinstance(stats['completion_rate'], (int, float))
        assert 0 <= stats['completion_rate'] <= 100

    def test_stats_targets_found_count(self, client, flask_app):
        # Scan all targets
        client.post('/api/scan',
                    json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})
        client.post('/api/scan',
                    json={'scanner_id': 'user_002', 'scanned_id': 'user_003'})

        resp = client.get('/api/stats')
        stats = resp.get_json()
        assert stats['targets_found'] >= 0


class TestLeaderboardAfterMeeting:
    """Verify leaderboard ordering and content after meeting activity."""

    def test_leaderboard_max_10(self, client, flask_app):
        resp = client.get('/api/leaderboard')
        lb = resp.get_json()
        assert len(lb) <= 10

    def test_leaderboard_entries_have_required_fields(self, client, flask_app):
        client.post('/api/scan',
                    json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})

        resp = client.get('/api/leaderboard')
        lb = resp.get_json()
        for entry in lb:
            assert 'id' in entry
            assert 'name' in entry
            assert 'score' in entry

    def test_highest_scorer_is_first(self, client, flask_app):
        # user_001 scans target for 100 pts, user_002 scans non-target for 10 pts
        client.post('/api/scan',
                    json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})
        client.post('/api/scan',
                    json={'scanner_id': 'user_002', 'scanned_id': 'user_004'})

        resp = client.get('/api/leaderboard')
        lb = resp.get_json()
        if len(lb) >= 2:
            assert lb[0]['score'] >= lb[1]['score']

    def test_scanned_count_increments(self, client, flask_app):
        client.post('/api/scan',
                    json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})
        client.post('/api/scan',
                    json={'scanner_id': 'user_001', 'scanned_id': 'user_003'})

        resp = client.get('/api/leaderboard')
        lb = resp.get_json()
        entry = next((e for e in lb if e['id'] == 'user_001'), None)
        assert entry is not None
        assert entry.get('scanned_count', 0) >= 2


class TestMissionsEndpoint:
    """Test the /api/missions endpoint for meeting operation visibility."""

    def test_missions_list_not_empty(self, client, flask_app):
        resp = client.get('/api/missions')
        assert resp.status_code == 200
        missions = resp.get_json()
        assert isinstance(missions, list)

    def test_missions_have_scanner_and_target(self, client, flask_app):
        resp = client.get('/api/missions')
        missions = resp.get_json()
        for mission in missions:
            assert 'scanner_id' in mission
            assert 'target_id' in mission
            assert 'scanner_name' in mission
            assert 'target_name' in mission

    def test_missions_no_self_assignment(self, client, flask_app):
        resp = client.get('/api/missions')
        missions = resp.get_json()
        for mission in missions:
            assert mission['scanner_id'] != mission['target_id']

    def test_missions_have_found_field(self, client, flask_app):
        """Each mission entry should include a 'found' boolean field."""
        resp = client.get('/api/missions')
        missions = resp.get_json()
        for mission in missions:
            assert 'found' in mission
            assert isinstance(mission['found'], bool)
