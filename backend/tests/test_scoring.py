"""
Tests for the ScoringEngine.
"""
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scoring import ScoringEngine


class TestScoringConstants:
    """Verify point values are configured correctly."""

    def test_regular_scan_points(self):
        assert ScoringEngine.POINTS_REGULAR_SCAN == 10

    def test_target_found_points(self):
        assert ScoringEngine.POINTS_TARGET_FOUND == 100

    def test_color_series_points(self):
        assert ScoringEngine.POINTS_COLOR_SERIES == 50

    def test_conversation_points(self):
        assert ScoringEngine.POINTS_CONVERSATION == 5


class TestColorSeriesBonus:
    """Tests for _check_color_series_bonus."""

    def setup_method(self):
        self.db = MagicMock()
        self.engine = ScoringEngine(self.db)

    def test_no_bonus_when_color_already_scanned(self):
        scanner_data = {
            'color_scanned': {'red': True, 'blue': False, 'green': False, 'yellow': False}
        }
        bonus = self.engine._check_color_series_bonus(scanner_data, 'red')
        assert bonus == 0

    def test_no_bonus_when_incomplete_series(self):
        scanner_data = {
            'color_scanned': {'red': True, 'blue': True, 'green': False, 'yellow': False}
        }
        bonus = self.engine._check_color_series_bonus(scanner_data, 'green')
        assert bonus == 0

    def test_bonus_when_series_completed(self):
        scanner_data = {
            'color_scanned': {'red': True, 'blue': True, 'green': True, 'yellow': False}
        }
        bonus = self.engine._check_color_series_bonus(scanner_data, 'yellow')
        assert bonus == ScoringEngine.POINTS_COLOR_SERIES

    def test_default_color_scanned_when_missing(self):
        scanner_data = {}
        bonus = self.engine._check_color_series_bonus(scanner_data, 'red')
        assert bonus == 0

    def test_first_color_scan_no_bonus(self):
        scanner_data = {
            'color_scanned': {'red': False, 'blue': False, 'green': False, 'yellow': False}
        }
        bonus = self.engine._check_color_series_bonus(scanner_data, 'blue')
        assert bonus == 0


