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
# DEFINE FUNCTION: generateOutputFileStructure
# =========================
def generateOutputFileStructure(out_dir: Path, command: str) -> Path:
    '''
    Create and return the expected EValuator output directory structure for a given command.
    If the supplied out_dir does not already end in the expected structure
    (.../evaluator/results/<command>/), the structure is appended and created.
    '''
    exp_stru = ''.join(["evaluator/results/", command])
    if not out_dir.match(exp_stru):
        out_struc = Path(out_dir, exp_stru)
        out_struc.mkdir(parents=True, exist_ok=True)
        return out_struc
    else:
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