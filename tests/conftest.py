# -- Import external dependencies ------
import importlib.util, pytest, shutil
import numpy as np
from pathlib import Path

# -- Define default paths --------------
DATA_DIR = Path(__file__).parent / "data"
TOMO_PATH = DATA_DIR / "test_tomogram.mrc"
SEG_PATH = DATA_DIR / "test_segmentation.mrc"
LABELLED_PATH = DATA_DIR / "test_segmentation_labelled.mrc"

# -- Define generator parameters -------
# -- nb: must stay in sync with generate_test_data.py
N_EVS = 4
SEED = 42
VOX_NM = 0.536

# -- Define _load_generator helper function
def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_test_data",
        DATA_DIR / "generate_test_data.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# -- Define fixtures -------------------
@pytest.fixture(scope="session")
def synthetic_mrc_files():
    """
    Ensure test_tomogram.mrc and test_segmentation.mrc exist in tests/data/.
    Generates them from the bundled generator if they are absent.
    Returns (tomo_path, seg_path).
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not TOMO_PATH.exists() or not SEG_PATH.exists():
        gen = _load_generator()
        rng = np.random.default_rng(SEED)
        shape = (gen.Z, gen.Y, gen.X)
        ev_defs = gen.generate_ev_defs(N_EVS, rng, shape)
        # Build and write segmentation first (lower memory)
        seg = gen.build_segmentation(shape, ev_defs)
        gen.write_mrc(seg, SEG_PATH, gen.VOX_A)
        del seg
        # Build and write tomogram
        tomo = gen.build_tomogram(shape, ev_defs, rng)
        gen.write_mrc(tomo, TOMO_PATH, gen.VOX_A)
        del tomo
    return [TOMO_PATH, SEG_PATH]

@pytest.fixture(scope="session")
def tomo_path(synthetic_mrc_files):
    """Path to the synthetic greyscale tomogram MRC."""
    return synthetic_mrc_files[0]


@pytest.fixture(scope="session")
def seg_path(synthetic_mrc_files):
    """Path to the synthetic binary segmentation mask MRC."""
    return synthetic_mrc_files[1]


@pytest.fixture(scope="session")
def labelled_path(seg_path, tmp_path_factory):
    """
    Run label_components on the synthetic segmentation once per session and
    cache the labelled MRC in tests/data/. If the cached file already exists
    it is used directly.
    """
    if LABELLED_PATH.exists():
        return LABELLED_PATH
    from evaluator.commands.label.label import label_components
    tmp = tmp_path_factory.mktemp("label_cache")
    label_components(seg_path, tmp)
    label_out = (
        tmp
        / "evaluator"
        / "results"
        / "label"
        / "test_segmentation_labelled.mrc"
    )
    assert label_out.exists(), (
        "label_components did not produce the expected output file. "
        "Check that label_components writes to <out_dir>/evaluator/results/label/."
    )
    shutil.copy(label_out, LABELLED_PATH)
    return LABELLED_PATH