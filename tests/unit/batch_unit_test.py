'''
Unit tests for EValuator batch processing utilities.
'''

# ====================
# Import external dependencies
# ====================
import pytest

# ====================
# Import internal batch utilities
# ====================
from evaluator.utils import batch as batchutil

# ====================
# Define helper functions
# ====================
def _get_name(p) -> str:
    '''Return the name of a Path (basic function to test run_batch)'''
    return p.name

def _fail_on_1_mrc(p) -> str:
    if p.name == '1.mrc':
        raise ValueError()
    return p.name

# ====================
# Define tests
# ====================
class TestResolveMrcInputs:
    def test_resolve_mrc_inputs_single_file(self, tmp_path, monkeypatch):
        f = tmp_path / 'a.mrc'
        f.write_bytes(b'')
        monkeypatch.setattr(batchutil.mrcutil, 'validateMRCFile', lambda p: True)
        assert batchutil.resolve_mrc_inputs(f) == [f]

    def test_resolve_mrc_inputs_directory(self, tmp_path, monkeypatch):
        for name in ('b.mrc', 'a.mrc'):
            (tmp_path / name).write_bytes(b'')
        monkeypatch.setattr(batchutil.mrcutil, 'validateMRCFile', lambda p: True)
        result = batchutil.resolve_mrc_inputs(tmp_path)
        assert result == sorted(tmp_path.glob('*.mrc'))

    def test_resolve_mrc_inputs_drops_invalid(self, tmp_path, monkeypatch, caplog):
        good = tmp_path / 'good.mrc'
        bad = tmp_path / 'bad.mrc'
        good.write_bytes(b'')
        bad.write_bytes(b'')
        monkeypatch.setattr(batchutil.mrcutil, 'validateMRCFile', lambda p: p == good)
        result = batchutil.resolve_mrc_inputs(tmp_path)
        assert result == [good]

    def test_resolve_mrc_inputs_empty_dir_logs_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(batchutil.mrcutil, 'validateMRCFile', lambda p: True)
        result = batchutil.resolve_mrc_inputs(tmp_path)
        assert result == []

class TestRunBatch:
    def test_run_batch_all_succeed(self, tmp_path):
        files = [tmp_path / f'{i}.mrc' for i in range(3)]
        for f in files:
            f.write_bytes(b'')
        results = batchutil.run_batch(files, worker=_get_name)
        assert set(results) == {f.name for f in files}

    def test_run_batch_partial_failure_skips(self, tmp_path):
        files = [tmp_path / f'{i}.mrc' for i in range(3)]
        for f in files:
            f.write_bytes(b'')
        results = batchutil.run_batch(files, worker=_fail_on_1_mrc)
        assert set(results) == {'0.mrc', '2.mrc'}

    def test_run_batch_empty_input(self):
        assert batchutil.run_batch([], worker=lambda p: p) == []
