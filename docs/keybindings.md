# Run Controls Keybindings

The run controls smoke window must be focused for key presses to be captured.

- `F5`: Start a run.
- `F6`: Stop the active run.
- `F7`: Abort the active run with `reason=keyboard_abort`.
- `F8`: Add a run tag by entering `key=value` in the terminal.
- `ESC`: Quit the run controls smoke app.

Run metadata is written under `runs/<run_id>_<timestamp>/metadata.json`.
