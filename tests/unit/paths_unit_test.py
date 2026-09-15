# -- Define external dependencies ------
import pytest
from pathlib import Path

# -- Define internal dependencies ------
from evaluator.utils.paths import checkUniqueFileName, generate_command_output_dir

# -- Define output file structure generation test
class TestGenerateCommandOutputDir:
    def test_creates_expected_subdirectory(self, tmp_path):
        evaluator_dir = tmp_path / "evaluator"
        out = generate_command_output_dir(evaluator_dir, "analyse")
        assert out.exists() and out.is_dir()
        assert out == evaluator_dir / "analyse"
    def test_creates_label_subdirectory(self, tmp_path):
        evaluator_dir = tmp_path / "evaluator"
        out = generate_command_output_dir(evaluator_dir, "label")
        assert out == evaluator_dir / "label"
        assert out.exists()
    def test_creates_visualise_subdirectory(self, tmp_path):
        evaluator_dir = tmp_path / "evaluator"
        out = generate_command_output_dir(evaluator_dir, "visualise")
        assert out == evaluator_dir / "visualise"
        assert out.exists()
    def test_idempotent_on_existing_correct_path(self, tmp_path):
        """Calling twice on the same root must return the same path."""
        evaluator_dir = tmp_path / "evaluator"
        out1 = generate_command_output_dir(evaluator_dir, "analyse")
        out2 = generate_command_output_dir(evaluator_dir, "analyse")
        assert out1 == out2
    def test_does_not_raise_if_directory_already_exists(self, tmp_path):
        evaluator_dir = tmp_path / "evaluator"
        generate_command_output_dir(evaluator_dir, "analyse")
        # Must not raise FileExistsError on a second call
        generate_command_output_dir(evaluator_dir, "analyse")

# -- Define unique output file name check test
class TestCheckUniqueFileName:
    # --- analyse command ---
    def test_analyse_base_name(self, tmp_path):
        p = checkUniqueFileName(tmp_path, "analyse")
        assert p.name == "evaluator-analyse_results.csv"
        assert p.parent == tmp_path
    def test_analyse_increments_on_conflict(self, tmp_path):
        (tmp_path / "evaluator-analyse_results.csv").touch()
        p = checkUniqueFileName(tmp_path, "analyse")
        assert p.name == "evaluator-analyse_results-1.csv"
    def test_analyse_increments_through_multiple_conflicts(self, tmp_path):
        (tmp_path / "evaluator-analyse_results.csv").touch()
        (tmp_path / "evaluator-analyse_results-1.csv").touch()
        p = checkUniqueFileName(tmp_path, "analyse")
        assert p.name == "evaluator-analyse_results-2.csv"
    # --- label command ---
    def test_label_constructs_correct_name(self, tmp_path):
        p = checkUniqueFileName(
            tmp_path, "label",
            orig_name="tomo_seg", overlay_style="both", fmt="png"
        )
        assert p.name == "tomo_seg_overlay-both.png"
    def test_label_increments_on_conflict(self, tmp_path):
        (tmp_path / "tomo_seg_overlay-both.png").touch()
        p = checkUniqueFileName(
            tmp_path, "label",
            orig_name="tomo_seg", overlay_style="both", fmt="png"
        )
        assert p.name == "tomo_seg_overlay-both-1.png"
    # --- visualise command ---
    def test_visualise_constructs_correct_name(self, tmp_path):
        p = checkUniqueFileName(
            tmp_path, "visualise",
            orig_name="tomo_1", vis_out="Zstack-movie", fmt="mp4"
        )
        assert p.name == "tomo_1_Zstack-movie.mp4"
    def test_visualise_isoview_name(self, tmp_path):
        p = checkUniqueFileName(
            tmp_path, "visualise",
            orig_name="tomo_seg", vis_out="isometric-view", fmt="png"
        )
        assert p.name == "tomo_seg_isometric-view.png"