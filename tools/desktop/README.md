# The desktop launchers on this PC

The copies installed in `~/.local/bin` (add that folder to PATH; the icons call
them through `bash -lc`).  Keep them here so a reinstall is one copy:

    cp tools/desktop/maya-{start,stop,select-model,verify} ~/.local/bin/
    chmod +x ~/.local/bin/maya-{start,stop,select-model,verify}

| script | what it does |
| --- | --- |
| `maya-select-model` | the model picker behind **Start Maya (choose model)**: lists the installed configs through `serve/models.py`, pick one in a menu or by name (`glm`, `deepseek`, `minimax`, `qwen`), starts it on its config's port.  `MAYA_PORT` overrides the port, `--list` prints what is installed. |
| `maya-start` | starts one model directly, no question (the GLM config).  Kept because the old icon and muscle memory use it. |
| `maya-stop` | stops the server first - killing only the engine does nothing, `serve/server.py` starts it again - then the engine (`maya`, `maya-ds4`, `maya-mm3`) and waits for its RAM to come back. |
| `maya-verify` | proves a running Maya answers: waits for the model to load, sends one chat request, prints the answer with tok/s.  Checks the process behind the port, because Strata answers the same endpoints on 8080. |

Maya and Strata share port 8080 and are never run at once - each wants the whole
GPU and most of the RAM - so a port already held is reported with what holds it,
and nothing starts.

The icons themselves live in `~/Desktop` (`Start-Maya.desktop`,
`Stop-Maya.desktop`).
