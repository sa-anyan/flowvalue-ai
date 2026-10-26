// Use a public API URL for documentation links when the runtime connects over Docker DNS.
export async function GET() {
  const base =
    process.env.API_PUBLIC_URL ??
    process.env.API_INTERNAL_URL ??
    "http://127.0.0.1:8000";
  return Response.redirect(`${base.replace(/\/$/, "")}/docs`, 307);
}
