'''
=======================================
EValuator: OUTPUT PATH UTILITIES
=======================================
Functions for constructing and validating output directory structures
and generating unique output file names.
'''

# ====================
# Import external dependencies
# ====================
from pathlib import Path
from typing import Optional

# =========================
# DEFINE FUNCTION: generate_command_output_dir
# =========================
def generate_command_output_dir(evaluator_dir: Path, command: str) -> Path:
    out_dir = evaluator_dir / command
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

# =========================
# DEFINE FUNCTION: checkUniqueFileName
# =========================
def checkUniqueFileName(
    out_dir: Path,
    command: str,
    orig_name: Optional[str] = "",
    overlay_style: Optional[str] = "",
    fmt: Optional[str] = "",
    vis_out: Optional[str] = "",
) -> Path:
    '''
    Build a unique output file path for a given command, incrementing a counter
    suffix if a file with the same name already exists.

    Naming patterns by command:
        analyse  → evaluator-analyse_results.csv
        label    → <orig_name>_overlay-<overlay_style>.<fmt>
        overlay  → <orig_name>_overlay-<overlay_style>.<fmt>
        visualise→ <orig_name>_<vis_out>.<fmt>
    '''
    naming_patterns = {
        "analyse": "evaluator-analyse_results",
        "label": ''.join([orig_name, "_overlay-", overlay_style]),
        "overlay": ''.join([orig_name, "_overlay-", overlay_style]),
        "visualise": ''.join([orig_name, "_", vis_out]),
    }
    out_fmt = {
        "analyse": ".csv",
        "label": ''.join([".", fmt]),
        "overlay": ''.join([".", fmt]),
        "visualise": ''.join([".", fmt]),
    }
    out_filepath = Path(out_dir, ''.join([naming_patterns[command], out_fmt[command]]))
    if out_filepath.exists():
        file_counter = 1
        while True:
            out_filepath = Path(out_dir, ''.join([naming_patterns[command], "-", str(file_counter), out_fmt[command]]))
            if out_filepath.exists():
                file_counter += 1
            else:
                break
    return out_filepath