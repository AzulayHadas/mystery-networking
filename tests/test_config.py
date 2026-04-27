"""
Configuration and project structure validation tests.
Ensures the project is correctly set up for deployment and development.
"""
import sys
import os
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BACKEND_DIR = os.path.join(REPO_ROOT, 'backend')


class TestProjectStructure:
    """Verify essential project files and directories exist."""

    def test_backend_dir_exists(self):
        assert os.path.isdir(BACKEND_DIR)

    def test_frontend_dir_exists(self):
        assert os.path.isdir(os.path.join(REPO_ROOT, 'frontend'))

    def test_data_dir_exists(self):
        assert os.path.isdir(os.path.join(REPO_ROOT, 'data'))

    def test_requirements_txt_exists(self):
        assert os.path.isfile(os.path.join(BACKEND_DIR, 'requirements.txt'))

    def test_app_py_exists(self):
        assert os.path.isfile(os.path.join(BACKEND_DIR, 'app.py'))

    def test_models_py_exists(self):
        assert os.path.isfile(os.path.join(BACKEND_DIR, 'models.py'))

    def test_scoring_py_exists(self):
        assert os.path.isfile(os.path.join(BACKEND_DIR, 'scoring.py'))

    def test_admin_py_exists(self):
        assert os.path.isfile(os.path.join(BACKEND_DIR, 'admin.py'))

    def test_teams_csv_exists(self):
        assert os.path.isfile(os.path.join(REPO_ROOT, 'data', 'teams.csv'))

    def test_frontend_html_files_exist(self):
        frontend = os.path.join(REPO_ROOT, 'frontend')
        for name in ['participant.html', 'dashboard.html', 'admin.html']:
            assert os.path.isfile(os.path.join(frontend, name)), f"Missing {name}"

    def test_frontend_js_files_exist(self):
        js_dir = os.path.join(REPO_ROOT, 'frontend', 'js')
        for name in ['participant-js.js', 'dashboard.js', 'firebase-config.js']:
            assert os.path.isfile(os.path.join(js_dir, name)), f"Missing {name}"

    def test_ci_workflow_exists(self):
        assert os.path.isfile(
            os.path.join(REPO_ROOT, '.github', 'workflows', 'ci.yml'))

    def test_pytest_ini_exists(self):
        assert os.path.isfile(os.path.join(REPO_ROOT, 'pytest.ini'))


class TestRequirementsTxt:
    """Verify requirements.txt has necessary packages."""

    @pytest.fixture
    def requirements(self):
        path = os.path.join(BACKEND_DIR, 'requirements.txt')
        with open(path) as f:
            return f.read().lower()

    def test_flask_in_requirements(self, requirements):
        assert 'flask' in requirements

    def test_pandas_in_requirements(self, requirements):
        assert 'pandas' in requirements

    def test_firebase_admin_in_requirements(self, requirements):
        assert 'firebase-admin' in requirements

    def test_flask_cors_in_requirements(self, requirements):
        assert 'flask-cors' in requirements

    def test_gunicorn_in_requirements(self, requirements):
        assert 'gunicorn' in requirements

    def test_qrcode_in_requirements(self, requirements):
        assert 'qrcode' in requirements


class TestBackendImports:
    """Verify all backend modules import without errors."""

    def test_import_models(self):
        sys.path.insert(0, BACKEND_DIR)
        from models import User, Scan
        assert User is not None
        assert Scan is not None

    def test_import_scoring(self):
        sys.path.insert(0, BACKEND_DIR)
        from scoring import ScoringEngine
        assert ScoringEngine is not None

    def test_import_admin(self):
        sys.path.insert(0, BACKEND_DIR)
        from admin import AdminPanel
        assert AdminPanel is not None


class TestGitignore:
    """Verify .gitignore covers sensitive and generated files."""

    @pytest.fixture
    def gitignore_content(self):
        path = os.path.join(REPO_ROOT, '.gitignore')
        if not os.path.exists(path):
            pytest.skip(".gitignore not present")
        with open(path) as f:
            return f.read()

    def test_gitignore_has_pycache(self, gitignore_content):
        assert '__pycache__' in gitignore_content

    def test_gitignore_has_env(self, gitignore_content):
        # Should ignore virtual environments
        assert '.env' in gitignore_content or 'venv' in gitignore_content
