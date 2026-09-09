# ⚙️ Known Issues & Troubleshooting

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

The issue occurs at the interaction between tkinterdnd2 and Tkinter's event-substitution handling.

During drag-and-drop events, the underlying Tcl/Tk drag-and-drop extension can provide the literal string `"%#"` where Tkinter expects an integer event serial number.

Python 3.12's Tkinter implementation attempts to convert this value to an integer when constructing the event object:

```text
e.serial = getint(nsign)
```

Because `"%#"` is not a valid integer, Tkinter raises:

```text
_tkinter.TclError: expected integer but got "%#"
```

*Reference:* [CPython Issue #94861](https://github.com/python/cpython/issues/94861)

### Implemented Solution (Monkey Patch)

CleanSheet applies an in-memory monkey patch to `tk.Misc._substitute` before mounting the UI components.

The patch detects the invalid `"%#"` value and replaces it with `0` before passing the arguments to Tkinter's original `_substitute` implementation.



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

### Why this works

The drag-and-drop event can otherwise fail before the application's own callback receives the event.

Replacing `"%#"` with `0` gives Tkinter a valid integer value, allowing it to continue constructing the event object and dispatching the drag-and-drop callback normally.

The event serial number is not used by CleanSheet's file-processing logic, so using `0` is sufficient for this compatibility workaround.

### Scope

This is an application-level monkey patch. It:

- Does not modify the installed Python standard library.
- Does not modify tkinterdnd2 itself.
- Applies only while the CleanSheet process is running.
- Allows the existing drag-and-drop implementation to continue working.
- Can be removed when the underlying compatibility issue is resolved upstream.

### Maintenance Notice

This workaround should be reviewed when upgrading Python, Tkinter, or **tkinterdnd2**.

If a future version of **tkinterdnd2** or Tkinter resolves the underlying incompatibility, the monkey patch should be tested for necessity and removed if it is no longer required.