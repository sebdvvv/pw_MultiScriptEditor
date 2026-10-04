# Multi Script Editor for Gaffer

Native dockable **GafferUI.Editor** panel — same registration path as custom
pipeline shelves (`Editor.registerType` + `Layouts.registerEditor`).

Tested against **Gaffer 1.7.3.1** (Windows, PySide6).

Built on [charliewales/pw_MultiScriptEditor 6.8.0](https://github.com/charliewales/pw_MultiScriptEditor/releases/tag/6.8.0) + Gaffer port.

**Author (Gaffer port):** Sebastien Durand

---

## What you get

- Panel type **Multi Script Editor** (add from the layout / editor menu)
- Menu entry **Window -> Multi Script Editor**
- Execution namespace like Gaffer's built-in Python Editor:
  - `root` — current `ScriptNode`
  - `Gaffer`, `GafferUI`, `IECore`, `imath`
- Graph edits wrapped in `Gaffer.UndoScope` + the editor context
- Host helpers: `root['...']` completion, Alt-drop path wrapping
- Prefs / tab session under `~/gaffer/mse_settings/` (Windows: `%USERPROFILE%\gaffer\mse_settings\`)

---

## Install (recommended layout)

**Do not** put the whole `multi_script_editor` package inside `startup/gui/`.
Gaffer executes every `.py` under startup as config and will error on widgets/vendor code.

### 1. Package on PYTHONPATH

Gaffer already puts `<GAFFER_ROOT>/python` on `PYTHONPATH`. The folder that
**contains** `multi_script_editor/` must be on that path.

**Option A — package directly under `python/` (simplest):**

```text
<GAFFER_ROOT>/python/multi_script_editor/
```

**Option B — wrapped in a parent folder (also supported):**

```text
<GAFFER_ROOT>/python/pw_MultiScriptEditor/multi_script_editor/
```

### 2. Startup script only in `startup/gui`

Copy **one** file:

| From | To |
|------|----|
| `multi_script_editor/managers/gaffer/startup/gui/multiScriptEditor.py` | `<GAFFER_ROOT>/startup/gui/multiScriptEditor.py` |
| or the same file | `~/gaffer/startup/gui/multiScriptEditor.py` |

### 3. Restart Gaffer

Then open via **Window -> Multi Script Editor**, layout editor type **Multi Script Editor**, or:

```python
import multi_script_editor
multi_script_editor.showGaffer()
```

---

## Notes

| Topic | Detail |
|-------|--------|
| `root` | Bound to the ScriptNode of the window that owns the panel |
| Undo | Node graph edits go through `Gaffer.UndoScope` |
| Menus | File / Tools / Run / Options / Help appear as a button strip inside Gaffer tabs |
| Qt | Gaffer manager bootstraps Gaffer's Qt/PySide6 into MSE `vendor.Qt` |
| Session | 6.8.x autosave + `aboutToQuit` persist tabs under `~/gaffer/mse_settings/` |

## Developer map

| File | Role |
|------|------|
| `multi_script_editor/managers/_gaffer.py` | Native Editor, namespace, UndoScope, completer/drop |
| `multi_script_editor/managers/gaffer/startup/gui/multiScriptEditor.py` | Startup registration + Window menu |
| `multi_script_editor/scriptEditor.py` | `embedded=True`, `takeEmbeddedPanel()`, execute wrapper |
| `multi_script_editor/__init__.py` | `showGaffer(scriptNode=None)` |
