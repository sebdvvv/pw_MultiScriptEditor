"""
Gaffer GUI startup script — register Multi Script Editor as a native Editor panel.

See the project root ``readme_gaffer.md`` for full install instructions.
"""

import os
import sys

import GafferUI
import IECore


def _ensurePackageOnPath():
    """Find the folder that *contains* multi_script_editor and put it on sys.path."""
    try:
        import multi_script_editor  # noqa: F401
        return
    except ImportError:
        pass

    candidates = []

    gafferRoot = os.environ.get('GAFFER_ROOT')
    if gafferRoot:
        py = os.path.join(gafferRoot, 'python')
        candidates.append(py)
        candidates.append(os.path.join(py, 'pw_MultiScriptEditor'))

    here = os.path.abspath(os.path.dirname(__file__))
    probe = here
    for _ in range(8):
        candidates.append(probe)
        candidates.append(os.path.join(probe, 'python'))
        candidates.append(os.path.join(probe, 'python', 'pw_MultiScriptEditor'))
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent

    seen = set()
    for folder in candidates:
        folder = os.path.normpath(folder)
        if folder in seen or not os.path.isdir(folder):
            continue
        seen.add(folder)
        pkg = os.path.join(folder, 'multi_script_editor')
        if os.path.isfile(os.path.join(pkg, '__init__.py')):
            if folder not in sys.path:
                sys.path.insert(0, folder)
            return

    raise ImportError(
        'Could not find package multi_script_editor. '
        'Install it as <GAFFER_ROOT>/python/multi_script_editor/ '
        'or <GAFFER_ROOT>/python/pw_MultiScriptEditor/multi_script_editor/'
    )


_ensurePackageOnPath()

import multi_script_editor.managers._gaffer as _mseGaffer


_mseGaffer.registerWithApplication(application)


def __showMultiScriptEditor(menu):
    scriptWindow = menu.ancestor(GafferUI.ScriptWindow)
    if scriptWindow is None:
        return
    layout = scriptWindow.getLayout()
    try:
        layout.addEditor(_mseGaffer.EDITOR_TYPE_NAME)
    except Exception:
        _mseGaffer.show(scriptWindow.scriptNode())


GafferUI.ScriptWindow.menuDefinition(application).append(
    '/Window/Multi Script Editor',
    {'command': __showMultiScriptEditor},
)

IECore.msg(
    IECore.Msg.Level.Info,
    'Multi Script Editor',
    'Registered native Editor panel "Multi Script Editor".',
)
