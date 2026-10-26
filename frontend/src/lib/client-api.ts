import { createClient, type SupabaseClient } from "@supabase/supabase-js";
let connection: Promise<SupabaseClient | null> | null = null;
export function authClient() {
  if (!connection)
    connection = fetch("/api/config")
      .then(async (r) => {
        if (!r.ok) throw new Error("Account configuration unavailable");
        const c = await r.json();
        return c.supabase_url && c.supabase_publishable_key
          ? createClient(c.supabase_url, c.supabase_publishable_key)
          : null;
      })
      .catch((e) => {
        connection = null;
        throw e;
      });
  return connection;
}
export async function apiFetch(input: string, init: RequestInit = {}) {
  const client = await authClient();
  const session = client ? (await client.auth.getSession()).data.session : null;
  const headers = new Headers(init.headers);
  if (session) headers.set("Authorization", `Bearer ${session.access_token}`);
  return fetch(input, { ...init, headers });
}
