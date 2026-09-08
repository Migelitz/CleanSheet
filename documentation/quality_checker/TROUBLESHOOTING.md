# Known Issues & Troubleshooting

## `tkinterdnd2` Event Serial Crash in Python 3.12+

### Problem Description
When running CleanSheet on Python 3.12 or newer, dragging and dropping a file into the application window causes an immediate crash with the following traceback:

```python
Exception in Tkinter callback
Traceback (most recent call last):
  File "/usr/lib/python3.12/tkinter/__init__.py", line 1966, in __call__
    args = self.subst(*args)
           ^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/tkinter/__init__.py", line 1651, in _substitute
    e.serial = getint(nsign)
               ^^^^^^^^^^^^^
_tkinter.TclError: expected integer but got "%#"

```

### Root Cause

This issue originates in the underlying Tcl/Tk drag-and-drop extension used by `tkinterdnd2`.

During drag-and-drop events, the extension fails to emit a valid integer event serial number and instead passes the literal string `"%#"`. Prior to Python 3.12, Tkinter handled substitution loosely. Starting in Python 3.12, `tkinter.__init__.py` strictly enforces integer conversion on `e.serial`, triggering an unhandled `_tkinter.TclError`.

*Reference:* [cpython Issue #94861](https://github.com/python/cpython/issues/94861)

### Implemented Solution (Monkey Patch)

To prevent runtime crashes without modifying system Python libraries or waiting for upstream package updates, `tab_quality.py` applies an in-memory monkey patch to `tk.Misc._substitute` prior to mounting UI components:

```python
# ==============================================================================
# BUG FIX: tkinterdnd2 Compatibility Patch for Python 3.12+
# ==============================================================================
import tkinter as tk

_orig_substitute = tk.Misc._substitute

def _patched_substitute(self, *args):
    # args[0] is typically the event serial number. If it is the broken string,
    # replace it with a dummy integer (0) before handing to Tkinter's type checks.
    if args and len(args) > 0 and args[0] == "%#":
        args = (0,) + args[1:]
    return _orig_substitute(self, *args)

# Apply the patch globally to Tkinter
tk.Misc._substitute = _patched_substitute
# ==============================================================================
```

This intercepts incoming callback arguments, replaces the invalid `"%#"` string with `0`, and forwards the sanitized arguments to Tkinter.