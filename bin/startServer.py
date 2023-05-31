#  Copyright (c) 2023 JukeBox Developers - All Rights Reserved
#  This file is part of the JukeBox Music App and is released under the "MIT License Agreement"
#  Please see the LICENSE file that should have been included as part of this package

import multiprocessing
import os
import pathlib
import sys
import time
from typing import Callable

import uvicorn
import watchfiles

from jukebox.globals import root
from jukebox.scheduler import run_scheduler
from jukebox.utils import get_logger, logging_config

logger = get_logger()

run_config: dict = {
    'app': 'jukebox.main:app',
    'host': 'localhost',
    'port': 8000,
    'workers': 4,
    'log_config': logging_config,
}

multiprocessing.allow_connection_pickling()
spawn = multiprocessing.get_context("spawn")

processes: list[spawn.Process] = []


def start_process(config: uvicorn.Config, target: Callable, *args: list, **kwargs: dict) -> spawn.Process:
    try:
        stdin_fno = sys.stdin.fileno()
    except OSError:
        stdin_fno = None

    process = spawn.Process(
        target=child,
        kwargs={
            "config": config,
            "target": target,
            "args": args,
            "kwargs": kwargs,
            "stdin_fno": stdin_fno,
        }
    )
    process.start()
    return process


def child(config: uvicorn.Config, target: Callable, args: list, kwargs: dict, stdin_fno: int = None) -> None:
    # Re-open stdin.
    if stdin_fno is not None:
        sys.stdin = os.fdopen(stdin_fno)

    # Logging needs to be setup again for each child.
    config.configure_logging()

    # Run target
    target(*args, **kwargs)


def prettify_changes(changes) -> str:
    paths: list[str] = []

    for change in changes:
        path = pathlib.Path(change[1])
        try:
            paths.append(f"'{path.relative_to(root)}'")
        except ValueError:
            paths.append(f"'{path}'")

    return ', '.join(paths)


def main():
    logger.info("Starting development server at http://%s:%d/", run_config['host'], run_config['port'])
    logger.info("Quit the server with CONTROL-C.")

    config = uvicorn.Config(**run_config)
    sockets = [config.bind_socket()]
    worker = uvicorn.Server(config)

    watcher = watchfiles.watch(
        root / 'jukebox',
        watch_filter=watchfiles.PythonFilter(
            extra_extensions=['.yml', '.yaml'],
        ),
    )

    while True:
        # Stop running processes (if any)
        while len(processes) > 0:
            process: spawn.Process = processes.pop()
            process.terminate()
            process.join()

        # Bootstrap
        for _ in range(config.workers):
            processes.append(start_process(config, worker.run, sockets))
        processes.append(start_process(config, run_scheduler))

        # Wait for changes
        try:
            changes = next(watcher)
            logger.debug("Watchfiles detected changes in %s. Reloading ...", prettify_changes(changes))
        except (StopIteration, KeyboardInterrupt):
            break

    time.sleep(1)
    logger.info("Server stopped !!!")


if __name__ == "__main__":
    main()
