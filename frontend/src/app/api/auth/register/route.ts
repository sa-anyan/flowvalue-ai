import {NextRequest, NextResponse} from 'next/server';
import {cloudAuthEnabled} from '@/lib/cloud-auth';

const confirmation = 'If this email is eligible, check your inbox for a confirmation link. Then return to sign in.';
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Public self-registration uses the Supabase publishable key only.
 * Supabase Auth owns password hashing, signup policy, email verification and throttling.
 * Do not use a service-role key here or grant workspace/database access directly.
 */
export async function POST(request: NextRequest) {
  if (request.headers.get('origin') !== request.nextUrl.origin) {
    return NextResponse.json({detail: 'Same-origin registration required'}, {status: 403});
  }
  if (!cloudAuthEnabled()) {
    return NextResponse.json({detail: 'Account registration is available only on the hosted FlowValue service.'}, {status: 503});
  }
  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_PUBLISHABLE_KEY) {
    return NextResponse.json({detail: 'Account registration is not configured.'}, {status: 503});
  }
  if (!(request.headers.get('content-type') || '').toLowerCase().startsWith('application/json')) {
    return NextResponse.json({detail: 'Expected JSON'}, {status: 415});
  }
  let data: unknown;
  try {
    data = await request.json();
  } catch {
    return NextResponse.json({detail: 'Invalid registration request'}, {status: 400});
  }
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return NextResponse.json({detail: 'Enter your email and password'}, {status: 400});
  }
  const {email, password} = data as Record<string, unknown>;
  if (typeof email !== 'string' || email.length > 320 || !emailPattern.test(email.trim()) ||
      typeof password !== 'string' || password.length < 12 || password.length > 128) {
    return NextResponse.json({detail: 'Enter a valid email and a password of at least 12 characters.'}, {status: 400});
  }
  try {
    const base = new URL(process.env.SUPABASE_URL);
    if (base.protocol !== 'https:') throw new Error('Invalid auth configuration');
    const signup = new URL('/auth/v1/signup', base);
    const response = await fetch(signup, {
      method: 'POST',
      headers: {
        apikey: process.env.SUPABASE_PUBLISHABLE_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({email: email.trim().toLowerCase(), password}),
      cache: 'no-store',
      redirect: 'error',
      signal: AbortSignal.timeout(10000),
    });
    if (response.status === 429) {
      return NextResponse.json({detail: 'Too many attempts. Please try again later.'}, {status: 429});
    }
    if (!response.ok) {
      // Keep user-existence and Supabase policy details out of unauthenticated responses.
      return NextResponse.json({detail: 'Unable to complete registration. Check your details or try again later.'}, {status: 400});
    }
    // Intentionally do not set auth cookies here: the sign-in flow is separate,
    // and hosted instances should require Supabase email confirmation.
    return NextResponse.json({ok: true, message: confirmation});
  } catch {
    return NextResponse.json({detail: 'Account service is temporarily unavailable'}, {status: 503});
  }
}
