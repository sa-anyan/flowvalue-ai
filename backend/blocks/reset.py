"""Clear the local workspace: projects, versions, AI cache and background-job registries.

With ``force``, running work does not block the reset. Threads cannot be
killed safely, so they are left to finish; their saves then find no study
(the row is gone) and are dropped, and their registries are already empty,
so nothing from before the reset reappears.
"""

from contextlib import ExitStack


def clear_history(store, force=False):
    from . import analyst, launch, progress
    from .opex import brainstorm
    from backend.orchestration.current_prices import _calculate

    with ExitStack() as stack:
        for guard in (launch._guard, analyst._guard, brainstorm._guard, progress._lock):
            stack.enter_context(guard)
        active = (any(t.is_alive() for t in launch._threads.values())
                  or bool(launch._delivery)
                  or any(r.get("status") == "running" for r in analyst._live.values())
                  or any(r.get("status") == "running" for r in brainstorm._live.values())
                  or any(r.get("finished") is None for r in progress._runs.values()))
        if active and not force:
            raise ValueError("Background analysis is still running. Let it finish, then reset.")
        counts = store.clear_history(force=force)
        if active:
            counts["stopped_running_work"] = True
        launch._threads.clear()
        launch._inbox.clear()
        launch._delivery.clear()
        analyst._live.clear()
        brainstorm._live.clear()
        progress._runs.clear()
        _calculate.cache_clear()
    return counts
