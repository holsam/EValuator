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
from evaluator.utils.settings import lg
from evaluator.commands.plot.utils.input import resolve_plot_inputs, available_sections, PlotRun
from evaluator.commands.plot.utils.dispatch import resolve_rscript, dispatch, RscriptError

# ====================
# Define R scripts for each section
# ====================
SECTION_SCRIPTS = {
    'distributions': 'distributions.R',
    'qc': 'qc.R',
    'scatter': 'scatter.R',
    'concordance': 'concordance.R',
    'compare': 'compare.R',
}

# ====================
# run_plot: orchestration logic for plot command
# ====================
def run_plot(analyse_input, model_input, output, sections, all_sections, overwrite, rscript):
    config, evaluator_dir = confutil.load_config(output)
    params = config.plot
    runs, multi_run, sheet_path = resolve_plot_inputs(analyse_input, model_input)
    runnable = available_sections(runs, multi_run)
    requested = runnable if all_sections else (sections or params.default_sections)
    to_run = [s for s in requested if s in runnable]
    skipped = set(requested) - set(to_run)
    if skipped:
        lg.warning(f'plot | Section(s) not runnable with the given input and will be skipped: {sorted(skipped)}')
    if not to_run:
        lg.error('plot | No runnable sections for the given input.')
        return
    rscript_bin = resolve_rscript(rscript)
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
            _run_section(section, runs, multi_run, section_dir, rscript_bin, params, sheet_path)
            completed.append(section)
        except RscriptError as e:
            lg.warning('plot | Section {} failed: {}', section, e)
    _write_index(out_dir, completed)
    lg.info(f'plot | Finished. Sections completed: {completed}')

# ====================
# _run_section: orchestration logic for each section
# ====================
def _run_section(section: str, runs, multi_run: bool, section_dir: Path, rscript_bin: Path, params, sheet_path: Path | None = None) -> None:
    mode = 'multi' if multi_run else 'single'
    script = SECTION_SCRIPTS[section]
    if section == 'concordance':
        run = runs[0]
        dispatch(rscript_bin, script, [section_dir, run.analyse_path, run.model_path, mode])
    elif section == 'qc':
        run = runs[0]
        dispatch(rscript_bin, script, [section_dir, run.analyse_path, mode, params.fill_ratio_flag_threshold])
    elif section in ('distributions', 'scatter'):
        run = runs[0]
        dispatch(rscript_bin, script, [section_dir, run.analyse_path, mode])
    elif section == 'compare':
        dispatch(rscript_bin, script, [section_dir, sheet_path, mode])

# ====================
# _write_index: write the markdown index of all generated files
# ====================
def _write_index(out_dir: Path, sections: list[str]) -> None:
    lines = ['# EValuator plot results', '']
    for s in sections:
        lines.append(f'- [`{s}/`]({s}/)')
    (out_dir / 'index.md').write_text('\n'.join(lines) + '\n')