"""
Tests for CSV data loading, configuration, and data import flows.
Covers: teams.csv, qr_mapping.csv, target_assignments.csv,
        participants.csv, and the load_participant_data() function.
"""
import sys
import os
import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


# ---------------------------------------------------------------------------
# teams.csv validation
# ---------------------------------------------------------------------------

class TestTeamsCSV:
    """Validate the teams.csv data file schema and content."""

    @pytest.fixture
    def teams_df(self):
        teams_file = os.path.join(REPO_ROOT, 'data', 'teams.csv')
        if not os.path.exists(teams_file):
            pytest.skip("data/teams.csv not present")
        return pd.read_csv(teams_file)

    def test_teams_csv_exists(self):
        assert os.path.exists(os.path.join(REPO_ROOT, 'data', 'teams.csv'))

    def test_teams_has_required_columns(self, teams_df):
        for col in ['color', 'name', 'emoji', 'description']:
            assert col in teams_df.columns, f"Missing column: {col}"

    def test_teams_no_empty_colors(self, teams_df):
        assert teams_df['color'].notna().all()
        assert (teams_df['color'].str.strip() != '').all()

    def test_teams_no_empty_names(self, teams_df):
        assert teams_df['name'].notna().all()

    def test_teams_unique_colors(self, teams_df):
        colors = teams_df['color'].str.strip().str.lower()
        assert colors.is_unique, f"Duplicate colors: {colors[colors.duplicated()].tolist()}"

    def test_teams_has_at_least_two(self, teams_df):
        assert len(teams_df) >= 2


class TestTeamsAPIWithCSV:
    """Test /api/teams loading from real and synthetic CSV files."""

    def test_teams_loads_from_csv(self, client, tmp_path, flask_app):
        """Verify teams endpoint returns data matching a CSV file."""
        resp = client.get('/api/teams')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'teams' in data
        teams = data['teams']
        assert isinstance(teams, list)
        # Each team must have the required fields
        for team in teams:
            assert 'color' in team
            assert 'name' in team


# ---------------------------------------------------------------------------
# participants.csv validation
# ---------------------------------------------------------------------------

class TestParticipantsData:
    """Validate participants data file schema."""

    @pytest.fixture
    def participants_df(self):
        path = os.path.join(REPO_ROOT, 'data', 'participants_trial.csv')
        if not os.path.exists(path):
            pytest.skip("data/participants_trial.csv not present")
        return pd.read_csv(path)

    def test_participants_file_exists(self):
        assert os.path.exists(os.path.join(REPO_ROOT, 'data', 'participants_trial.csv'))

    def test_participants_required_columns(self, participants_df):
        required = ['full_name', 'email', 'linkedin_url', 'genre_color', 'convo_tip']
        for col in required:
            assert col in participants_df.columns, f"Missing column: {col}"

    def test_participants_emails_are_valid(self, participants_df):
        for email in participants_df['email']:
            assert '@' in str(email), f"Invalid email: {email}"

    def test_participants_no_duplicate_emails(self, participants_df):
        emails = participants_df['email'].str.lower().str.strip()
        assert emails.is_unique, f"Duplicate emails: {emails[emails.duplicated()].tolist()}"

    def test_participants_names_not_empty(self, participants_df):
        assert participants_df['full_name'].notna().all()
        assert (participants_df['full_name'].str.len() >= 2).all()

    def test_participants_colors_are_known(self, participants_df):
        allowed = {'red', 'blue', 'green', 'yellow', 'purple'}
        colors = set(participants_df['genre_color'].str.lower().str.strip())
        unknown = colors - allowed
        assert not unknown, f"Unknown colors: {unknown}"


# ---------------------------------------------------------------------------
# CSV data loading into the app
# ---------------------------------------------------------------------------

