"""
Shared pytest fixtures for backend tests.
"""
import sys
import os
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch


# Add backend to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def mock_db():
    """Create a mock Firestore database client."""
    db = MagicMock()
    return db


@pytest.fixture
def sample_participants_data():
    """Participant data keyed by email."""
    return {
        'john.doe@email.com': {
            'full_name': 'John Doe',
            'email': 'john.doe@email.com',
            'linkedin_url': 'https://linkedin.com/in/johndoe',
            'genre_color': 'blue',
            'convo_tip': 'Ask about their favorite travel destination'
        },
        'jane.smith@email.com': {
            'full_name': 'Jane Smith',
            'email': 'jane.smith@email.com',
            'linkedin_url': 'https://linkedin.com/in/janesmith',
            'genre_color': 'red',
            'convo_tip': 'Discuss favorite books or movies'
        },
        'mike.johnson@email.com': {
            'full_name': 'Mike Johnson',
            'email': 'mike.johnson@email.com',
            'linkedin_url': 'https://linkedin.com/in/mikejohnson',
            'genre_color': 'green',
            'convo_tip': 'Talk about hobby projects or side interests'
        },
        'sarah.wilson@email.com': {
            'full_name': 'Sarah Wilson',
            'email': 'sarah.wilson@email.com',
            'linkedin_url': 'https://linkedin.com/in/sarahwilson',
            'genre_color': 'yellow',
            'convo_tip': 'Ask about their career journey'
        },
    }


@pytest.fixture
def sample_qr_mapping():
    """QR mapping: user_id -> email."""
    return {
        'user_001': 'john.doe@email.com',
        'user_002': 'jane.smith@email.com',
        'user_003': 'mike.johnson@email.com',
        'user_004': 'sarah.wilson@email.com',
    }


@pytest.fixture
def sample_email_to_userid():
    """Reverse mapping: email -> user_id."""
    return {
        'john.doe@email.com': 'user_001',
        'jane.smith@email.com': 'user_002',
        'mike.johnson@email.com': 'user_003',
        'sarah.wilson@email.com': 'user_004',
    }


@pytest.fixture
def sample_target_assignments():
    """Target assignments: scanner_id -> target_id."""
    return {
        'user_001': 'user_002',
        'user_002': 'user_003',
        'user_003': 'user_004',
        'user_004': 'user_001',
    }


@pytest.fixture
def sample_user_stats():
    """In-memory user stats."""
    return {
        'user_001': {'total_score': 0, 'scanned_users': [], 'found_target': False, 'completed_targets': []},
        'user_002': {'total_score': 0, 'scanned_users': [], 'found_target': False, 'completed_targets': []},
        'user_003': {'total_score': 0, 'scanned_users': [], 'found_target': False, 'completed_targets': []},
        'user_004': {'total_score': 0, 'scanned_users': [], 'found_target': False, 'completed_targets': []},
    }


@pytest.fixture
def flask_app(sample_participants_data, sample_qr_mapping,
              sample_email_to_userid, sample_target_assignments,
              sample_user_stats):
    """Create a Flask test app in demo mode (db=None)."""
    # Patch Firebase before importing app
    with patch('firebase_admin.credentials.Certificate', side_effect=Exception("No creds")), \
         patch('firebase_admin.initialize_app'), \
         patch.dict('os.environ', {}, clear=False):

        # Need to reload the module to get a fresh app
        import importlib  # noqa: F401
        # Ensure scoring and models are importable
        if 'app' in sys.modules:
            del sys.modules['app']
        if 'scoring' in sys.modules:
            del sys.modules['scoring']

        import app as app_module

        # Override global state for demo mode
        app_module.db = None
        app_module.scorer = None
        app_module.participants_data = sample_participants_data
        app_module.qr_mapping = sample_qr_mapping
        app_module.email_to_userid = sample_email_to_userid
        app_module.target_assignments = sample_target_assignments
        app_module.user_stats = sample_user_stats

        # Build a target_assignments_df matching the simple dict
        # Each scanner has exactly 1 target in the test fixture
        rows = []
        for scanner_id, target_id in sample_target_assignments.items():
            scanner_email = sample_qr_mapping.get(scanner_id, '')
            target_email = sample_qr_mapping.get(target_id, '')
            scanner_name = sample_participants_data.get(scanner_email, {}).get('full_name', '')
            target_name = sample_participants_data.get(target_email, {}).get('full_name', '')
            target_color = sample_participants_data.get(target_email, {}).get('genre_color', 'blue')
            convo_tip = sample_participants_data.get(target_email, {}).get('convo_tip', '')
            rows.append({
                'scanner_id': scanner_id,
                'scanner_name': scanner_name,
                'target_id': target_id,
                'target_name': target_name,
                'target_color': target_color,
                'target_job_title': 'Unknown',
                'convo_tip': convo_tip,
            })
        app_module.target_assignments_df = pd.DataFrame(rows) if rows else None

        app_module.app.config['TESTING'] = True
        yield app_module


@pytest.fixture
def client(flask_app):
    """Flask test client."""
    with flask_app.app.test_client() as client:
        yield client
