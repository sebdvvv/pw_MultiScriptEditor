"""Qt5 / Qt6 helpers."""


def qt_exec(obj, *args, **kwargs):
    """Run QDialog/QMenu/QApplication modal loop without exec_ deprecation warnings."""
    fn = getattr(obj, 'exec', None)
    if callable(fn):
        return fn(*args, **kwargs)
    return obj.exec_(*args, **kwargs)
