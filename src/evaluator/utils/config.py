'''
=======================================
EValuator: CONFIGURATION UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
from dataclasses import dataclass
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

# ====================
# Define configuration classes
# ====================
class _Section(BaseModel):
    model_config = ConfigDict(extra='forbid')   # raise error on additional keys (or if misstyped)


class LogConfig(_Section):
    '''Global configuration parameters for logging'''
    verbose: bool = Field(..., description='Run EValuator with increased verbosity')
    debug: bool = Field(..., description='Run EValuator with debug messages (implies verbose)')


class LabelConfig(_Section):
    '''Configuration parameters for `evaluator label` command'''
    minimum_diameter: float = Field(..., description='Minimum component diameter (nm)')
    maximum_diameter: float = Field(..., description='Maximum component diameter (nm)')
    fill_threshold: float = Field(..., description='Fill ratio threshold for labelling')
    membrane_thickness_nm: float = Field(..., description='Membrane thickness (nm)')


class AnalyseConfig(_Section):
    '''Configuration parameters for `evaluator analyse` command'''
    pass


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


class Config(_Section):
    '''Overall EValuator configuration'''
    log: LogConfig
    label: LabelConfig
    analyse: AnalyseConfig
    visualise: VisualiseConfig


@dataclass(frozen=True)
class ResolvedConfig:
    evaluator_dir: Path
    config_path: Path
    existed: bool

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
