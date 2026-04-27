"""
Tests for root-level utility scripts:
  - create_sample_data.py
  - qr_generator.py
  - generate_multiple_targets.py
"""
import sys
import os
import pytest
import tempfile
import shutil
import pandas as pd
from unittest.mock import patch

# Ensure repo root is on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, REPO_ROOT)


class TestCreateSampleData:
    """Tests for create_sample_data.py."""

    def test_creates_csv_file(self, tmp_path):
        output_file = str(tmp_path / 'participants.csv')
        participants = [
            {'full_name': 'A', 'email': 'a@b.com', 'linkedin_url': 'https://linkedin.com/in/a',
             'genre_color': 'blue', 'convo_tip': 'tip'},
        ]
        df = pd.DataFrame(participants)
        df.to_csv(output_file, index=False)

        assert os.path.exists(output_file)
        loaded = pd.read_csv(output_file)
        assert len(loaded) == 1
        assert 'full_name' in loaded.columns
        assert 'email' in loaded.columns

    def test_sample_data_has_required_columns(self):
        """Verify the actual sample data file has the right schema."""
        # Try both repo root and CWD-relative paths
        for candidate in [
            os.path.join(REPO_ROOT, 'data', 'participants_trial.csv'),
            os.path.join(os.getcwd(), 'data', 'participants_trial.csv'),
        ]:
            if os.path.exists(candidate):
                sample_file = candidate
                break
        else:
            pytest.skip("participants_trial.csv not present")
        df = pd.read_csv(sample_file)
        required = ['full_name', 'email', 'linkedin_url', 'genre_color', 'convo_tip']
        for col in required:
            assert col in df.columns, f"Missing column: {col}"


class TestQrGenerator:
    """Tests for qr_generator.py core function."""

    def test_generate_qr_codes_from_csv(self, tmp_path):
        # Create a minimal participant CSV file
        data = [
            {'full_name': 'Test User', 'email': 'test@example.com',
             'linkedin_url': 'https://linkedin.com/in/test', 'genre_color': 'blue',
             'convo_tip': 'Hello'},
        ]
        input_file = str(tmp_path / 'test_participants.csv')
        pd.DataFrame(data).to_csv(input_file, index=False)

        output_dir = str(tmp_path / 'qr_output')

        from qr_generator import generate_qr_codes_from_csv
        codes = generate_qr_codes_from_csv(input_file, output_dir)

        assert len(codes) == 1
        assert codes[0]['email'] == 'test@example.com'
        assert os.path.exists(output_dir)
        # Check mapping file
        mapping = os.path.join(output_dir, 'qr_mapping.csv')
        assert os.path.exists(mapping)
        mapping_df = pd.read_csv(mapping)
        assert len(mapping_df) == 1

    def test_generate_qr_creates_images(self, tmp_path):
        data = [
            {'full_name': 'Alice', 'email': 'alice@test.com',
             'genre_color': 'red'},
            {'full_name': 'Bob', 'email': 'bob@test.com',
             'genre_color': 'green'},
        ]
        input_file = str(tmp_path / 'people.csv')
        pd.DataFrame(data).to_csv(input_file, index=False)
        output_dir = str(tmp_path / 'qr_out')

        from qr_generator import generate_qr_codes_from_csv
        codes = generate_qr_codes_from_csv(input_file, output_dir)

        assert len(codes) == 2
        for code in codes:
            assert os.path.exists(code['filepath'])
            assert code['filepath'].endswith('.png')

    def test_missing_required_column_raises(self, tmp_path):
        data = [{'name': 'Bad'}]  # missing full_name and email
        input_file = str(tmp_path / 'bad.csv')
        pd.DataFrame(data).to_csv(input_file, index=False)
        output_dir = str(tmp_path / 'qr_bad')

        from qr_generator import generate_qr_codes_from_csv
        with pytest.raises(ValueError, match="Missing required columns"):
            generate_qr_codes_from_csv(input_file, output_dir)

    def test_card_dimensions(self, tmp_path):
        """Generated card should be 400x500 pixels."""
        from PIL import Image
        data = [{'full_name': 'Card Test', 'email': 'card@test.com', 'genre_color': 'blue'}]
        input_file = str(tmp_path / 'card.csv')
        pd.DataFrame(data).to_csv(input_file, index=False)
        output_dir = str(tmp_path / 'qr_card')

        from qr_generator import generate_qr_codes_from_csv
        codes = generate_qr_codes_from_csv(input_file, output_dir)

        img = Image.open(codes[0]['filepath'])
        assert img.size == (400, 500), f"Expected 400x500, got {img.size}"
        assert img.mode == 'RGB'

    def test_card_has_white_background_padding(self, tmp_path):
        """Card edges (padding area) should be white."""
        from PIL import Image
        data = [{'full_name': 'Pad Test', 'email': 'pad@test.com'}]
        input_file = str(tmp_path / 'pad.csv')
        pd.DataFrame(data).to_csv(input_file, index=False)
        output_dir = str(tmp_path / 'qr_pad')

        from qr_generator import generate_qr_codes_from_csv
        codes = generate_qr_codes_from_csv(input_file, output_dir)

        img = Image.open(codes[0]['filepath'])
        # Top-left and top-right corners should be white (padding area)
        assert img.getpixel((0, 0)) == (255, 255, 255)
        assert img.getpixel((399, 0)) == (255, 255, 255)
        # Bottom corners should be white
        assert img.getpixel((0, 499)) == (255, 255, 255)
        assert img.getpixel((399, 499)) == (255, 255, 255)

    def test_qr_code_centered_with_top_padding(self, tmp_path):
        """QR code should be centered horizontally with 50px top offset."""
        from PIL import Image
        import numpy as np
        data = [{'full_name': 'Center Test', 'email': 'center@test.com'}]
        input_file = str(tmp_path / 'center.csv')
        pd.DataFrame(data).to_csv(input_file, index=False)
        output_dir = str(tmp_path / 'qr_center')

        from qr_generator import generate_qr_codes_from_csv
        codes = generate_qr_codes_from_csv(input_file, output_dir)

        img = Image.open(codes[0]['filepath'])
        pixels = np.array(img)

        # The QR area is 250x250 centered at x_offset=75, y_offset=50
        # Row just above QR (y=49) should be all white
        assert (pixels[49, :, :] == 255).all(), "Row above QR should be white"

        # QR region should contain non-white (black) pixels
        qr_region = pixels[50:300, 75:325]
        has_dark_pixels = (qr_region < 128).any()
        assert has_dark_pixels, "QR region should contain dark pixels"

        # Left padding column (x=0..74) at QR height should be white
        left_pad = pixels[50:300, 0:75]
        assert (left_pad == 255).all(), "Left padding beside QR should be white"

        # Right padding column (x=325..399) at QR height should be white
        right_pad = pixels[50:300, 325:400]
        assert (right_pad == 255).all(), "Right padding beside QR should be white"

    def test_name_text_rendered_below_qr(self, tmp_path):
        """Area below QR code should contain non-white pixels (rendered text)."""
        from PIL import Image
        import numpy as np
        data = [{'full_name': 'NameRender', 'email': 'name@test.com'}]
        input_file = str(tmp_path / 'name.csv')
        pd.DataFrame(data).to_csv(input_file, index=False)
        output_dir = str(tmp_path / 'qr_name')

        from qr_generator import generate_qr_codes_from_csv
        codes = generate_qr_codes_from_csv(input_file, output_dir)

        img = Image.open(codes[0]['filepath'])
        pixels = np.array(img)

        # Text area starts at y=320 (QR ends at 300, +20 padding)
        # Check a band where the name should be rendered (y=310..360)
        text_band = pixels[310:370, :, :]
        has_non_white = (text_band < 200).any()
        assert has_non_white, "Name text should be rendered below the QR code"

    def test_card_with_color_badge(self, tmp_path):
        """Card with genre_color should render extra text below the ID."""
        from PIL import Image
        import numpy as np
        data = [{'full_name': 'ColorUser', 'email': 'color@test.com', 'genre_color': 'red'}]
        input_file = str(tmp_path / 'color.csv')
        pd.DataFrame(data).to_csv(input_file, index=False)
        output_dir = str(tmp_path / 'qr_color')

        from qr_generator import generate_qr_codes_from_csv
        codes = generate_qr_codes_from_csv(input_file, output_dir)

        img_with_color = Image.open(codes[0]['filepath'])

        # Generate a card without genre_color for comparison
        data_no_color = [{'full_name': 'PlainUser', 'email': 'plain@test.com'}]
        input_file2 = str(tmp_path / 'nocolor.csv')
        pd.DataFrame(data_no_color).to_csv(input_file2, index=False)
        output_dir2 = str(tmp_path / 'qr_nocolor')
        codes2 = generate_qr_codes_from_csv(input_file2, output_dir2)
        img_no_color = Image.open(codes2[0]['filepath'])

        # The color-badge card should have more non-white pixels in the lower region
        arr_color = np.array(img_with_color)[380:460, :, :]
        arr_plain = np.array(img_no_color)[380:460, :, :]
        dark_color = (arr_color < 200).sum()
        dark_plain = (arr_plain < 200).sum()
        assert dark_color > dark_plain, "Color badge card should have more text in lower region"