class TestProcessScan:
    """Tests for process_scan method."""

    def setup_method(self):
        self.db = MagicMock()
        self.engine = ScoringEngine(self.db)

    def _make_scanner_data(self, target_id='user_002', score=0):
        return {
            'target_id': target_id,
            'current_score': score,
            'scanned_users': [],
            'color_scanned': {'red': False, 'blue': False, 'green': False, 'yellow': False},
            'convo_tip': 'Talk about travel'
        }

    def _make_scanned_data(self, name='Jane Smith', color='red'):
        return {
            'full_name': name,
            'genre_color': color,
            'linkedin_url': 'https://linkedin.com/in/jane'
        }

    def test_regular_scan_points(self):
        scanner_data = self._make_scanner_data(target_id='user_999')
        scanned_data = self._make_scanned_data()

        result = self.engine.process_scan('user_001', 'user_002', scanner_data, scanned_data)

        assert result['success'] is True
        assert result['is_target'] is False
        assert result['points_earned'] == ScoringEngine.POINTS_REGULAR_SCAN

    def test_target_found_points(self):
        scanner_data = self._make_scanner_data(target_id='user_002')
        scanned_data = self._make_scanned_data()

        result = self.engine.process_scan('user_001', 'user_002', scanner_data, scanned_data)

        assert result['success'] is True
        assert result['is_target'] is True
        assert result['points_earned'] >= ScoringEngine.POINTS_TARGET_FOUND

    def test_target_found_includes_convo_tip(self):
        scanner_data = self._make_scanner_data(target_id='user_002')
        scanned_data = self._make_scanned_data()

        result = self.engine.process_scan('user_001', 'user_002', scanner_data, scanned_data)
        assert result['conversation_tip'] is not None

    def test_regular_scan_no_convo_tip(self):
        scanner_data = self._make_scanner_data(target_id='user_999')
        scanned_data = self._make_scanned_data()

        result = self.engine.process_scan('user_001', 'user_002', scanner_data, scanned_data)
        assert result['conversation_tip'] is None

    def test_total_score_accumulated(self):
        scanner_data = self._make_scanner_data(target_id='user_999', score=50)
        scanned_data = self._make_scanned_data()

        result = self.engine.process_scan('user_001', 'user_002', scanner_data, scanned_data)
        assert result['total_score'] == 50 + ScoringEngine.POINTS_REGULAR_SCAN

    def test_color_series_bonus_in_scan(self):
        scanner_data = self._make_scanner_data(target_id='user_999')
        scanner_data['color_scanned'] = {'red': True, 'blue': True, 'green': True, 'yellow': False}
        scanned_data = self._make_scanned_data(color='yellow')

        result = self.engine.process_scan('user_001', 'user_002', scanner_data, scanned_data)

        expected = ScoringEngine.POINTS_REGULAR_SCAN + ScoringEngine.POINTS_COLOR_SERIES
        assert result['points_earned'] == expected

    def test_target_plus_color_bonus(self):
        scanner_data = self._make_scanner_data(target_id='user_002')
        scanner_data['color_scanned'] = {'red': True, 'blue': True, 'green': True, 'yellow': False}
        scanned_data = self._make_scanned_data(color='yellow')

        result = self.engine.process_scan('user_001', 'user_002', scanner_data, scanned_data)

        expected = ScoringEngine.POINTS_TARGET_FOUND + ScoringEngine.POINTS_COLOR_SERIES
        assert result['points_earned'] == expected

    def test_result_contains_scanned_user_info(self):
        scanner_data = self._make_scanner_data(target_id='user_999')
        scanned_data = self._make_scanned_data(name='Jane Smith', color='red')

        result = self.engine.process_scan('user_001', 'user_002', scanner_data, scanned_data)

        assert result['scanned_user']['name'] == 'Jane Smith'
        assert result['scanned_user']['color'] == 'red'

    def test_result_contains_bonuses_list(self):
        scanner_data = self._make_scanner_data(target_id='user_999')
        scanned_data = self._make_scanned_data()

        result = self.engine.process_scan('user_001', 'user_002', scanner_data, scanned_data)
        assert isinstance(result['bonuses'], list)
        assert len(result['bonuses']) > 0


class TestUpdateScanner:
    """Tests for _update_scanner Firestore writes."""

    def setup_method(self):
        self.db = MagicMock()
        self.engine = ScoringEngine(self.db)

    def test_update_scanner_calls_firestore(self):
        scanner_data = {
            'scanned_users': [],
            'color_scanned': {'red': False, 'blue': False, 'green': False, 'yellow': False},
            'current_score': 0
        }
        self.engine._update_scanner(
            'user_001', 'user_002', 10, False, 'red', scanner_data
        )
        self.db.collection.assert_called_with('users')
        self.db.collection().document.assert_called_with('user_001')
        self.db.collection().document().update.assert_called_once()

    def test_update_scanner_sets_found_target_on_target(self):
        scanner_data = {
            'scanned_users': [],
            'color_scanned': {'red': False, 'blue': False, 'green': False, 'yellow': False},
            'current_score': 0
        }
        self.engine._update_scanner(
            'user_001', 'user_002', 100, True, 'red', scanner_data
        )
        update_call = self.db.collection().document().update.call_args[0][0]
        assert update_call['found_target'] is True


class TestRecordScan:
    """Tests for _record_scan Firestore writes."""

    def setup_method(self):
        self.db = MagicMock()
        self.engine = ScoringEngine(self.db)

    def test_record_scan_adds_to_collection(self):
        self.engine._record_scan('user_001', 'user_002', False, 10)
        self.db.collection.assert_called_with('scans')
        self.db.collection().add.assert_called_once()

    def test_record_scan_data_content(self):
        self.engine._record_scan('user_001', 'user_002', True, 100)
        call_data = self.db.collection().add.call_args[0][0]
        assert call_data['scanner_id'] == 'user_001'
        assert call_data['scanned_id'] == 'user_002'
        assert call_data['was_target'] is True
        assert call_data['points_earned'] == 100
        assert 'timestamp' in call_data
