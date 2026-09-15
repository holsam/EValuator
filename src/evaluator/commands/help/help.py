'''
=======================================
EValuator: VIEW DOCUMENTATION
=======================================
'''

# ====================
# Import external dependencies
# ====================
from importlib.resources import files as pkg_files
from textual.app import App, ComposeResult
from textual.widgets import Footer, Markdown, TabbedContent, TabPane

# ====================
# Define constants
# ====================
# _DOC_FILES: path to all documentation files, relative to this file
_DOC_FILES: list[tuple[str, str]] = [
    ('README', '../../README.md'),
    ('analyse', '../../docs/analyse.md'),
    ('config', '../../docs/config.md'),
    ('label', '../../docs/label.md'),
    ('model', '../../docs/model.md'),
    ('plot', '../../docs/plot.md'),
    ('tools', '../../docs/tools.md'),
    ('viewer', '../../docs/viewer.md'),
    ('visualise', '../../docs/visualise.md'),
]

# ====================
# Define functions
# ====================
# _readDoc: read a doc file
def _readDoc(relPath: str) -> str:
    with pkg_files('evaluator').joinpath(relPath).open('r') as f:
        return f.read()

# showHelp: entry point
def showHelp() -> None:
    HelpApp().run()
    raise SystemExit(0)

# ====================
# Define functions
# ====================
# HelpApp: Textual app showing each doc as a scrollable tab
class HelpApp(App):
    BINDINGS = [('q', 'quit', 'Quit'), ('escape', 'quit', 'Quit')]

    def compose(self) -> ComposeResult:
        with TabbedContent():
            for title, relPath in _DOC_FILES:
                with TabPane(title, id=title.lower()):
                    yield Markdown(_readDoc(relPath))
        yield Footer()
