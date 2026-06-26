'''
=======================================
EValuator: IO ANALYSIS UTILITIES
=======================================
'''
# ====================
# Import external dependencies
# ====================
import datetime, pandas
from pathlib import Path
from rich import print

# ====================
# Import shared EValuator utilities
# ====================
from evaluator.utils.settings import lg

# =========================
# DEFINE FUNCTION: saveResultsCSV
# =========================
def saveResultsCSV(analyse_results, out_path: Path):
    '''
    Convert list of result dictionaries to a pandas DataFrame and save to CSV.
    '''
    analyse_df = pandas.DataFrame(analyse_results)
    analyse_df.to_csv(out_path, index=False)
    lg.info(f"Analyse results saved to: {out_path}")
    return analyse_df

# =========================
# DEFINE FUNCTION: printSummaryMessage
# =========================
def printSummaryMessage(results, nfiles: int, startt: datetime.datetime, endt: datetime.datetime, out_path: Path):
    RUNTIME = endt - startt
    print(f"\n[bold]Pipeline run summary[/bold]")
    print(f"- Runtime: {RUNTIME}")
    print(f"- Segmentation files processed: {nfiles}")
    print(f"- Segmentation files with EVs: {results['tomogram'].nunique()} ({(100 * results['tomogram'].nunique()) / nfiles:.1f}%)")
    print(f"- EVs processed: {len(results)}")
    print(f"- Number of enclosed EVs: {results['is_enclosed'].sum()} ({100 * results['is_enclosed'].mean():.1f}%)")
    print(f"- Equivalent diameters: {results['equiv_diameter_nm'].mean():.1f} ± {results['equiv_diameter_nm'].std():.1f} nm (mean ± SD)")
    print(f"Results saved to: {out_path}\n")