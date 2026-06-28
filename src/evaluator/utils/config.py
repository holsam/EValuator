'''
=======================================
EValuator: CONFIGURATION UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
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
