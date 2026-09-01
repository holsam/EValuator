# ====================
# Import external dependencies
# ====================
import json, tomllib
import pytest

# ====================
# Import internal dependencies
# ====================
from evaluator.commands.model.model import model_evs
from evaluator.utils.mrc import readMRCFile

# ====================
# Define constants
# ====================
N_EVS = 4
VOX_NM = 0.536
R_OUTER_MIN, R_OUTER_MAX = 40, 120
SHELL_THICKNESS_VOX = 10
EXPECTED_RECORD_KEYS = {
    'chosen_model', 'centre', 'radius', 'radii', 'orientation',
    'rmse_nm', 'bic_sphere', 'bic_ellipsoid', 'reliability',
    'beam_axis', 'sphere_fit', 'ellipsoid_fit',
    'source_file', 'label_id',
}
# Loose bound: fits average across the shell thickness, so the fitted
# radius should sit somewhere between the inner and outer generator bounds.
MIN_PLAUSIBLE_RADIUS_NM = (R_OUTER_MIN - SHELL_THICKNESS_VOX) * VOX_NM
MAX_PLAUSIBLE_RADIUS_NM = R_OUTER_MAX * VOX_NM

# ====================
# Define module functions/fixtures
# ====================
def _results_json(model_dir, input_path):
    return model_dir / f'{input_path.stem}_model_results.json'

def _fitted_mrc(model_dir, input_path):
    return model_dir / f'{input_path.stem}_model_fitted.mrc'

@pytest.fixture(scope='module')
def model_output(labelled_path, tmp_path_factory):
    '''Run model once on the cached labelled MRC and return the output directory.'''
    out = tmp_path_factory.mktemp('model_output')
    model_evs(labelled_path, out)
    model_dir = out / 'evaluator' / 'model'
    assert model_dir.exists(), (
        'model_evs did not produce the expected output directory. '
        'Check that model_evs writes to <out_dir>/evaluator/model/.'
    )
    return model_dir

@pytest.fixture(scope='module')
def model_results(model_output):
    '''Load the results JSON produced by model_evs.'''
    results_path = model_output / 'test_segmentation_labelled_model_results.json'
    assert results_path.exists()
    payload = json.loads(results_path.read_text())
    return payload

# ====================
# Define output file tests
# ====================
class TestModelOutputFiles:
    def test_results_json_exists(self, model_output):
        assert (model_output / 'test_segmentation_labelled_model_results.json').exists()

    def test_fitted_mrc_exists(self, model_output):
        assert (model_output / 'test_segmentation_labelled_model_fitted.mrc').exists()

    def test_params_toml_exists(self, model_output):
        assert (model_output / 'params.toml').exists()

    def test_params_toml_readable(self, model_output):
        data = tomllib.loads((model_output / 'params.toml').read_text())
        assert 'rmse_relative_max' in data
        assert 'min_points' in data


# ====================
# Define results schema tests
# ====================
class TestModelResultsSchema:
    def test_payload_has_parameters_and_results(self, model_results):
        assert 'parameters' in model_results
        assert 'results' in model_results

    def test_n_results_equals_n_evs(self, model_results):
        assert len(model_results['results']) == N_EVS

    def test_all_expected_keys_present(self, model_results):
        for record in model_results['results']:
            missing = EXPECTED_RECORD_KEYS - record.keys()
            assert not missing, f'Missing keys in record: {missing}'

    def test_provenance_records_n_vesicles(self, model_results):
        assert model_results['parameters']['n_vesicles_fitted'] == N_EVS


# ====================
# Define fit quality tests
# ====================
class TestModelFitQuality:
    def test_all_reliable_for_clean_synthetic_spheres(self, model_results):
        '''Clean, well-sampled spherical shells should all pass the reliability gate.'''
        for record in model_results['results']:
            assert record['reliability']['is_reliable'] is True, (
                f'Label {record['label_id']} was not classified as reliable: '
                f'{record['reliability']}'
            )
    def test_radius_within_plausible_bounds(self, model_results):
        for record in model_results['results']:
            assert MIN_PLAUSIBLE_RADIUS_NM < record['radius'] < MAX_PLAUSIBLE_RADIUS_NM, (
                f'Label {record['label_id']} radius {record['radius']:.2f} nm '
                f'outside plausible bounds'
            )
    def test_chosen_model_is_recognised(self, model_results):
        valid = {
            'sphere', 'ellipsoid', 'sphere (anisotropy)',
            'sphere (beam-axis)', 'sphere (degenerate)',
        }
        for record in model_results['results']:
            assert record['chosen_model'] in valid

# ====================
# Define fitted MRC tests
# ====================
class TestModelFittedMRC:
    def test_fitted_mrc_readable(self, model_output):
        data, _ = readMRCFile(model_output / 'test_segmentation_labelled_model_fitted.mrc')
        assert data is not None
    def test_fitted_mrc_has_labels(self, model_output, model_results):
        '''All four synthetic EVs are reliable, so all four should be rasterised.'''
        data, _ = readMRCFile(model_output / 'test_segmentation_labelled_model_fitted.mrc')
        labels = set(int(v) for v in set(data.flatten().tolist()) if v != 0)
        expected = {record['label_id'] for record in model_results['results']}
        assert labels == expected

# ====================
# Define config override tests
# ====================
class TestModelConfigOverrides:
    def test_overrides_recorded_in_params_toml(self, labelled_path, tmp_path):
        '''Overrides must be captured in provenance/params.toml.'''
        model_evs(labelled_path, tmp_path, rmse_relative_max=0.5, min_points=5)
        params_path = tmp_path / 'evaluator' / 'model' / 'params.toml'
        data = tomllib.loads(params_path.read_text())
        assert data['rmse_relative_max'] == 0.5
        assert data['min_points'] == 5

    def test_strict_min_points_override_fails_reliability(self, labelled_path, tmp_path):
        '''
        A deliberately unreachable min_points threshold must flip every synthetic EV to unreliable, confirming the override reaches _assess_reliability rather than only being recorded in provenance.
        '''
        model_evs(labelled_path, tmp_path, min_points=10_000_000)
        results_path = tmp_path / 'evaluator' / 'model' / 'test_segmentation_labelled_model_results.json'
        payload = json.loads(results_path.read_text())
        for record in payload['results']:
            assert record['reliability']['is_reliable'] is False
            assert record['reliability']['count_ok'] is False