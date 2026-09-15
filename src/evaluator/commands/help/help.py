'''
=======================================
EValuator: VIEW DOCUMENTATION
=======================================
'''

# ====================
# Import external dependencies
# ====================
import re
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

# _BADGE_LINE: shields.io badge lines at the top of README
_BADGE_LINE = re.compile(r'^!?\[!\[.*$|^!\[.*\]\[.*\]$', re.MULTILINE)
# _DIV_WRAPPER: div wrapper lines
_DIV_WRAPPER = re.compile(r'^</?div.*>$', re.MULTILINE)
_FOOTNOTE_DEF = re.compile(r'^\[\^(\w+)\]:\s*(.*)$', re.MULTILINE)
_FOOTNOTE_REF = re.compile(r'\[\^(\w+)\]')
_SUP_MARKER = re.compile(r'<sup>\*\*(\d+)\*\*</sup>')

# ====================
# Define functions
# ====================
# _numberFootnotes: markdown-it [^name] refs/defs -> plain numbered _(N)_ markers, numbered by reference order
def _numberFootnotes(text: str) -> str:
    if not _FOOTNOTE_DEF.search(text):
        return text
    order = {name: i + 1 for i, name in enumerate(dict.fromkeys(_FOOTNOTE_REF.findall(text)))}
    text = _FOOTNOTE_DEF.sub(lambda m: f'_({order[m.group(1)]})_ {m.group(2)}' if m.group(1) in order else '', text)
    return _FOOTNOTE_REF.sub(lambda m: f' _({order[m.group(1)]})_', text)

# _numberSupMarkers: docs/model.md uses <sup>**N**</sup> for both the inline ref and the
# line-leading definition (e.g. "<sup>**4**</sup> `reliability` contains: ...") -> the same _(N)_ style
def _numberSupMarkers(text: str) -> str:
    return _SUP_MARKER.sub(lambda m: f'_({m.group(1)})_', text)

# _readDoc: read a doc file
def _readDoc(relPath: str) -> str:
    with pkg_files('evaluator').joinpath(relPath).open('r') as f:
        text = f.read()
    if relPath.endswith('README.md'):
        text = _BADGE_LINE.sub('', text)
        text = _DIV_WRAPPER.sub('', text)
        text = text.lstrip('\n')
    return _numberSupMarkers(_numberFootnotes(text))

# showHelp: entry point
def showHelp(topic: str | None = None) -> None:
    HelpApp(topic).run()
    print()
    raise SystemExit(0)

# ====================
# Define functions
# ====================
# HelpApp: Textual app showing each doc as a scrollable tab
class HelpApp(App):
    BINDINGS = [('q', 'quit', 'Quit'), ('escape', 'quit', 'Quit')]

    def __init__(self, topic: str | None = None) -> None:
        super().__init__()
        self._initialTopic = topic

    def compose(self) -> ComposeResult:
        validIds = {title.lower() for title, _ in _DOC_FILES}
        initial = self._initialTopic if self._initialTopic in validIds else None
        with TabbedContent(initial=initial):
            for title, relPath in _DOC_FILES:
                with TabPane(title, id=title.lower()):
                    yield Markdown(_readDoc(relPath), open_links=False)
        yield Footer()

    def on_mount(self) -> None:
        validIds = {title.lower() for title, _ in _DOC_FILES}
        if self._initialTopic is not None and self._initialTopic not in validIds:
            self.notify(f'No help page for {self._initialTopic!r}, showing README', severity='warning')

    def action_focus_next(self) -> None:
        self._cycleTab(1)

    def action_focus_previous(self) -> None:
        self._cycleTab(-1)

    def _cycleTab(self, step: int) -> None:
        tabs = self.query_one(TabbedContent)
        ids = [title.lower() for title, _ in _DOC_FILES]
        nextIndex = (ids.index(tabs.active) + step) % len(ids)
        tabs.active = ids[nextIndex]

    # on_markdown_link_clicked: intercept README/doc cross-links so they switch tabs instead of opening a browser
    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        stem = event.href.split('/')[-1].removesuffix('.md').lower()
        validIds = {title.lower() for title, _ in _DOC_FILES}
        if stem in validIds:
            self.query_one(TabbedContent).active = stem
        else:
            self.app.open_url(event.href)