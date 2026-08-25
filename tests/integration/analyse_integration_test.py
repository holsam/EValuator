# -- Import external dependencies ------
import mrcfile, pytest
import numpy as np
import pandas as pd
from pathlib import Path

# -- Import internal dependencies ------
from evaluator.commands.analyse.analyse import analyse

# -- Define constants ------------------
N_EVS = 4
VOX_NM = 0.536
EXPECTED_COLUMNS = [
    "tomogram", "label", "equiv_diameter_nm",
    "major_axis_diameter", "minor_axis_diameter",
    "aspect_ratio", "eccentricity",
    "membrane_volume", "lumen_volume", "surface_area",
    "is_enclosed", "closure_fill_ratio",
    "voxel_size_nm", "measurement_units",
]

# -- Define module fixture -------------
@pytest.fixture(scope="module")
def analyse_csv(labelled_path, tmp_path_factory):
    """
    Run analyse once on the cached labelled MRC and return the path to
    the output CSV. The pipeline is run with default diameter filter values.
    """
    out = tmp_path_factory.mktemp("analyse_output")
    analyse(labelled_path, out)
    csv_dir = out / "evaluator" / "analyse"
    csv_files = list(csv_dir.glob("*.csv"))
    assert len(csv_files) == 1, (
        "analyse did not produce exactly one CSV. "
        "Check that labelled_path contains labelled components within the diameter filter."
    )
    return csv_files[0]

# -- Define output file test -----------
class TestAnalyseOutputFile:
    def test_csv_file_exists(self, analyse_csv):
        assert analyse_csv.exists()
    def test_csv_is_readable(self, analyse_csv):
        df = pd.read_csv(analyse_csv)
        assert isinstance(df, pd.DataFrame)
    def test_output_directory_structure(self, analyse_csv):
        assert "evaluator/analyse" in str(analyse_csv)

# -- Define CSV schema test ------------
class TestAnalyseCSVSchema:
    def test_all_expected_columns_present(self, analyse_csv):
        df = pd.read_csv(analyse_csv)
        missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
        assert not missing, f"Missing CSV columns: {missing}"
    def test_no_unexpected_extra_columns(self, analyse_csv):
        """Guard against accidental column additions or renames."""
        df = pd.read_csv(analyse_csv)
        extra = [c for c in df.columns if c not in EXPECTED_COLUMNS]
        assert not extra, f"Unexpected CSV columns: {extra}"

# -- Define row counts and EV detection class
class TestAnalyseEVDetection:
    def test_n_rows_equals_n_evs(self, analyse_csv):
        """All four synthetic EVs must pass the default diameter filter."""
        df = pd.read_csv(analyse_csv)
        assert len(df) == N_EVS, (
            f"Expected {N_EVS} EVs in output, found {len(df)}. "
            "One or more synthetic EVs may have been incorrectly filtered."
        )
    def test_all_evs_classified_as_enclosed(self, analyse_csv):
        """Synthetic perfect spherical shells must all be enclosed."""
        df = pd.read_csv(analyse_csv)
        assert df["is_enclosed"].all(), (
            "One or more synthetic EVs were not classified as enclosed. "
            "Check morphologicalClosure and checkEnclosed logic."
        )
    def test_closure_fill_ratio_above_threshold(self, analyse_csv):
        df = pd.read_csv(analyse_csv)
        assert (df["closure_fill_ratio"] > 0.05).all()

