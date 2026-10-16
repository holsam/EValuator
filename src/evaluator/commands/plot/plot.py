'''
=======================================
EValuator: EV MORPHOLOGY FEATURES PLOTTING
=======================================
'''

# ====================
# Import external dependencies
# ====================
from pathlib import Path

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils import config as confutil
from evaluator.utils import paths as pathutil
from evaluator.utils.figures import plots as plotutil
from evaluator.utils.figures import theme as themeutil
from evaluator.utils.settings import lg
from evaluator.commands.plot import sections as sectionutil
from evaluator.commands.plot.utils import export as exportutil
from evaluator.commands.plot.utils.input import resolve_plot_inputs, available_sections, PlotRun

# ====================
# run_plot: orchestration logic for plot command
# ====================
def run_plot(analyse_input, model_input, output, sections, all_sections, overwrite, include_flagged=False, agreement=None):
    config, evaluator_dir = confutil.load_config(output)
    params = config.plot
    runs, multi_run, sheet_path = resolve_plot_inputs(analyse_input, model_input)
    runnable = available_sections(runs, multi_run)
    requested = runnable if all_sections else (sections or params.default_sections)
    if agreement and 'agreement' not in sections:
        requested.append('agreement')
    to_run = [s for s in requested if s in runnable]
    skipped = set(requested) - set(to_run)
    if skipped:
        lg.warning(f'plot | Section(s) not runnable with the given input and will be skipped: {sorted(skipped)}')
    if not to_run:
        lg.error('plot | No runnable sections for the given input.')
        return
    try:
        exportutil.check_kaleido()
    except RuntimeError as e:
        lg.error(str(e))
        return
    plotutil.use_theme(themeutil.resolve(params.theme))
    out_dir = pathutil.generate_command_output_dir(evaluator_dir, 'plot')
    confutil.write_params(params, out_dir)
    completed = []
    for section in to_run:
        section_dir = out_dir / section
        if section_dir.exists() and not overwrite:
            lg.warning(f'plot | {section_dir} already exists, skipping (use --overwrite to replace).')
            continue
        section_dir.mkdir(parents=True, exist_ok=True)
        try:
            _run_section(section, runs, multi_run, section_dir, params, include_flagged, agreement)
            completed.append(section)
        except Exception as e:
            lg.warning(f'plot | Section {section} failed: {e}')
    _write_index(out_dir, completed)
    lg.info(f'plot | Finished. Sections completed: {completed}')

# ====================
# _run_section: orchestration logic for each section
# ====================
def _run_section(section: str, runs: list[PlotRun], multi_run: bool, section_dir: Path, params, include_flagged: bool, agreement) -> None:
    if section == 'compare':
        sectionutil.compare(section_dir, runs, params, include_flagged=include_flagged)
        return
    # per-sample sections: in multi-run mode every sample is plotted into its own subdirectory
    for run in (runs if multi_run else runs[:1]):
        run_dir = section_dir / run.sample_id if multi_run else section_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        sectionutil.SECTIONS[section](run_dir, sectionutil.load(run, include_flagged=include_flagged, agreement=agreement), params)

# ====================
# _write_index: write the markdown index of all generated files
# ====================
def _write_index(out_dir: Path, sections: list[str]) -> None:
    lines = ['# EValuator plot results', '']
    for s in sections:
        lines.append(f'- [`{s}/`]({s}/)')
    (out_dir / 'index.md').write_text('\n'.join(lines) + '\n')
