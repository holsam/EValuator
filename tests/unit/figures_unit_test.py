'''
Unit tests for the shared figure package
'''

# ====================
# Import external dependencies
# ====================
import subprocess, sys

# ====================
# Import evaluator figure helpers
# ====================
from evaluator.utils.figures import theme as figtheme

# ====================
# Define tests
# ====================
class TestFigures:
    def test_plots_import_without_streamlit(self):
        code = "import sys; sys.modules['streamlit'] = None; import evaluator.utils.figures.plots"
        subprocess.run([sys.executable, '-c', code], check=True)

    def test_resolve_default_theme_has_ui_and_roles(self):
        theme = figtheme.resolve()
        assert set(figtheme.UI_KEYS) <= set(theme) and set(figtheme.ROLE_KEYS) <= set(theme)
        assert theme['paper_bg'] == '#FFFFFF'

    def test_resolve_named_theme(self):
        assert figtheme.resolve('Neon')['base'] == figtheme.THEMES['Neon']['base']
