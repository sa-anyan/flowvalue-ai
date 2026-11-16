"""Clear an idle local workspace without orphaning active background jobs."""

from contextlib import ExitStack


def clear_history(store):
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
        if active:
            raise ValueError("Background analysis is still running. Let it finish, then reset.")
        counts = store.clear_history()
        launch._threads.clear()
        launch._inbox.clear()
        launch._delivery.clear()
        analyst._live.clear()
        brainstorm._live.clear()
        progress._runs.clear()
        _calculate.cache_clear()
    return counts
