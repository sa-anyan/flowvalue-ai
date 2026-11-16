// nextUrl can use localhost internally when the browser requested 127.0.0.1.
// The incoming Host is the public address against which the browser's Origin
// must be checked; forwarded headers are deliberately not trusted here.
export function acceptsRequestOrigin(origin: string | null, host: string | null, requestUrl: string): boolean {
  if (!origin) return true;
  try {
    const url = new URL(requestUrl);
    return origin === new URL(`${url.protocol}//${host || url.host}`).origin;
  } catch {
    return false;
  }
}
