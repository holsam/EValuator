# -- Define external dependencies ------
import pytest
from pathlib import Path

# -- Define internal dependencies ------
from evaluator.utils.paths import checkUniqueFileName, generateOutputFileStructure

# -- Define output file structure generation test
class TestGenerateOutputFileStructure:
    def test_creates_expected_subdirectory(self, tmp_path):
        out = generateOutputFileStructure(tmp_path, "analyse")
        assert out.exists() and out.is_dir()
        assert out == tmp_path / "evaluator" / "results" / "analyse"
    def test_creates_label_subdirectory(self, tmp_path):
        out = generateOutputFileStructure(tmp_path, "label")
        assert out == tmp_path / "evaluator" / "results" / "label"
        assert out.exists()
    def test_creates_visualise_subdirectory(self, tmp_path):
        out = generateOutputFileStructure(tmp_path, "visualise")
        assert out == tmp_path / "evaluator" / "results" / "visualise"
        assert out.exists()
    def test_idempotent_on_existing_correct_path(self, tmp_path):
        """Calling twice on the same root must return the same path."""
        out1 = generateOutputFileStructure(tmp_path, "analyse")
        out2 = generateOutputFileStructure(tmp_path, "analyse")
        assert out1 == out2
    def test_does_not_raise_if_directory_already_exists(self, tmp_path):
        generateOutputFileStructure(tmp_path, "analyse")
        # Must not raise FileExistsError on a second call
        generateOutputFileStructure(tmp_path, "analyse")

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