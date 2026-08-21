'''
=======================================
EValuator: PLOT COMMAND INPUT RESOLUTION
=======================================
'''

# ====================
# Import external dependencies
# ====================
import csv
from dataclasses import dataclass
from pathlib import Path

# ====================
# Import internal EValuator utilities
# ====================
from evaluator.utils.settings import lg

# ====================
# Define constant variables
# ====================
# Required column in sheet for plotting
REQUIRED_SHEET_COLUMNS = {'sample_id'}

# ====================
# Define dataclass for a run of Plot
# ====================
@dataclass(frozen=True)
class PlotRun:
    sample_id: str
    analyse_path: Path | None
    model_path: Path | None
    group: str | None = None
    replicate: int | None = None

# ====================
# Define functions for parsing plot input
# ====================
def _is_sample_sheet(path: Path) -> bool:
    '''A sample sheet is any TSV/TXT file (headers validated on read)'''
    return path.suffix.lower() in {".tsv", ".txt"}

def resolve_plot_inputs(analyse_input: Path | None, model_input: Path | None) -> tuple[list[PlotRun], bool, Path | None]:
    '''
    Resolve --analyse/--model into a list of PlotRun entries, whether this is multi-run mode (sample sheet supplied on either side), and the sheet path used (if any)
    '''
    analyse_sheet = analyse_input is not None and _is_sample_sheet(analyse_input)
    model_sheet = model_input is not None and _is_sample_sheet(model_input)
    if not analyse_sheet and not model_sheet:
        run = PlotRun(sample_id="sample", analyse_path=analyse_input, model_path=model_input)
        return [run], False, None
    sheet_path = analyse_input if analyse_sheet else model_input
    analyse_rows = _read_sheet(analyse_input) if analyse_sheet else {}
    model_rows = _read_sheet(model_input) if model_sheet else {}
    sample_ids = set(analyse_rows) | set(model_rows)
    runs = []
    for sid in sorted(sample_ids):
        a_row = analyse_rows.get(sid, {})
        m_row = model_rows.get(sid, {})
        runs.append(PlotRun(
            sample_id=sid,
            analyse_path=Path(a_row["path"]).expanduser() if a_row.get("path") else (analyse_input if not analyse_sheet else None),
            model_path=Path(m_row["path"]).expanduser() if m_row.get("path") else (model_input if not model_sheet else None),
            group=a_row.get("group") or m_row.get("group"),
            replicate=int(a_row["replicate"]) if a_row.get("replicate") else (int(m_row["replicate"]) if m_row.get("replicate") else None),
        ))
    return runs, True, sheet_path

def _read_sheet(path: Path) -> dict[str, dict]:
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if not REQUIRED_SHEET_COLUMNS.issubset(reader.fieldnames or []):
            raise ValueError(f'{path.name}: sample sheet missing required column(s) {REQUIRED_SHEET_COLUMNS}')
        rows = {row["sample_id"]: row for row in reader}
    lg.debug(f'plot | Loaded {len(rows)} row(s) from sample sheet {path.name}')
    return rows

def available_sections(runs: list[PlotRun], multi_run: bool) -> list[str]:
    '''Determine which sections are runnable given what input was actually supplied'''
    has_analyse = any(r.analyse_path for r in runs)
    has_model = any(r.model_path for r in runs)
    sections = []
    if has_analyse:
        sections += ['distributions', 'qc', 'scatter']
    if has_analyse and has_model:
        sections.append("concordance")
    if multi_run and len({r.group for r in runs if r.group} ) > 1:
        sections.append('compare')
    return sections
