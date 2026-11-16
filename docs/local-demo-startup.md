# Reliable local demo startup

Run the frontend as a production build for demos. Development hot reload and
on-demand compilation are useful while coding but should not run a live demo.

From `frontend/`:

```sh
npm run demo:build
npm run demo:start -- --port 3000
```

The `FLOWVALUE_DEMO=1` scripts use `.next-demo`, separate from `.next`. This lets
a new demo build compile without overwriting a running development build. Stop
the existing frontend listener only after the replacement build passes. The API
continues on port 8000; no assessment reset or database migration is involved.
After source edits, stop the demo frontend before rebuilding its `.next-demo` directory, then restart it to publish those edits. Do not overwrite a build directory used by a running production server.
The normal `npm run dev` command retains development mode.

## Startup contract

- Server-rendered controls are hidden and inert until React attaches handlers.
  Users see an explicit opening state with a native reload link instead.
- A small native inline bootstrap runs independently of application chunks.
  Before initialization only, a failed application chunk or a 20-second stall
  triggers at most one automatic reload per exact page URL within two minutes.
- Storage refusal prevents automatic reload rather than risking a reload loop.
  The native reload link and slow-start explanation remain available.
- Once initialized, automatic recovery stops. A later error must not reload
  the page and discard edits. The route error boundary offers explicit retry.
- Saved assessment loading has its own visible state. A failed request offers
  Retry loading project; it must not masquerade as a fresh Entry form.
- Browser API requests have a bounded timeout; saves are not automatically
  replayed. The server continues to own job deduplication and persistence.

## Verification

`frontend/tests/startup-recovery.test.cjs` exercises delayed initialization,
application chunk failures, unrelated extension failures, bounded retries,
storage denial, active-session protection and the initial inert HTML.
Production browser verification should include normal project reopening,
Reset confirmation and cancellation, and blocked application-chunk startup.
Never confirm Reset on a real assessment to test responsiveness.

For an already running demo, build into a new dedicated directory first:

```sh
FLOWVALUE_DEMO_OUTPUT=.next-demo-next npm run demo:build
# After that build passes, stop the previous frontend and start its replacement:
FLOWVALUE_DEMO_OUTPUT=.next-demo-next npm run demo:start -- --port 3000
```

Use the same `FLOWVALUE_DEMO_OUTPUT` for the build and its server. Rotate to a
new directory for the next release; never rebuild the directory currently served.

Equipment domain-review changes are backend-only. Restart the API only when no
assessment/Monte Carlo job is active; no frontend rebuild or project reset is
required. Existing saved calculations remain unchanged until an explicit run.
