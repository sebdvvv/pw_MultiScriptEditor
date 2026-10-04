"""
Gaffer host integration: native dockable GafferUI.Editor wrapping Multi Script Editor.
Adapted for pw_MultiScriptEditor 6.8.x (create_editor_instance / updateNamespace).
"""
from __future__ import absolute_import

import re
import sys
import types
import warnings

import imath
import IECore
import Gaffer
import GafferUI

from Qt import QtCore
from Qt import QtWidgets
import Qt as _gafferQt


def _install_vendor_qt(vendor_qt):
    """Register vendor.Qt in sys.modules AND on the vendor package (for `vendor.Qt`)."""
    import importlib
    sys.modules['vendor.Qt'] = vendor_qt
    try:
        vendor_pkg = importlib.import_module('vendor')
        setattr(vendor_pkg, 'Qt', vendor_qt)
    except Exception:
        if 'vendor' in sys.modules:
            try:
                setattr(sys.modules['vendor'], 'Qt', vendor_qt)
            except Exception:
                pass


def _bootstrapVendorQt():
    """
    Build a vendor.Qt that combines:
    - real PySide6/PySide2 modules (full API: QLockFile, QKeySequenceEdit, ...)
    - Gaffer Qt.py compat remaps (QAction/QShortcut on QtWidgets, etc.)
    """
    import importlib

    def _binding_modules():
        try:
            import PySide6  # noqa: F401
            name = 'PySide6'
        except ImportError:
            try:
                import PySide2  # noqa: F401
                name = 'PySide2'
            except ImportError:
                return None, {}
        mods = {}
        for sub in (
            'QtCore', 'QtGui', 'QtWidgets', 'QtNetwork', 'QtXml',
            'QtTest', 'QtSvg', 'QtOpenGL', 'QtPrintSupport',
        ):
            try:
                mods[sub] = importlib.import_module('%s.%s' % (name, sub))
            except ImportError:
                pass
        # Alias PySide6 as PySide2 for leftover imports
        if name == 'PySide6':
            import PySide6
            sys.modules.setdefault('PySide2', PySide6)
            for sub, mod in mods.items():
                sys.modules.setdefault('PySide2.%s' % sub, mod)
        return name, mods

    _COMPAT_OVERLAY = {
        'QtWidgets': (
            'QAction', 'QShortcut', 'QActionGroup', 'QFileSystemModel',
            'QUndoCommand', 'QUndoGroup', 'QUndoStack',
        ),
    }

    def _merge_submodule(sub_name, real_mod, gaffer_mod):
        mod = types.ModuleType('vendor.Qt.%s' % sub_name)
        # 1) full real binding API
        if real_mod is not None:
            for key in dir(real_mod):
                if key.startswith('__'):
                    continue
                try:
                    setattr(mod, key, getattr(real_mod, key))
                except Exception:
                    pass
        # 2) fill gaps from Gaffer shim
        if gaffer_mod is not None:
            for key in dir(gaffer_mod):
                if key.startswith('__'):
                    continue
                if not hasattr(mod, key):
                    try:
                        setattr(mod, key, getattr(gaffer_mod, key))
                    except Exception:
                        pass
            # 3) force compat remaps from Gaffer even if real binding lacks them
            for key in _COMPAT_OVERLAY.get(sub_name, ()):
                if hasattr(gaffer_mod, key):
                    try:
                        setattr(mod, key, getattr(gaffer_mod, key))
                    except Exception:
                        pass
        return mod

    binding_name, real_mods = _binding_modules()
    if not real_mods:
        # Last resort: pure Gaffer Qt.py
        vendor_qt = types.ModuleType('vendor.Qt')
        vendor_qt.__name__ = 'vendor.Qt'
        vendor_qt.__package__ = 'vendor'
        for key in dir(_gafferQt):
            if key in ('__name__', '__package__', '__loader__', '__spec__', '__file__', '__cached__'):
                continue
            try:
                setattr(vendor_qt, key, getattr(_gafferQt, key))
            except Exception:
                pass
        for name in ('QtCore', 'QtGui', 'QtWidgets', 'QtNetwork', 'QtXml', 'QtTest', 'QtSvg', 'QtCompat'):
            if hasattr(_gafferQt, name):
                sub = getattr(_gafferQt, name)
                setattr(vendor_qt, name, sub)
                sys.modules['vendor.Qt.%s' % name] = sub
        _install_vendor_qt(vendor_qt)
        return

    vendor_qt = types.ModuleType('vendor.Qt')
    vendor_qt.__name__ = 'vendor.Qt'
    vendor_qt.__package__ = 'vendor'
    vendor_qt.__binding__ = binding_name or getattr(_gafferQt, '__binding__', 'PySide6')
    vendor_qt.__binding_version__ = getattr(_gafferQt, '__binding_version__', '')
    try:
        if not vendor_qt.__binding_version__:
            bmod = importlib.import_module(binding_name)
            vendor_qt.__binding_version__ = getattr(bmod, '__version__', '')
    except Exception:
        pass

    # Copy misc helpers from Gaffer Qt.py (QtCompat, etc.)
    for key in dir(_gafferQt):
        if key.startswith('__') or key.startswith('Qt'):
            continue
        try:
            setattr(vendor_qt, key, getattr(_gafferQt, key))
        except Exception:
            pass
    if hasattr(_gafferQt, 'QtCompat'):
        vendor_qt.QtCompat = _gafferQt.QtCompat
        sys.modules['vendor.Qt.QtCompat'] = _gafferQt.QtCompat

    for sub_name in (
        'QtCore', 'QtGui', 'QtWidgets', 'QtNetwork', 'QtXml',
        'QtTest', 'QtSvg', 'QtOpenGL', 'QtPrintSupport',
    ):
        gaffer_sub = getattr(_gafferQt, sub_name, None)
        real_sub = real_mods.get(sub_name)
        if real_sub is None and gaffer_sub is None:
            continue
        merged = _merge_submodule(sub_name, real_sub, gaffer_sub)
        setattr(vendor_qt, sub_name, merged)
        sys.modules['vendor.Qt.%s' % sub_name] = merged

    _install_vendor_qt(vendor_qt)