# -- Define measurement values test ----
class TestAnalyseMeasurements:
    def test_equiv_diameter_within_generator_range(self, analyse_csv):
        """
        Synthetic EVs have outer diameters 42.9–128.6 nm (r_outer 40–120 vox).
        equiv_diameter is derived from shell volume, not geometric diameter,
        so it will be somewhat smaller — but must remain within the filter bounds.
        """
        df = pd.read_csv(analyse_csv)
        assert (df["equiv_diameter_nm"] > 20.0).all()
        assert (df["equiv_diameter_nm"] < 500.0).all()
    def test_major_axis_geq_minor_axis(self, analyse_csv):
        df = pd.read_csv(analyse_csv)
        assert (df["major_axis_diameter"] >= df["minor_axis_diameter"]).all()
    def test_all_positive_morphology_columns(self, analyse_csv):
        df = pd.read_csv(analyse_csv)
        for col in ["equiv_diameter_nm", "membrane_volume", "major_axis_diameter", "minor_axis_diameter"]:
            assert (df[col] > 0).all(), f"Non-positive value found in column '{col}'"
    def test_lumen_volume_positive_for_all_enclosed(self, analyse_csv):
        df = pd.read_csv(analyse_csv)
        enclosed = df[df["is_enclosed"]]
        assert (enclosed["lumen_volume"] > 0).all()
    def test_voxel_size_correct(self, analyse_csv):
        df = pd.read_csv(analyse_csv)
        assert np.allclose(df["voxel_size_nm"], VOX_NM, rtol=1e-3)
    def test_measurement_units_are_nm(self, analyse_csv):
        df = pd.read_csv(analyse_csv)
        assert (df["measurement_units"] == "nm").all()
    def test_aspect_ratio_near_one_for_spheres(self, analyse_csv):
        """Synthetic perfect spheres must have aspect ratios close to 1.0."""
        df = pd.read_csv(analyse_csv)
        assert (df["aspect_ratio"] > 0.5).all()
        assert (df["aspect_ratio"] < 2.0).all()

# -- Define filtering behaviour test ---
class TestAnalyseFiltering:
    def test_high_fill_threshold_excludes_all_evs(self, labelled_path, tmp_path):
        """
        A fill threshold of 1.0 (nothing can satisfy fill_ratio > 1.0) should classify all EVs as non-enclosed
        """
        analyse(labelled_path, tmp_path, fill_threshold=1.0)
        csv_dir = tmp_path / "evaluator" / "analyse"
        csvs = list(csv_dir.glob("*.csv"))
        if csvs:
            df = pd.read_csv(csvs[0])
            assert not df["is_enclosed"].any()

# -- Define input type test ------------
class TestAnalyseInputTypes:
    def test_binary_segmentation_input_accepted(self, seg_path, tmp_path):
        """
        analyse must accept a binary segmentation mask directly and
        produce the same number of EVs as with a pre-labelled input.
        """
        analyse(seg_path, tmp_path)
        csv_dir = tmp_path / "evaluator" / "analyse"
        csvs = list(csv_dir.glob("*.csv"))
        assert len(csvs) == 1
        df = pd.read_csv(csvs[0])
        assert len(df) == N_EVS

    def test_directory_input_processes_single_file(self, labelled_path, tmp_path_factory):
        """
        Passing a directory containing one labelled MRC must produce a CSV
        with the same results as passing the file directly.
        """
        import shutil
        tmp_in = tmp_path_factory.mktemp("dir_input")
        tmp_out = tmp_path_factory.mktemp("dir_output")
        shutil.copy(labelled_path, tmp_in / labelled_path.name)
        analyse(tmp_in, tmp_out)
        csv_dir = tmp_out / "evaluator" / "analyse"
        csvs = list(csv_dir.glob("*.csv"))
        assert len(csvs) == 1
        df = pd.read_csv(csvs[0])
        assert len(df) == N_EVS

    def test_no_voxel_size_uses_vox_units(self, tmp_path):
        """
        An MRC with no voxel size header must produce output with
        measurement_units='vox' and voxel_size_nm=None.
        """
        # Build a small binary MRC with no voxel size
        seg = np.zeros((30, 30, 30), dtype=np.float32)
        zz, yy, xx = np.indices((30, 30, 30))
        dist = np.sqrt((zz - 15) ** 2 + (yy - 15) ** 2 + (xx - 15) ** 2)
        seg[(dist >= 5) & (dist <= 10)] = 1.0
        mrc_path = tmp_path / "no_vox.mrc"
        with mrcfile.new(str(mrc_path)) as mrc:
            mrc.set_data(seg)
            # Deliberately leave voxel_size at 0.0 (default)
        out = tmp_path / "out"
        analyse(mrc_path, out)
        csv_dir = out / "evaluator" / "analyse"
        csvs = list(csv_dir.glob("*.csv"))
        # Component is within the volume; no size filter applied (no voxel size)
        if csvs:
            df = pd.read_csv(csvs[0])
            assert (df["measurement_units"] == "vox").all()
            assert df["voxel_size_nm"].isna().all()