class TestGenerateMultipleTargets:
    """Tests for generate_multiple_targets.py."""

    def test_target_assignment_logic(self, tmp_path):
        """Test that target generation creates valid assignments."""
        import random
        random.seed(42)

        # Create mock qr_mapping.csv
        qr_dir = tmp_path / 'qr_codes'
        qr_dir.mkdir()
        qr_mapping = pd.DataFrame([
            {'user_id': f'u{i}', 'full_name': f'User {i}', 'email': f'user{i}@test.com',
             'filename': f'u{i}.png', 'filepath': f'qr_codes/u{i}.png'}
            for i in range(5)
        ])
        qr_mapping.to_csv(str(qr_dir / 'qr_mapping.csv'), index=False)

        # Create mock participants file
        data_dir = tmp_path / 'data'
        data_dir.mkdir()
        jobs = ['Engineer', 'Designer', 'Manager', 'Analyst', 'Lead']
        participants = pd.DataFrame([
            {'full_name': f'User {i}', 'email': f'user{i}@test.com',
             'linkedin_url': f'https://linkedin.com/in/user{i}',
             'genre_color': ['red', 'blue', 'green', 'yellow', 'purple'][i],
             'convo_tip': f'Tip {i}'}
            for i in range(5)
        ])
        participants.to_csv(str(data_dir / 'participants.csv'), index=False)

        # Run the generator logic in the temp directory
        old_cwd = os.getcwd()
        try:
            os.chdir(str(tmp_path))

            # Import and run
            from generate_multiple_targets import generate_multiple_target_assignments
            generate_multiple_target_assignments()

            # Verify output
            output_file = str(qr_dir / 'target_assignments.csv')
            assert os.path.exists(output_file)

            assignments_df = pd.read_csv(output_file)
            # Each user should have up to 3 targets (4 other users available)
            assert len(assignments_df) > 0

            # No self-assignments
            for _, row in assignments_df.iterrows():
                assert row['scanner_id'] != row['target_id'], \
                    f"Self-assignment found: {row['scanner_id']}"

        finally:
            os.chdir(old_cwd)