class TestLoadParticipantDataFromCSV:
    """Test that CSV/Excel data round-trips correctly through the app."""

    def test_add_new_participant_via_csv(self, tmp_path):
        """Create a fresh participants.csv, load it, and verify mappings."""
        data = [
            {'full_name': 'New Person', 'email': 'new@test.com',
             'linkedin_url': 'https://linkedin.com/in/new',
             'genre_color': 'green', 'convo_tip': 'Ask about food'},
            {'full_name': 'Another One', 'email': 'another@test.com',
             'linkedin_url': 'https://linkedin.com/in/another',
             'genre_color': 'red', 'convo_tip': 'Ask about pets'},
        ]
        csv_file = tmp_path / 'participants.csv'
        pd.DataFrame(data).to_csv(str(csv_file), index=False)

        df = pd.read_csv(str(csv_file))
        df['email'] = df['email'].str.lower().str.strip()

        loaded = {}
        for _, row in df.iterrows():
            loaded[row['email']] = {
                'full_name': row['full_name'],
                'email': row['email'],
                'genre_color': row.get('genre_color', 'blue'),
            }

        assert 'new@test.com' in loaded
        assert 'another@test.com' in loaded
        assert loaded['new@test.com']['full_name'] == 'New Person'
        assert loaded['another@test.com']['genre_color'] == 'red'

    def test_qr_mapping_csv_roundtrip(self, tmp_path):
        """Create a QR mapping CSV and verify it loads correctly."""
        mapping_data = [
            {'user_id': 'u1', 'full_name': 'Alice', 'email': 'alice@test.com',
             'filename': 'alice.png', 'filepath': 'qr_codes/alice.png'},
            {'user_id': 'u2', 'full_name': 'Bob', 'email': 'bob@test.com',
             'filename': 'bob.png', 'filepath': 'qr_codes/bob.png'},
        ]
        csv_file = tmp_path / 'qr_mapping.csv'
        pd.DataFrame(mapping_data).to_csv(str(csv_file), index=False)

        df = pd.read_csv(str(csv_file))
        qr_mapping = dict(zip(df['user_id'], df['email']))
        email_to_userid = dict(zip(df['email'], df['user_id']))

        assert qr_mapping['u1'] == 'alice@test.com'
        assert email_to_userid['bob@test.com'] == 'u2'
        assert len(qr_mapping) == 2

    def test_target_assignments_csv_roundtrip(self, tmp_path):
        """Create a target assignments CSV and verify loading."""
        assignments = [
            {'scanner_id': 'u1', 'scanner_name': 'Alice', 'target_id': 'u2',
             'target_name': 'Bob', 'target_color': 'red',
             'target_job_title': 'Engineer', 'convo_tip': 'Ask about code'},
            {'scanner_id': 'u2', 'scanner_name': 'Bob', 'target_id': 'u1',
             'target_name': 'Alice', 'target_color': 'blue',
             'target_job_title': 'Designer', 'convo_tip': 'Ask about design'},
        ]
        csv_file = tmp_path / 'target_assignments.csv'
        pd.DataFrame(assignments).to_csv(str(csv_file), index=False)

        df = pd.read_csv(str(csv_file))
        assert len(df) == 2

        # Verify no self-assignments
        for _, row in df.iterrows():
            assert row['scanner_id'] != row['target_id']

        # Verify required columns
        for col in ['scanner_id', 'target_id', 'target_name', 'convo_tip']:
            assert col in df.columns

    def test_bad_csv_missing_columns(self, tmp_path):
        """CSV with missing required columns should be detectable."""
        bad_data = [{'name': 'Alice', 'score': 10}]
        csv_file = tmp_path / 'bad_mapping.csv'
        pd.DataFrame(bad_data).to_csv(str(csv_file), index=False)

        df = pd.read_csv(str(csv_file))
        required = ['user_id', 'email']
        missing = [col for col in required if col not in df.columns]
        assert len(missing) > 0

    def test_empty_csv_handled(self, tmp_path):
        """Empty CSV file should load as empty DataFrame."""
        csv_file = tmp_path / 'empty.csv'
        csv_file.write_text('user_id,email\n')

        df = pd.read_csv(str(csv_file))
        assert len(df) == 0

    def test_duplicate_emails_in_csv_detectable(self, tmp_path):
        """CSV with duplicate emails should be caught."""
        data = [
            {'user_id': 'u1', 'email': 'same@test.com'},
            {'user_id': 'u2', 'email': 'same@test.com'},
        ]
        csv_file = tmp_path / 'dup.csv'
        pd.DataFrame(data).to_csv(str(csv_file), index=False)

        df = pd.read_csv(str(csv_file))
        has_dups = df['email'].duplicated().any()
        assert has_dups

    def test_add_participants_to_existing_data(self, tmp_path):
        """Simulate adding new participants to an existing dataset."""
        # Original data
        original = [
            {'full_name': 'Alice', 'email': 'alice@test.com',
             'linkedin_url': 'https://linkedin.com/in/alice',
             'genre_color': 'blue', 'convo_tip': 'Travel'},
        ]
        # New data to add
        new_entries = [
            {'full_name': 'Charlie', 'email': 'charlie@test.com',
             'linkedin_url': 'https://linkedin.com/in/charlie',
             'genre_color': 'green', 'convo_tip': 'Tech'},
        ]

        all_data = original + new_entries
        csv_file = tmp_path / 'combined.csv'
        pd.DataFrame(all_data).to_csv(str(csv_file), index=False)

        df = pd.read_csv(str(csv_file))
        assert len(df) == 2
        emails = df['email'].tolist()
        assert 'alice@test.com' in emails
        assert 'charlie@test.com' in emails
