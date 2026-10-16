# ====================
# Import external dependencies
# ====================
import csv, pytest
from openpyxl import load_workbook

# ====================
# Import internal dependencies
# ====================
from evaluator.commands.plot.plot import run_plot
from evaluator.commands.plot.utils.export import check_kaleido

def _kaleido_ok() -> bool:
    try:
        check_kaleido()
        return True
    except RuntimeError:
        return False

pytestmark = pytest.mark.skipif(not _kaleido_ok(), reason='kaleido/Chrome unavailable')

# ====================
# Define constants
# ====================
ANALYSE_COLUMNS = [
    'tomogram', 'label', 'equiv_diameter_nm', 'major_axis_diameter', 'minor_axis_diameter',
    'aspect_ratio', 'eccentricity', 'membrane_volume', 'lumen_volume', 'surface_area',
    'is_enclosed', 'closure_fill_ratio', 'sphere_rmse_rel', 'is_vesicle_like', 'qc_flags',
]

# ====================
# Define helper functions
# ====================
def _write_analyse_csv(path, n=12, tomogram='tomo1.mrc'):
    with path.open('w', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(ANALYSE_COLUMNS)
        for i in range(n):
            writer.writerow([
                tomogram, i, 60.0 + i, 70.0 + i, 50.0 + i, 1.2 + 0.01 * i, 0.4 + 0.01 * i,
                40000 + i * 100, 25000 + i * 50, 18000 + i * 80,
                bool(i % 3), 0.02 + 0.01 * i, 0.05 + 0.005 * i, i != 0, 'sphere_rmse' if i == 0 else '',
            ])

# ====================
# Define module fixtures
# ====================
@pytest.fixture(scope='module')
def analyse_csv(tmp_path_factory):
    path = tmp_path_factory.mktemp('plot_data') / 'analyse.csv'
    _write_analyse_csv(path)
    return path

@pytest.fixture(scope='module')
def plot_output(analyse_csv, tmp_path_factory):
    out = tmp_path_factory.mktemp('plot_output')
    run_plot(
        analyse_csv,
        None,
        out,
        sections=['distributions', 'qc', 'scatter', 'correlations'],
        all_sections=False,
        overwrite=False,
    )
    return out / 'evaluator' / 'plot'

# ====================
# Define tests
# ====================
class TestPlotDistributionsQC:
    def test_distributions_summary_stats_written(self, plot_output):
        path = plot_output / 'distributions' / 'summary_stats.xlsx'
        assert path.exists()
        wb = load_workbook(path)
        assert wb.active.max_row > 1  # header + at least one feature row

    def test_qc_summary_written(self, plot_output):
        path = plot_output / 'qc' / 'qc_summary.xlsx'
        assert path.exists()
        wb = load_workbook(path)
        row = list(wb.active.iter_rows(min_row=2, max_row=2, values_only=True))[0]
        assert row[0] == 'tomo1.mrc'  # tomogram column

    def test_histogram_svg_written_per_feature(self, plot_output):
        assert (plot_output / 'distributions' / 'equiv_diameter_nm_histogram.svg').exists()

    def test_index_md_lists_both_sections(self, plot_output):
        index = (plot_output / 'index.md').read_text()
        assert 'distributions/' in index and 'qc/' in index

    def test_sphere_rmse_rel_reported(self, plot_output):
        assert (plot_output / 'distributions' / 'sphere_rmse_rel_histogram.svg').exists()

    def test_debris_excluded_by_default(self, plot_output):
        wb = load_workbook(plot_output / 'qc' / 'qc_summary.xlsx')
        assert list(wb.active.iter_rows(min_row=2, max_row=2, values_only=True))[0][1] == 11  # 12 rows, 1 flagged

    def test_scatter_and_correlations_written(self, plot_output):
        assert (plot_output / 'scatter' / 'equiv_diameter_nm_vs_lumen_volume.svg').exists()
        assert (plot_output / 'correlations' / 'correlation_spearman.svg').exists()

class TestPlotMultiRun:
    def test_all_samples_reflected_in_per_sample_output(self, tmp_path):
        csv_a, csv_b = tmp_path / 'a.csv', tmp_path / 'b.csv'
        _write_analyse_csv(csv_a, tomogram='a.mrc')
        _write_analyse_csv(csv_b, tomogram='b.mrc')
        sheet = tmp_path / 'samples.tsv'
        sheet.write_text(f'sample_id\tpath\nsample_a\t{csv_a}\nsample_b\t{csv_b}\n')
        out = tmp_path / 'out'
        run_plot(sheet, None, out, sections=['distributions'], all_sections=False, overwrite=False)
        section_dir = out / 'evaluator' / 'plot' / 'distributions'
        for sample_id in ('sample_a', 'sample_b'):
            assert (section_dir / sample_id / 'summary_stats.xlsx').exists()
            assert (section_dir / sample_id / 'equiv_diameter_nm_histogram.svg').exists()

    def test_include_flagged_keeps_debris(self, tmp_path):
        csv_a = tmp_path / 'a.csv'
        _write_analyse_csv(csv_a)
        out = tmp_path / 'out'
        run_plot(csv_a, None, out, sections=['qc'], all_sections=False, overwrite=False, include_flagged=True)
        wb = load_workbook(out / 'evaluator' / 'plot' / 'qc' / 'qc_summary.xlsx')
        assert list(wb.active.iter_rows(min_row=2, max_row=2, values_only=True))[0][1] == 12

class TestPlotConcordance:
    def test_concordance_requires_matching_rows(self, tmp_path, analyse_csv):
        model_json = tmp_path / 'model.json'
        model_json.write_text(
            "{'results': [{'label_id': 999, 'source_file': 'no_such_tomo.mrc', "
            "'chosen_model': 'sphere', 'radius': 40.0, 'rmse_nm': 1.0, "
            "'reliability': {'is_reliable': true}}]}"
        )
        out = tmp_path / 'out'
        run_plot(analyse_csv, model_json, out, sections=['concordance'], all_sections=False, overwrite=False)
        section_dir = out / 'evaluator' / 'plot' / 'concordance'
        assert not (section_dir / 'concordance_stats.xlsx').exists()

    def test_concordance_and_reliability_with_matching_rows(self, tmp_path):
        csv_a = tmp_path / 'a.csv'
        _write_analyse_csv(csv_a, n=6)
        model = tmp_path / 'model.json'
        results = [
            {'label_id': i, 'source_file': 'tomo1.mrc', 'chosen_model': 'sphere', 'radius': (60 + i) / 2, 'rmse_nm': 1.0 + i,
            'reliability': {'is_reliable': bool(i % 2)}}
            for i in range(1, 6)
        ]
        model.write_text(__import__('json').dumps({'results': results, 'parameters': {}}))
        out = tmp_path / 'out'
        run_plot(csv_a, model, out, sections=['concordance', 'reliability'], all_sections=False, overwrite=False)
        base = out / 'evaluator' / 'plot'
        assert (base / 'concordance' / 'model_vs_equiv_diameter_nm.svg').exists()
        assert (base / 'concordance' / 'concordance_stats.xlsx').exists()
        assert (base / 'reliability' / 'reliability.svg').exists()

    def test_agreement_plots_requested_pairs(self, tmp_path):
        csv_a = tmp_path / 'a.csv'
        _write_analyse_csv(csv_a, n=6)
        model = tmp_path / 'model.json'
        results = [
            {'label_id': i, 'source_file': 'tomo1.mrc', 'chosen_model': 'sphere', 'radius': (60 + i) / 2 + 0.3 * i, 'rmse_nm': 1.0,
            'reliability': {'is_reliable': True}}
            for i in range(1, 6)
        ]
        model.write_text(__import__('json').dumps({'results': results, 'parameters': {}}))
        out = tmp_path / 'out'
        run_plot(
            csv_a, model, out, sections=['qc'], all_sections=False, overwrite=False,
            agreement=[('equiv_diameter_nm', 'model_diameter_nm'), ('major_axis_diameter', 'model_diameter_nm')],
        )
        base = out / 'evaluator' / 'plot' / 'agreement'
        assert (base / 'equiv_diameter_nm_vs_model_diameter_nm.svg').exists()
        assert (base / 'major_axis_diameter_vs_model_diameter_nm.svg').exists()
        assert (base / 'agreement_stats.xlsx').exists()

class TestPlotCompare:
    def test_compare_writes_group_outputs(self, tmp_path):
        a, b = tmp_path / 'a.csv', tmp_path / 'b.csv'
        _write_analyse_csv(a, tomogram='a.mrc')
        _write_analyse_csv(b, tomogram='b.mrc')
        sheet = tmp_path / 'samples.tsv'
        sheet.write_text(f'sample_id\tpath\tgroup\ns1\t{a}\tcontrol\ns2\t{b}\ttreated\n')
        out = tmp_path / 'out'
        run_plot(sheet, None, out, sections=['compare'], all_sections=False, overwrite=False)
        base = out / 'evaluator' / 'plot' / 'compare'
        assert (base / 'violin_equiv_diameter_nm.svg').exists()
        assert (base / 'pca.svg').exists()
        assert (base / 'group_summary.xlsx').exists()
