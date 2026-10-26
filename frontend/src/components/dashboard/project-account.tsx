"use client";
import { useEffect, useState } from "react";
import { authClient, apiFetch } from "@/lib/client-api";
import { apiError } from "@/lib/assessment";
import type { Workspace } from "@/lib/workspace";
import { Button } from "@/components/ui/button";
export function ProjectAccount({
  workspace,
  onLoad,
  onAuth,
}: {
  workspace: Workspace | null;
  onLoad: (w: Workspace) => void;
  onAuth: (clear?: boolean) => void;
}) {
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [user, setUser] = useState(""),
    [configured, setConfigured] = useState(false),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const [versions, setVersions] = useState<
    {
      id: string;
      project_id: string;
      name: string;
      revision: number;
      created_at: string;
    }[]
  >([]);
  const [current, setCurrent] = useState<{
    project_id: string;
    revision: number;
  } | null>(null);
  useEffect(() => {
    let clean = () => {};
    let alive = true;
    authClient()
      .then((c) => {
        if (!alive) return;
        setConfigured(!!c);
        if (!c) return;
        c.auth.getSession().then(({ data }) => {
          if (alive) setUser(data.session?.user.email || "");
        });
        const { data } = c.auth.onAuthStateChange((_e, s) => {
          const owner = s?.user.id || "";
          if (_e === "TOKEN_REFRESHED") return;
          const previousOwner =
            sessionStorage.getItem("flowvalue-workspace-owner") || "";
          const clear =
            _e === "SIGNED_OUT" || (!!previousOwner && previousOwner !== owner);
          if (clear) sessionStorage.removeItem("flowvalue-workspace-v1");
          sessionStorage.setItem("flowvalue-workspace-owner", owner);
          setUser(s?.user.email || "");
          if (clear) {
            setVersions([]);
            setCurrent(null);
          }
          onAuth(clear);
        });
        clean = () => data.subscription.unsubscribe();
      })
      .catch((e) => setMessage(e.message));
    return () => {
      alive = false;
      clean();
    };
  }, [onAuth]);
  async function sign(mode: "login" | "signup" | "logout") {
    setBusy(true);
    setMessage("");
    try {
      const c = await authClient();
      if (!c) throw Error("Supabase is not configured");
      if (mode === "logout") {
        await c.auth.signOut();
        setUser("");
        setCurrent(null);
        setVersions([]);
        onAuth();
        return;
      }
      const { error } =
        mode === "login"
          ? await c.auth.signInWithPassword({ email, password })
          : await c.auth.signUp({ email, password });
      if (error) throw error;
      setPassword("");
      setMessage(
        mode === "signup"
          ? "Account created. Check your email for confirmation if required."
          : "Signed in.",
      );
      onAuth();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Account request failed");
    } finally {
      setBusy(false);
    }
  }
  async function list() {
    const r = await apiFetch("/api/projects");
    if (!r.ok) throw Error(await apiError(r));
    setVersions(await r.json());
  }
  async function save(fork = false) {
    if (!workspace) return;
    setBusy(true);
    try {
      const r = await apiFetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...workspace,
          name: workspace.project.advisor_context?.name || "Untitled process",
          project_id: fork ? null : current?.project_id,
          expected_revision: fork ? 0 : current?.revision || 0,
        }),
      });
      if (!r.ok) throw Error(await apiError(r));
      const v = await r.json();
      setCurrent({ project_id: v.project_id, revision: v.revision });
      setMessage(`Saved revision ${v.revision}.`);
      await list();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }
  async function load(id: string) {
    setBusy(true);
    try {
      const r = await apiFetch(`/api/projects/${id}`);
      if (!r.ok) throw Error(await apiError(r));
      const v = await r.json();
      onLoad(v.payload);
      setCurrent({ project_id: v.project_id, revision: v.revision });
      setMessage(`Loaded ${v.name}, revision ${v.revision}.`);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Load failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel extension-panel">
      <details>
        <summary>
          Accounts & saved projects {user ? `· ${user}` : "· sign in to sync"}
        </summary>
        {!configured ? (
          <p>
            Cloud storage is not configured. The current scenario remains
            available in this browser tab.
          </p>
        ) : user ? (
          <>
            <div className="extension-actions">
              <Button disabled={busy || !workspace} onClick={() => save()}>
                Save revision
              </Button>
              <Button
                disabled={busy || !workspace}
                onClick={() => {
                  setCurrent(null);
                  save(true);
                }}
              >
                Save as new project
              </Button>
              <Button
                disabled={busy}
                onClick={() => list().catch((e) => setMessage(e.message))}
              >
                Refresh history
              </Button>
              <Button disabled={busy} onClick={() => sign("logout")}>
                Sign out
              </Button>
            </div>
            <div className="project-history">
              {versions.map((v) => (
                <button key={v.id} disabled={busy} onClick={() => load(v.id)}>
                  {v.name} · v{v.revision} ·{" "}
                  {new Date(v.created_at).toLocaleString()}
                </button>
              ))}
            </div>
          </>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sign("login");
            }}
            className="extension-actions"
          >
            <label>
              Email
              <input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </label>
            <label>
              Password
              <input
                required
                minLength={8}
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </label>
            <Button disabled={busy}>Sign in</Button>
            <Button
              type="button"
              disabled={busy || !email || password.length < 8}
              onClick={() => sign("signup")}
            >
              Create account
            </Button>
          </form>
        )}
        {message && <p role="status">{message}</p>}
      </details>
    </section>
  );
}