_bootstrapVendorQt()

EDITOR_TYPE_NAME = 'Multi Script Editor'


def _importScriptEditor():
    _bootstrapVendorQt()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', DeprecationWarning)
        from multi_script_editor import scriptEditor as se
    return se


def getMainWindow(scriptNode=None):
    """Return the ScriptWindow QWidget for scriptNode, or any visible main window."""
    if scriptNode is not None:
        try:
            return GafferUI.ScriptWindow.acquire(scriptNode)._qtWidget()
        except Exception:
            pass
    app = QtWidgets.QApplication.instance()
    if app:
        for w in app.topLevelWidgets():
            if w.isVisible() and w.inherits('QMainWindow'):
                return w
    return None


def show(scriptNode=None):
    """Add a Multi Script Editor tab to the layout for the given (or active) script."""
    if scriptNode is None:
        scriptNode = _activeScriptNode()
    if scriptNode is None:
        raise RuntimeError('No Gaffer ScriptNode available for Multi Script Editor')

    scriptWindow = GafferUI.ScriptWindow.acquire(scriptNode)
    layout = scriptWindow.getLayout()
    try:
        return layout.addEditor(EDITOR_TYPE_NAME)
    except Exception:
        editor = MultiScriptEditor(scriptNode)
        layout.addEditor(editor)
        return editor


def _activeScriptNode():
    """Best-effort: focused ScriptWindow, else first script on application.root()['scripts']."""
    try:
        focus = QtWidgets.QApplication.focusWidget()
        while focus is not None:
            try:
                owner = GafferUI.Widget._owner(focus)
            except Exception:
                owner = None
            if owner is not None:
                scriptWindow = owner.ancestor(GafferUI.ScriptWindow)
                if scriptWindow is not None:
                    return scriptWindow.scriptNode()
            focus = focus.parentWidget() if hasattr(focus, 'parentWidget') else None
    except Exception:
        pass

    try:
        import __main__
        application = getattr(__main__, 'application', None)
        if application is not None:
            scripts = application.root()['scripts']
            if len(scripts):
                return scripts[0]
    except Exception:
        pass
    return None


class MultiScriptEditor(GafferUI.Editor):
    """
    Native dockable Gaffer Editor panel.

    Builds MSE into a plain QWidget, then passes that widget as the Editor's
    top-level Qt widget (same ownership model as other Qt-backed Editors).
    """

    def __init__(self, scriptNode, **kw):
        seModule = _importScriptEditor()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            self.__scriptEditor = seModule.create_editor_instance(embedded=True)

        panel = self.__scriptEditor.takeEmbeddedPanel()
        GafferUI.Editor.__init__(self, panel, scriptNode, **kw)

        self.__scriptEditor.updateNamespace({
            'imath': imath,
            'IECore': IECore,
            'Gaffer': Gaffer,
            'GafferUI': GafferUI,
            'root': scriptNode,
            'self_main': self.__scriptEditor,
            'self_version': self.__scriptEditor.ver,
            'self_output': self.__scriptEditor.out,
            'self_help': self.__scriptEditor.mse_help,
            'self_context': 'gaffer',
        })
        self.__scriptEditor.setExecuteWrapper(self.__executeWithUndo)

    def scriptEditor(self):
        return self.__scriptEditor

    def __executeWithUndo(self, func):
        with Gaffer.UndoScope(self.scriptNode()):
            with self.context():
                func()

    def __del__(self):
        se = getattr(self, "_MultiScriptEditor__scriptEditor", None)
        if se is not None:
            try:
                se.prepare_for_host_close()
            except Exception:
                try:
                    se._stop_lifecycle_hooks()
                    se._ui_torn_down = True
                except Exception:
                    pass

    def __repr__(self):
        return 'multi_script_editor.managers._gaffer.MultiScriptEditor( scriptNode )'


