"""
Tests for AdminPanel (backend/admin.py) with mocked Firebase.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def admin_panel():
    """Create an AdminPanel with mocked Firebase, bypassing __init__."""
    from admin import AdminPanel
    panel = AdminPanel.__new__(AdminPanel)
    panel.db = MagicMock()
    return panel


class TestAdminImportFromCsv:
    def test_import_valid_csv(self, admin_panel, tmp_path):
        data = [
            {'full_name': 'Alice', 'email': 'alice@test.com',
             'linkedin_url': 'https://linkedin.com/in/alice',
             'genre_color': 'blue', 'convo_tip': 'Travel'},
            {'full_name': 'Bob', 'email': 'bob@test.com',
             'linkedin_url': 'https://linkedin.com/in/bob',
             'genre_color': 'red', 'convo_tip': 'Books'},
        ]
        csv_file = str(tmp_path / 'test.csv')
        pd.DataFrame(data).to_csv(csv_file, index=False)

        result = admin_panel.import_from_csv(csv_file)
        assert result is True

    def test_import_missing_columns(self, admin_panel, tmp_path):
        data = [{'name': 'Bad', 'email': 'a@b.com'}]
        csv_file = str(tmp_path / 'bad.csv')
        pd.DataFrame(data).to_csv(csv_file, index=False)

        result = admin_panel.import_from_csv(csv_file)
        assert result is False

    def test_import_validation_error(self, admin_panel, tmp_path):
        data = [
            {'full_name': 'A', 'email': 'bad',
             'linkedin_url': 'http://notlinkedin.com',
             'genre_color': 'purple', 'convo_tip': 'tip'},
        ]
        csv_file = str(tmp_path / 'invalid.csv')
        pd.DataFrame(data).to_csv(csv_file, index=False)

        result = admin_panel.import_from_csv(csv_file)
        assert result is False

    def test_import_nonexistent_file(self, admin_panel):
        result = admin_panel.import_from_csv('/nonexistent/file.csv')
        assert result is False


class TestAdminAssignTargets:
    def test_no_self_assignments(self, admin_panel):
        from models import User
        users = [
            User(full_name=f'User {i}', email=f'user{i}@test.com',
                 linkedin_url=f'https://linkedin.com/in/user{i}',
                 genre_color=['red', 'blue', 'green', 'yellow'][i % 4])
            for i in range(10)
        ]
        result = admin_panel._assign_targets(users)

        for user in result:
            assert hasattr(user, 'target_email')
            assert user.target_email != user.email

    def test_all_users_get_targets(self, admin_panel):
        from models import User
        users = [
            User(full_name=f'User {i}', email=f'user{i}@test.com',
                 linkedin_url=f'https://linkedin.com/in/user{i}',
                 genre_color='blue')
            for i in range(5)
        ]
        result = admin_panel._assign_targets(users)

        for user in result:
            assert hasattr(user, 'target_email')
            assert user.target_email is not None

    def test_two_users_swap_targets(self, admin_panel):
        from models import User
        users = [
            User(full_name='A', email='a@test.com',
                 linkedin_url='https://linkedin.com/in/a', genre_color='blue'),
            User(full_name='B', email='b@test.com',
                 linkedin_url='https://linkedin.com/in/b', genre_color='red'),
        ]
        result = admin_panel._assign_targets(users)
        # Both users should have targets
        for user in result:
            assert user.target_email != user.email


class TestAdminUploadUsers:
    def test_upload_creates_batch(self, admin_panel):
        from models import User
        users = [
            User(full_name='Alice', email='alice@test.com',
                 linkedin_url='https://linkedin.com/in/alice', genre_color='blue'),
        ]
        users[0].target_email = 'alice@test.com'  # Doesn't matter for upload test

        # Mock document() to return unique IDs
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = 'doc_001'
        admin_panel.db.collection.return_value.document.return_value = mock_doc_ref

        admin_panel._upload_users(users)

        # Verify batch operations were called
        admin_panel.db.batch.assert_called()


class TestAdminGenerateQrCodes:
    def test_generate_qr_creates_files(self, admin_panel, tmp_path):
        # Mock Firestore stream
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            'full_name': 'Test User',
            'genre_color': 'blue'
        }
        mock_doc.id = 'user_001'

        admin_panel.db.collection.return_value.stream.return_value = [mock_doc]

        output = str(tmp_path / 'qr_test')
        admin_panel.generate_qr_codes(output)

        assert os.path.exists(output)
        # Should have generated at least one file
        files = os.listdir(output)
        assert len(files) >= 1
