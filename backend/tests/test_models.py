"""
Tests for data models (User, Scan).
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import User, Scan


class TestUserModel:
    """Tests for the User dataclass."""

    def test_create_user_with_required_fields(self):
        user = User(
            full_name="John Doe",
            email="john@example.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            genre_color="blue"
        )
        assert user.full_name == "John Doe"
        assert user.email == "john@example.com"
        assert user.genre_color == "blue"
        assert user.current_score == 0
        assert user.scanned_users == []
        assert user.found_target is False

    def test_user_default_color_scanned(self):
        user = User(
            full_name="Jane",
            email="jane@example.com",
            linkedin_url="https://linkedin.com/in/jane",
            genre_color="red"
        )
        assert user.color_scanned == {
            'red': False,
            'blue': False,
            'green': False,
            'yellow': False
        }

    def test_user_to_dict(self):
        user = User(
            full_name="John Doe",
            email="JOHN@Example.COM",
            linkedin_url="https://linkedin.com/in/johndoe",
            genre_color="blue",
            convo_tip="Talk about travel"
        )
        d = user.to_dict()
        assert d['full_name'] == "John Doe"
        # to_dict normalizes email
        assert d['email'] == "john@example.com"
        assert d['linkedin_url'] == "https://linkedin.com/in/johndoe"
        assert d['genre_color'] == "blue"
        assert d['convo_tip'] == "Talk about travel"
        assert d['current_score'] == 0
        assert d['scanned_users'] == []
        assert d['found_target'] is False
        assert 'created_at' in d

    def test_user_validate_valid(self):
        user = User(
            full_name="John Doe",
            email="john@example.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            genre_color="blue"
        )
        errors = user.validate()
        assert errors == []

    def test_user_validate_short_name(self):
        user = User(
            full_name="J",
            email="john@example.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            genre_color="blue"
        )
        errors = user.validate()
        assert any("Full name" in e for e in errors)

    def test_user_validate_empty_name(self):
        user = User(
            full_name="",
            email="john@example.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            genre_color="blue"
        )
        errors = user.validate()
        assert any("Full name" in e for e in errors)

    def test_user_validate_invalid_email(self):
        user = User(
            full_name="John Doe",
            email="invalid-email",
            linkedin_url="https://linkedin.com/in/johndoe",
            genre_color="blue"
        )
        errors = user.validate()
        assert any("email" in e.lower() for e in errors)

    def test_user_validate_empty_email(self):
        user = User(
            full_name="John Doe",
            email="",
            linkedin_url="https://linkedin.com/in/johndoe",
            genre_color="blue"
        )
        errors = user.validate()
        assert any("email" in e.lower() for e in errors)

    def test_user_validate_invalid_linkedin(self):
        user = User(
            full_name="John Doe",
            email="john@example.com",
            linkedin_url="https://example.com/johndoe",
            genre_color="blue"
        )
        errors = user.validate()
        assert any("LinkedIn" in e for e in errors)

    def test_user_validate_invalid_color(self):
        user = User(
            full_name="John Doe",
            email="john@example.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            genre_color="purple"
        )
        errors = user.validate()
        assert any("color" in e.lower() for e in errors)

    def test_user_validate_multiple_errors(self):
        user = User(
            full_name="",
            email="bad",
            linkedin_url="http://bad.com",
            genre_color="invalid"
        )
        errors = user.validate()
        assert len(errors) >= 3

    def test_user_scanned_users_independence(self):
        """Ensure default mutable fields are independent across instances."""
        user1 = User(full_name="A", email="a@b.com",
                     linkedin_url="https://linkedin.com/in/a", genre_color="blue")
        user2 = User(full_name="B", email="b@b.com",
                     linkedin_url="https://linkedin.com/in/b", genre_color="red")
        user1.scanned_users.append("x")
        assert "x" not in user2.scanned_users


class TestScanModel:
    """Tests for the Scan dataclass."""

    def test_create_scan_defaults(self):
        scan = Scan(scanner_id="user_1", scanned_id="user_2")
        assert scan.scanner_id == "user_1"
        assert scan.scanned_id == "user_2"
        assert scan.points_awarded == 0
        assert scan.scan_type == "regular"
        assert isinstance(scan.timestamp, datetime)

    def test_scan_to_dict(self):
        scan = Scan(
            scanner_id="user_1",
            scanned_id="user_2",
            points_awarded=10,
            scan_type="target"
        )
        d = scan.to_dict()
        assert d['scanner_id'] == "user_1"
        assert d['scanned_id'] == "user_2"
        assert d['points_awarded'] == 10
        assert d['scan_type'] == "target"
        assert 'timestamp' in d

    def test_scan_validate_valid(self):
        scan = Scan(scanner_id="user_1", scanned_id="user_2")
        errors = scan.validate()
        assert errors == []

    def test_scan_validate_missing_scanner(self):
        scan = Scan(scanner_id="", scanned_id="user_2")
        errors = scan.validate()
        assert any("Scanner" in e for e in errors)

    def test_scan_validate_missing_scanned(self):
        scan = Scan(scanner_id="user_1", scanned_id="")
        errors = scan.validate()
        assert any("Scanned" in e for e in errors)

    def test_scan_validate_self_scan(self):
        scan = Scan(scanner_id="user_1", scanned_id="user_1")
        errors = scan.validate()
        assert any("yourself" in e.lower() for e in errors)

    def test_scan_validate_invalid_type(self):
        scan = Scan(scanner_id="user_1", scanned_id="user_2",
                    scan_type="invalid_type")
        errors = scan.validate()
        assert any("scan type" in e.lower() for e in errors)

    def test_scan_validate_valid_types(self):
        for scan_type in ['regular', 'target', 'color_bonus']:
            scan = Scan(scanner_id="a", scanned_id="b", scan_type=scan_type)
            errors = scan.validate()
            assert errors == [], f"Unexpected error for scan_type={scan_type}"