GafferUI.Editor.registerType(EDITOR_TYPE_NAME, MultiScriptEditor)


def registerWithApplication(application):
    """Register editor type with GafferUI.Layouts (call from startup/gui)."""
    layouts = GafferUI.Layouts.acquire(application)
    layouts.registerEditor(EDITOR_TYPE_NAME)
    if hasattr(GafferUI, 'CompoundEditor') and hasattr(GafferUI.CompoundEditor, 'registerType'):
        try:
            GafferUI.CompoundEditor.registerType(EDITOR_TYPE_NAME, MultiScriptEditor)
        except Exception:
            pass


###################### CONTEXT HELPERS

_ROOT_PATH_RE = re.compile(
    r"(?:^|[^\w.])(root(?:\[['\"][^'\"]*['\"]\])*)\[['\"]([^'\"]*)$"
)


def _resolvePath(root, pathExpr):
    """Resolve a chain like root['A']['B'] to a GraphComponent."""
    if root is None:
        return None
    node = root
    for name in re.findall(r"\[['\"]([^'\"]*)['\"]\]", pathExpr):
        if not name:
            continue
        try:
            node = node[name]
        except Exception:
            return None
    return node


def _pathToRootExpr(scriptNode, graphComponent):
    if scriptNode is None or graphComponent is None:
        return None
    if not scriptNode.isAncestorOf(graphComponent) and not graphComponent.isSame(scriptNode):
        return None
    if graphComponent.isSame(scriptNode):
        return 'root'
    rel = graphComponent.relativeName(scriptNode)
    parts = rel.split('.')
    return 'root' + ''.join("['%s']" % p for p in parts)


def completer(line, ns):
    """Complete root['Node']['Child'] style paths from the live ScriptNode.

    Returns the 6.8.x tuple format: (name, remainder, flag).
    """
    m = _ROOT_PATH_RE.search(line)
    if not m:
        return None, None

    baseExpr = m.group(1)
    partial = m.group(2)
    root = ns.get('root')
    parent = _resolvePath(root, baseExpr)
    if parent is None:
        return None, None

    try:
        names = [c.getName() for c in parent.children()]
    except Exception:
        return None, None

    if partial:
        names = [n for n in names if n.lower().startswith(partial.lower())]
    else:
        names = list(names)

    names = sorted(set(names))
    l = len(partial)
    return [(n, n[l:], True) for n in names], None


def contextMenu(parent):
    return gafferMenuClass(parent)


class gafferMenuClass(QtWidgets.QMenu):
    def __init__(self, parent):
        super(gafferMenuClass, self).__init__('Gaffer', parent)
        self.par = parent
        self.setTearOffEnabled(True)
        self.setWindowTitle('MSE %s Gaffer' % self.par.ver)
        insertRoot = QtWidgets.QAction('Insert Selected as root[...]', parent)
        insertRoot.triggered.connect(self.insertSelected)
        self.addAction(insertRoot)
        insertNames = QtWidgets.QAction('Insert Selected Names', parent)
        insertNames.triggered.connect(self.insertSelectedNames)
        self.addAction(insertNames)

    def _selectedComponents(self):
        root = self.par.namespace.get('root')
        if root is None:
            return []
        try:
            return list(root.selection())
        except Exception:
            return []

    def insertSelected(self):
        root = self.par.namespace.get('root')
        lines = []
        for comp in self._selectedComponents():
            expr = _pathToRootExpr(root, comp)
            if expr:
                lines.append(expr)
        if lines:
            self.par.insertText('\n'.join(lines) + '\n')

    def insertSelectedNames(self):
        names = []
        for comp in self._selectedComponents():
            try:
                names.append(comp.getName())
            except Exception:
                pass
        if names:
            self.par.insertText('\n'.join(names) + '\n')


def wrapDroppedText(namespace, text, event):
    """Convert dropped node path text to root['...'] when Alt is held."""
    modifiers = event.keyboardModifiers()
    if modifiers != QtCore.Qt.AltModifier:
        return text

    root = namespace.get('root')
    if root is None or not text:
        return text

    syntax = []
    for token in [t.strip() for t in text.replace(',', '\n').splitlines() if t.strip()]:
        if token.startswith('root[') or token == 'root':
            syntax.append(token)
            continue
        if re.match(r'^[\w.]+$', token) and not token.startswith('/'):
            parts = token.split('.')
            node = root
            ok = True
            for p in parts:
                try:
                    node = node[p]
                except Exception:
                    ok = False
                    break
            if ok:
                syntax.append('root' + ''.join("['%s']" % p for p in parts))
                continue
        path = token[1:] if token.startswith('/') else token
        parts = [p for p in path.split('/') if p]
        if parts:
            node = root
            ok = True
            for p in parts:
                try:
                    node = node[p]
                except Exception:
                    ok = False
                    break
            if ok:
                syntax.append('root' + ''.join("['%s']" % p for p in parts))

    if syntax:
        return '\n'.join(syntax)
    return text
