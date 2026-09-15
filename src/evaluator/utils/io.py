'''
=======================================
EValuator: INPUT & OUTPUT FUNCTIONS
=======================================
Functions for reading and writing EValuator input/output files.
'''

# ====================
# Import external dependencies
# ====================
import csv, json, tomllib, tomli_w
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

# ====================
# Define variables
# ====================
# OutputFormat: define available output formats
OutputFormat = Literal['csv', 'json']

# ====================
# Define dataclasses
# ====================
# WriteResult: dataclass containing paths of files which were written
@dataclass
class WriteResult:
    primary_path: Path
    params_path: Path | None   # None if format is 'json' as included inline

# ====================
# Define helper functions
# ====================
# _write_json: write a list of dictionaries and a dictionary of parameters to a JSON file at output_path
def _write_json(
    results: list[dict[str, Any]],
    parameters: dict[str, Any],
    output_path: Path,
) -> WriteResult:
    payload = {'parameters': parameters, 'results': results}
    path = output_path.with_suffix('.json')
    path.write_text(json.dumps(payload, indent=2, default=_json_default))
    return WriteResult(primary_path=path, params_path=None)

# _write_csv_and_toml: write a list of dictionaries to a CSV file at output_path, and a dictionary of parameters to a TOML file in the same directory
def _write_csv_and_toml(
    results: list[dict[str, Any]],
    parameters: dict[str, Any], 
    output_path: Path,
) -> WriteResult:
    csv_path = output_path.with_suffix('.csv')
    toml_path = output_path.parent / 'params.toml'
    # Flatten results so suitable for CSV format
    flat_results = [_flatten_record(r) for r in results]
    fieldnames = _union_fieldnames(flat_results)
    # Write CSV file for results
    with csv_path.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_results)
    # Write TOML file for parameters
    toml_path.write_bytes(tomli_w.dumps(parameters).encode())
    return WriteResult(primary_path=csv_path, params_path=toml_path)

# _flatten_record: flattens a single result dictionary to a CSV, encoding nested structures as JSON
def _flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, (dict, list, tuple)):
            flat[key] = json.dumps(value, default=_json_default)
        elif hasattr(value, 'tolist'):   # numpy arrays
            flat[key] = json.dumps(value.tolist())
        else:
            flat[key] = value
    return flat

# _union_fieldnames: find shared keys in a list of dictionaries
def _union_fieldnames(flat_records: list[dict[str, Any]]) -> list[str]:
    seen: dict[str, None] = {}
    for record in flat_records:
        for key in record:
            seen[key] = None
    return list(seen)

# _json_default: serialise an object to a list for JSON formatting
def _json_default(obj: Any) -> Any:
    if hasattr(obj, 'tolist'):
        return obj.tolist()
    raise TypeError(f'Object of type {type(obj)} is not JSON serialisable')

# _unflatten_record: given a dictionary containing row-column values (i.e. from CSV), create a dictionary
def _unflatten_record(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        try:
            out[key] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            out[key] = value
    return out

# ====================
# Define functions
# ====================
# write_results: write a list of per-record result dictionaries and parameters used
def write_results(
    records: list[dict[str, Any]],
    parameters: dict[str, Any],
    output_path: Path,
    output_format: OutputFormat,
) -> WriteResult:
    output_path = output_path.with_suffix('')
    if output_format == 'json':
        return _write_json(records, parameters, output_path)
    elif output_format == 'csv':
        return _write_csv_and_toml(records, parameters, output_path)
    raise ValueError(f'Unsupported output format: {output_format!r}')

# read_results: read a JSON/CSV+TOML file into a list of result dictionaries
def read_results(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if path.suffix == '.json':
        payload = json.loads(path.read_text())
        return payload['results'], payload['parameters']
    elif path.suffix == '.csv':
        with path.open() as fh:
            reader = csv.DictReader(fh)
            records = [_unflatten_record(row) for row in reader]
        toml_path = path.parent / 'params.toml'
        parameters = tomllib.loads(toml_path.read_text()) if toml_path.exists() else {}
        return records, parameters
    raise ValueError(f'Unrecognised results file suffix: {path.suffix}')