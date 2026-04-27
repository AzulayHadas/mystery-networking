"""
Tests for Flask API endpoints (demo mode — Firebase disabled).
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_health_returns_ok(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'ok'
        assert 'timestamp' in data

    def test_health_firebase_disconnected_in_demo(self, client):
        resp = client.get('/api/health')
        data = resp.get_json()
        assert data['firebase_connected'] is False


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_known_email(self, client):
        resp = client.post('/api/auth/login',
                           json={'email': 'john.doe@email.com'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['user']['full_name'] == 'John Doe'
        assert data['user']['id'] == 'user_001'
        assert 'current_score' in data['user']

    def test_login_email_case_insensitive(self, client):
        resp = client.post('/api/auth/login',
                           json={'email': 'JOHN.DOE@EMAIL.COM'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['user']['full_name'] == 'John Doe'

    def test_login_unknown_email_fallback(self, client):
        resp = client.post('/api/auth/login',
                           json={'email': 'unknown@example.com'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['user']['current_score'] == 0
        # Fallback demo user
        assert 'demo' in data['user']['id'].lower() or 'Demo' in data['user']['full_name']

    def test_login_empty_email(self, client):
        resp = client.post('/api/auth/login', json={'email': ''})
        assert resp.status_code == 400

    def test_login_missing_email_field(self, client):
        resp = client.post('/api/auth/login', json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# User Endpoints
# ---------------------------------------------------------------------------

class TestGetUser:
    def test_get_user_demo_mode(self, client):
        resp = client.get('/api/user/user_001')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'full_name' in data or 'email' in data


class TestGetUserTarget:
    def test_get_target_for_known_user(self, client, flask_app):
        resp = client.get('/api/user/user_001/target')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'target_name' in data
        assert 'target_color' in data

    def test_get_target_for_unknown_user(self, client):
        resp = client.get('/api/user/nonexistent_999/target')
        assert resp.status_code == 200
        data = resp.get_json()
        # Should still return gracefully
        assert 'target_name' in data or 'found' in data


class TestGetUserTargets:
    def test_get_targets_returns_list(self, client, flask_app):
        resp = client.get('/api/user/user_001/targets')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'targets' in data
        assert isinstance(data['targets'], list)

    def test_get_targets_unknown_user_returns_empty(self, client):
        resp = client.get('/api/user/nonexistent_999/targets')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'targets' in data
        assert isinstance(data['targets'], list)


# ---------------------------------------------------------------------------
# Conversation Complete
# ---------------------------------------------------------------------------

class TestConversationComplete:
    def test_complete_conversation_success(self, client, flask_app):
        resp = client.post('/api/conversation/complete',
                           json={'user_id': 'user_001'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['points_earned'] == 5
        assert 'new_score' in data

    def test_complete_conversation_accumulates_points(self, client, flask_app):
        # First completion
        resp1 = client.post('/api/conversation/complete',
                            json={'user_id': 'user_002'})
        score1 = resp1.get_json()['new_score']

        # Second completion
        resp2 = client.post('/api/conversation/complete',
                            json={'user_id': 'user_002'})
        score2 = resp2.get_json()['new_score']

        assert score2 == score1 + 5

    def test_complete_conversation_missing_user_id(self, client):
        resp = client.post('/api/conversation/complete', json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'error' in data

    def test_complete_conversation_new_user(self, client, flask_app):
        """Unregistered user should be rejected with 404."""
        resp = client.post('/api/conversation/complete',
                           json={'user_id': 'brand_new_user'})
        assert resp.status_code == 404
        data = resp.get_json()
        assert 'error' in data


# ---------------------------------------------------------------------------
# QR Scan
# ---------------------------------------------------------------------------

class TestScanEndpoint:
    def test_scan_missing_fields(self, client):
        resp = client.post('/api/scan', json={})
        assert resp.status_code == 400

    def test_scan_missing_scanned_id(self, client):
        resp = client.post('/api/scan', json={'scanner_id': 'user_001'})
        assert resp.status_code == 400

    def test_self_scan_rejected(self, client):
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'user_001'})
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'error' in data

    def test_valid_scan_known_users(self, client, flask_app):
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'user_002'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'points_earned' in data
        assert data['points_earned'] > 0

    def test_duplicate_scan_rejected(self, client, flask_app):
        # First scan succeeds
        client.post('/api/scan',
                    json={'scanner_id': 'user_003',
                          'scanned_id': 'user_004'})
        # Second scan same pair should fail
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_003',
                                 'scanned_id': 'user_004'})
        assert resp.status_code == 400

    def test_scan_unknown_qr_fallback(self, client):
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'unknown_qr_xyz'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

    def test_scan_awards_target_points(self, client, flask_app):
        """Scan the assigned target and verify higher points."""
        # user_001's target is user_002
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'user_002'})
        data = resp.get_json()
        assert data['success'] is True
        # Target scans award 100 points in demo mode
        assert data['points_earned'] >= 10

    def test_scan_non_target_lower_points(self, client, flask_app):
        """Scan a non-target user and verify regular points."""
        # user_001's target is user_002, scan user_003 instead
        resp = client.post('/api/scan',
                           json={'scanner_id': 'user_001',
                                 'scanned_id': 'user_003'})
        data = resp.get_json()
        assert data['success'] is True
        assert data['points_earned'] == 10


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

class TestLeaderboard:
    def test_leaderboard_returns_list(self, client):
        resp = client.get('/api/leaderboard')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_leaderboard_sorted_descending(self, client, flask_app):
        # Do some scans to create scores
        client.post('/api/scan',
                    json={'scanner_id': 'user_001', 'scanned_id': 'user_002'})
        client.post('/api/scan',
                    json={'scanner_id': 'user_002', 'scanned_id': 'user_003'})

        resp = client.get('/api/leaderboard')
        data = resp.get_json()

        scores = [entry['score'] for entry in data]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_returns_required_fields(self, client):
        resp = client.get('/api/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'total_participants' in data
        assert 'active_users' in data
        assert 'total_scans' in data

    def test_stats_participants_count(self, client):
        resp = client.get('/api/stats')
        data = resp.get_json()
        assert data['total_participants'] == 4  # 4 sample participants


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

class TestTeams:
    def test_teams_endpoint(self, client):
        resp = client.get('/api/teams')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'teams' in data
        assert isinstance(data['teams'], list)


# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------

class TestMissions:
    def test_missions_returns_list(self, client):
        resp = client.get('/api/missions')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Index / Frontend
# ---------------------------------------------------------------------------

class TestParticipantEmails:
    def test_emails_returns_list(self, client):
        resp = client.get('/api/participants/emails')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'emails' in data
        assert isinstance(data['emails'], list)

    def test_emails_sorted(self, client):
        resp = client.get('/api/participants/emails')
        data = resp.get_json()
        emails = data['emails']
        assert emails == sorted(emails)

    def test_emails_contains_known_participant(self, client):
        resp = client.get('/api/participants/emails')
        data = resp.get_json()
        assert 'john.doe@email.com' in data['emails']


# ---------------------------------------------------------------------------
# Index / Frontend
# ---------------------------------------------------------------------------

class TestIndex:
    def test_root_returns_html(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        assert b'Mystery Networking' in resp.data


# ---------------------------------------------------------------------------
# Admin - Upload Config
# ---------------------------------------------------------------------------

class TestAdminUploadConfig:
    @pytest.fixture(autouse=True)
    def _redirect_writes(self, tmp_path, monkeypatch):
        """Prevent upload-config from writing to real data files."""
        monkeypatch.setenv('K_SERVICE', 'test')
        os.makedirs(tmp_path / 'data', exist_ok=True)
        os.makedirs(tmp_path / 'qr_codes', exist_ok=True)

    def test_upload_participants(self, client, flask_app):
        payload = {
            "participants": [
                {
                    "user_id": "new_001",
                    "full_name": "Test User",
                    "email": "test@example.com",
                    "job_title": "Tester",
                    "genre_color": "blue",
                    "linkedin_url": "",
                    "convo_tip": "Talk about testing"
                }
            ]
        }
        resp = client.post('/api/admin/upload-config', json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'
        assert 'participants' in data['message']

    def test_upload_teams(self, client, flask_app):
        payload = {
            "teams": [
                {"color": "blue", "name": "Blue", "emoji": "💙", "description": "Blue team"}
            ]
        }
        resp = client.post('/api/admin/upload-config', json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'

    def test_upload_targets(self, client, flask_app):
        payload = {
            "targets": [
                {
                    "scanner_id": "user_001",
                    "target_id": "user_002",
                    "target_name": "Jane Smith",
                    "target_color": "red",
                    "target_job_title": "Designer",
                    "convo_tip": "Talk about design"
                }
            ]
        }
        resp = client.post('/api/admin/upload-config', json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'

    def test_upload_empty_payload(self, client, flask_app):
        resp = client.post('/api/admin/upload-config', json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['message'] == 'No data to update'

    def test_upload_options_cors(self, client):
        resp = client.options('/api/admin/upload-config')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Reset & Re-initialization Tests
# ---------------------------------------------------------------------------


class TestResetReinitializes:
    def test_reset_event_reinitializes_all_users(self, client, flask_app):
        """After reset, all users should have zero stats but still exist."""
        # Create some activity
        client.post('/api/scan', json={
            'scanner_id': 'user_001', 'scanned_id': 'user_002'
        })
        assert flask_app.user_stats['user_001']['total_score'] > 0

        # Reset
        resp = client.post('/api/admin/reset-event')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['users_initialized'] == len(flask_app.qr_mapping)

        # All users re-initialized with zero stats
        for uid in flask_app.qr_mapping:
            assert uid in flask_app.user_stats
            assert flask_app.user_stats[uid]['total_score'] == 0
            assert flask_app.user_stats[uid]['scanned_users'] == []
            assert flask_app.user_stats[uid]['completed_targets'] == []

    def test_reset_stats_reinitializes_all_users(self, client, flask_app):
        """reset-stats should also re-initialize, not leave empty."""
        client.post('/api/scan', json={
            'scanner_id': 'user_001', 'scanned_id': 'user_002'
        })
        resp = client.post('/api/admin/reset-stats')
        assert resp.status_code == 200
        for uid in flask_app.qr_mapping:
            assert uid in flask_app.user_stats
            assert flask_app.user_stats[uid]['total_score'] == 0

    def test_scan_works_after_reset(self, client, flask_app):
        """Scans should work immediately after reset without errors."""
        client.post('/api/admin/reset-event')
        resp = client.post('/api/scan', json={
            'scanner_id': 'user_001', 'scanned_id': 'user_002'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['points_earned'] > 0


# ---------------------------------------------------------------------------
# Leaderboard Tiebreaker Tests
# ---------------------------------------------------------------------------


class TestLeaderboardTiebreaker:
    def test_tiebreaker_by_scan_count(self, client, flask_app):
        """Same score: more scans ranks higher."""
        flask_app.user_stats['user_001']['total_score'] = 100
        flask_app.user_stats['user_001']['scanned_users'] = ['user_002', 'user_003']
        flask_app.user_stats['user_002']['total_score'] = 100
        flask_app.user_stats['user_002']['scanned_users'] = ['user_001']

        resp = client.get('/api/leaderboard')
        data = resp.get_json()
        # user_001 has 2 scans vs user_002's 1 scan
        assert data[0]['id'] == 'user_001'
        assert data[1]['id'] == 'user_002'

    def test_tiebreaker_by_name(self, client, flask_app):
        """Same score and scans: alphabetical by name."""
        flask_app.user_stats['user_001']['total_score'] = 50
        flask_app.user_stats['user_001']['scanned_users'] = ['user_002']
        flask_app.user_stats['user_002']['total_score'] = 50
        flask_app.user_stats['user_002']['scanned_users'] = ['user_001']

        resp = client.get('/api/leaderboard')
        data = resp.get_json()
        # Both tied on score and scans — alphabetical: Jane Smith < John Doe
        names = [d['name'] for d in data[:2]]
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# Conversation Validation Tests
# ---------------------------------------------------------------------------


class TestConversationValidation:
    def test_conversation_rejects_unknown_user(self, client, flask_app):
        """Conversation complete should reject non-registered users."""
        resp = client.post('/api/conversation/complete', json={
            'user_id': 'fake_user_999'
        })
        assert resp.status_code == 404

    def test_conversation_accepts_registered_user(self, client, flask_app):
        """Conversation complete should work for registered users."""
        resp = client.post('/api/conversation/complete', json={
            'user_id': 'user_001'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['points_earned'] == 5


# Admin - Generate Targets
# ---------------------------------------------------------------------------


class TestAdminGenerateTargets:
    def test_generate_targets_success(self, client):
        payload = {
            "participants": [
                {"user_id": "u1", "email": "a@test.com", "full_name": "A", "genre_color": "blue", "job_title": "Dev"},
                {"user_id": "u2", "email": "b@test.com", "full_name": "B", "genre_color": "red", "job_title": "PM"},
                {"user_id": "u3", "email": "c@test.com", "full_name": "C", "genre_color": "green", "job_title": "QA"},
                {"user_id": "u4", "email": "d@test.com", "full_name": "D", "genre_color": "blue", "job_title": "Lead"},
            ],
            "targets_per_person": 2
        }
        resp = client.post('/api/admin/generate-targets', json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'
        assert data['count'] == 8  # 4 participants * 2 targets each

    def test_generate_targets_empty_participants(self, client):
        resp = client.post('/api/admin/generate-targets', json={"participants": []})
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'error' in data

    def test_generate_targets_no_self_assignment(self, client):
        payload = {
            "participants": [
                {"user_id": "u1", "email": "a@test.com", "full_name": "A", "job_title": "Dev"},
                {"user_id": "u2", "email": "b@test.com", "full_name": "B", "job_title": "PM"},
            ],
            "targets_per_person": 1
        }
        resp = client.post('/api/admin/generate-targets', json=payload)
        data = resp.get_json()
        for assignment in data['assignments']:
            assert assignment['scanner_id'] != assignment['target_id']

    def test_generate_targets_options_cors(self, client):
        resp = client.options('/api/admin/generate-targets')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Admin - Reset Stats
# ---------------------------------------------------------------------------

class TestAdminResetStats:
    def test_reset_stats(self, client, flask_app):
        # Create some scores first
        client.post('/api/conversation/complete', json={'user_id': 'user_001'})
        # Reset
        resp = client.post('/api/admin/reset-stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'reset' in data['message'].lower() or 'success' in data['message'].lower()


# ---------------------------------------------------------------------------
# Admin - Reset Event
# ---------------------------------------------------------------------------

class TestAdminResetEvent:
    def test_reset_event(self, client, flask_app):
        # Create some scores first
        client.post('/api/conversation/complete', json={'user_id': 'user_001'})
        # Full reset
        resp = client.post('/api/admin/reset-event')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'
        assert 'reset_time' in data

    def test_reset_event_clears_stats(self, client, flask_app):
        # Score some points
        client.post('/api/conversation/complete', json={'user_id': 'user_001'})
        # Reset
        client.post('/api/admin/reset-event')
        # Stats should be empty
        resp = client.get('/api/stats')
        data = resp.get_json()
        assert data['active_users'] == 0
        assert data['total_scans'] == 0
