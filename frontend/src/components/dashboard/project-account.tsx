"use client";
import { useEffect, useState, useRef } from "react";
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
    [configured, setConfigured] = useState<boolean | null>(null),
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
  const ownerRef = useRef("");
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
          ownerRef.current = owner;
          if (clear) {
            sessionStorage.removeItem("flowvalue-workspace-v1");
            sessionStorage.removeItem("flowvalue-project-reference");
          }
          sessionStorage.setItem("flowvalue-workspace-owner", owner);
          setUser(s?.user.email || "");
          if (clear) {
            setVersions([]);
            setCurrent(null);
          }
          if (!clear && owner) {
            try {
              const saved = JSON.parse(
                sessionStorage.getItem("flowvalue-project-reference") || "null",
              );
              if (saved?.owner === owner) setCurrent(saved.current);
            } catch {
              /* ignore damaged browser metadata */
            }
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
  useEffect(() => {
    if (!user) return;
    let alive = true;
    apiFetch("/api/projects")
      .then(async (r) => {
        if (!r.ok) throw Error(await apiError(r));
        const rows = await r.json();
        if (alive) setVersions(rows);
      })
      .catch((e) => {
        if (alive) setMessage(e.message);
      });
    return () => {
      alive = false;
    };
  }, [user]);
  function remember(value: { project_id: string; revision: number }) {
    setCurrent(value);
    sessionStorage.setItem(
      "flowvalue-project-reference",
      JSON.stringify({ owner: ownerRef.current, current: value }),
    );
  }
  async function sign(mode: "login" | "signup" | "logout") {
    setBusy(true);
    setMessage("");
    try {
      const c = await authClient();
      if (!c) throw Error("Supabase is not configured");
      if (mode === "logout") {
        const { error } = await c.auth.signOut();
        if (error) throw error;
        setUser("");
        setCurrent(null);
        setVersions([]);
        return;
      }
      const { error } =
        mode === "login"
          ? await c.auth.signInWithPassword({ email, password })
          : await c.auth.signUp({
              email,
              password,
              options: {
                emailRedirectTo: `${window.location.origin}/dashboard`,
              },
            });
      if (error) throw error;
      setPassword("");
      setMessage(
        mode === "signup"
          ? "Account created. Check your email for confirmation if required."
          : "Signed in.",
      );
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Account request failed");
    } finally {
      setBusy(false);
    }
  }
  async function list() {
    const owner = ownerRef.current;
    const r = await apiFetch("/api/projects");
    if (!r.ok) throw Error(await apiError(r));
    const rows = await r.json();
    if (owner === ownerRef.current) setVersions(rows);
  }
  async function save(fork = false) {
    if (!workspace) return;
    const owner = ownerRef.current;
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
      if (owner !== ownerRef.current) return;
      remember({ project_id: v.project_id, revision: v.revision });
      setMessage(`Saved revision ${v.revision}.`);
      await list();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }
  async function load(id: string) {
    const owner = ownerRef.current;
    setBusy(true);
    try {
      const r = await apiFetch(`/api/projects/${id}`);
      if (!r.ok) throw Error(await apiError(r));
      const v = await r.json();
      if (owner !== ownerRef.current) return;
      onLoad(v.payload);
      remember({ project_id: v.project_id, revision: v.revision });
      setMessage(`Loaded ${v.name}, revision ${v.revision}.`);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Load failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel extension-panel">
      <details open={!workspace || undefined}>
        <summary>
          Accounts & saved projects {user ? `· ${user}` : "· sign in to sync"}
        </summary>
        {configured === null ? (
          <p>Connecting to account services…</p>
        ) : !configured ? (
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
              <Button disabled={busy || !workspace} onClick={() => save(true)}>
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
            <p>
              {current
                ? `Editing saved project · revision ${current.revision}. Save revision appends to its history.`
                : "Unsaved project. Save revision creates its first saved version."}
            </p>
            <div className="project-history">
              {!versions.length && <p>No saved versions yet.</p>}
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
            <Button type="submit" disabled={busy}>Sign in</Button>
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
