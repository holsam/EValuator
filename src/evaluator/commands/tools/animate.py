'''
=======================================
EValuator: ANIMATION/VISUALISATION UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import typer

# ====================
# Initialise typer as evaluatorAnimate
# ====================
evaluatorAnimate = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
)

# ====================
# Define command: animate
# ====================
@evaluatorAnimate.command('model')
def animate_model():
    '''
    Create an animation of the geometric principles underlying the model command. [bold yellow]\\[NOT IMPLEMENTED][/]
    '''
    print('\nevaluator tools animate model: not implemented.\n')
    