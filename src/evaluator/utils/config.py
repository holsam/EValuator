'''
=======================================
EValuator: CONFIGURATION UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import tomlkit, tomllib
from dataclasses import dataclass
from importlib.resources import files 
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal

# ====================
# Define configuration classes
# ====================
class _Section(BaseModel):
    model_config = ConfigDict(extra='forbid')   # raise error on additional keys (or if misstyped)


class LogConfig(_Section):
    '''Global configuration parameters for logging'''
    verbose: bool = Field(..., description='Run EValuator with increased verbosity')
    debug: bool = Field(..., description='Run EValuator with debug messages (implies verbose)')


class OutputConfig(_Section):
    '''Global configuration parameters for output files'''
    format: Literal['csv', 'json'] = 'json'


class LabelConfig(_Section):
    '''Configuration parameters for `evaluator label` command'''
    min_arc_coverage: float = Field(0.40, description='Minimum fraction of expected spherical surface a component must cover to be retained', gt=0, le=1)
    merge_centre_tol_factor: float = Field(1.5, description='Centroids within centre_tol_factor * (r_a + r_b) are merge candidates')
    merge_radius_tol_pct: float = Field(0.30, description='Maximum relative difference between two components\' estimated radii to be merge candidates', gt=0)
    minimum_diameter_nm: float = Field(..., description='Minimum component diameter (nm)')
    maximum_diameter_nm: float = Field(..., description='Maximum component diameter (nm)')
    membrane_thickness_nm: float = Field(..., description='Membrane thickness (nm)')
    max_workers: int | None = Field(None, description='Maximum parallel worker processes for batch input (default: CPU count)')


class ModelConfig(_Section):
    '''Configuration parameters for `evaluator model` command'''
    rmse_relative_max: float = Field(0.15, description='Maximum relative RMSE for reliability check')
    min_points: int = Field(20, description='Minimum surface points for a reliable fit')
    max_workers: int | None = Field(None, description='Maximum parallel worker processes for batch input (default: CPU count)')

class AnalyseConfig(_Section):
    '''Configuration parameters for `evaluator analyse` command'''
    fill_threshold: float = Field(..., description='Fill ratio threshold for labelling')
    max_workers: int | None = Field(None, description='Maximum parallel worker processes for batch input (default: CPU count)')

class PlotConfig(_Section):
    '''Configuration parameters for `evaluator plot` command'''
    default_sections: list[Literal['distributions', 'qc', 'scatter', 'concordance', 'compare']] = Field(
        default_factory=lambda: ['distributions', 'qc', 'scatter'], description='Sections run when --section/--all are not given',
    )
    fill_ratio_flag_threshold: float = Field(0.05, description='closure_fill_ratio below this is flagged in qc plots')

class VisualiseConfig(_Section):
    '''Configuration parameters for `evaluator visualise` command'''
    overlay_style: str = Field(..., description='Style of overlay to use (both, filled, contours)')
    n_slices: int = Field(..., description='Default number of slices in tiled panel outputs')
    fps: int = Field(..., description='Frames per second to use to use for visualise outputs')
    downsample: int = Field(..., description='Downsampling rate to use for visualise outputs')
    colourmap: str = Field(..., description='Matplotlib colourmap used to assign colours to components')
    alpha_fill: float = Field(..., description='Opacity of filled overlay regions (0-1)')
    contour_linewidth: float = Field(..., description='Line width for contour overlays (px)')
    label_fontsize: int = Field(..., description='Font size for component text annotations')
    figure_dpi: int = Field(..., description='Output image resolution (dpi)')
    max_workers: int | None = Field(None, description='Maximum parallel worker processes for batch input (default: CPU count)')


class Config(_Section):
    '''Overall EValuator configuration'''
    log: LogConfig
    output: OutputConfig = OutputConfig()
    label: LabelConfig = LabelConfig()
    model: ModelConfig = ModelConfig()
    analyse: AnalyseConfig
    plot: PlotConfig = PlotConfig()
    visualise: VisualiseConfig


@dataclass(frozen=True)
class ResolvedConfig:
    evaluator_dir: Path
    config_path: Path
    existed: bool


class ConfigError(Exception):
    '''Base class for EValuator configuration errors'''


class ConfigNotFoundError(ConfigError):
    '''Raised when an EValuator config is required but absent and autocreate is disabled'''

# ====================
# Define configuration utility helper functions
# ====================
def _default_text() -> str:
    package, name = ('evaluator', 'config.toml')
    return (files(package) / name).read_text(encoding='utf-8')

# ====================
# Define configuration utility functions
# ====================
def resolve_config(path: Path) -> ResolvedConfig:
    '''Resolve a given path to a configuration file location, based on precedence described within'''
    path = Path(path).expanduser().resolve()
    # 1: if path is to a file
    if path.is_file():
        return ResolvedConfig(evaluator_dir=path.parent, config_path=path, existed=True)
    if path.is_dir():
        # 2: if path is to evaluator directory containing config.toml
        if Path(path, 'config.toml').exists():
            return ResolvedConfig(evaluator_dir=path, config_path=Path(path, 'config.toml'), existed=True)
        # 3: if path is to a directory containing evaluator/config.toml
        if Path(path, 'evaluator/config.toml').exists():
            return ResolvedConfig(evaluator_dir=Path(path, 'evaluator'), config_path=Path(path, 'evaluator/config.toml'), existed=True)
    # 4: if path contains .toml suffix, create config path
    if path.suffix == '.toml':
        return ResolvedConfig(evaluator_dir=path.parent, config_path=path, existed=False)
    # 5: if path is to non-existent directory or a directory without evaluator/config.toml, create evaluator/config.toml
    return ResolvedConfig(evaluator_dir=Path(path, 'evaluator'), config_path=Path(path, 'evaluator/config.toml'), existed=False)

def create_default_config(target: Path) -> None:
    '''Create target (and parents) from default configuration file'''
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_default_text(), encoding='utf-8')

def read_config(config_path: Path) -> Config:
    '''Read and validate a config file'''
    try:
        data = tomllib.loads(config_path.read_text(encoding='utf-8'))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f'{config_path} is not valid TOML: {e}') from e
    try:
        return Config.model_validate(data)
    except ValidationError as e:
        raise ConfigError(f'{config_path} failed validation: {e}') from e

def load_config(output: Path, *, autocreate: bool = True) -> tuple[Config, Path]:
    '''Resolve, optionally create, then load the config for a pipeline run'''
    resolved = resolve_config(output)
    if not resolved.existed:
        if not autocreate:
            raise ConfigNotFoundError(f'No config found for {output} (expected {resolved.config_path})')
        create_default_config(resolved.config_path)
    config = read_config(resolved.config_path)
    return config, resolved.evaluator_dir

def write_params(params: BaseModel, out_dir: Path, filename: str = 'params.toml') -> Path:
    '''Write the effective parameters used for a run to out_dir'''
    out_dir.mkdir(parents=True, exist_ok=True)
    data = params.model_dump(mode='json', exclude_none=True)
    path = out_dir / filename
    path.write_text(tomlkit.dumps(data), encoding='utf-8')
    return path