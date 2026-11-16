'use client';
import {useState, type FormEvent} from 'react';
import './auth.css';

type Mode = 'sign-in' | 'create';
type AuthResult = {ok?: boolean; detail?: string; message?: string};

export default function Login() {
  const [mode, setMode] = useState<Mode>('sign-in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false);

  function changeMode(next: Mode) {
    setMode(next);
    setPassword('');
    setConfirmPassword('');
    setError('');
    setSuccess('');
    setShowPassword(false);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setError('');
    setSuccess('');
    if (mode === 'create') {
      if (password.length < 12) {
        setError('Use at least 12 characters for your password.');
        return;
      }
      if (password !== confirmPassword) {
        setError('The passwords do not match.');
        return;
      }
    }
    setBusy(true);
    try {
      const response = await fetch(mode === 'create' ? '/api/auth/register' : '/api/auth', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, password}),
        cache: 'no-store',
      });
      const payload = await response.json() as AuthResult;
      if (!response.ok) throw new Error(payload.detail || 'Something went wrong. Please try again.');
      if (mode === 'create') {
        setSuccess(payload.message || 'Check your inbox to verify your email, then sign in.');
        setPassword('');
        setConfirmPassword('');
      } else {
        window.location.assign('/entry');
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to connect. Please try again.');
    } finally {
      setBusy(false);
    }
  }

  return <main className="fv-auth">
    <div className="fv-auth-canvas">
      <section className="fv-auth-story" aria-label="About FlowValue">
        <a href="/" className="fv-auth-brand" aria-label="FlowValue AI home"><span className="fv-auth-brand-mark">≋</span> flowvalue <span>AI</span></a>
        <div className="fv-auth-story-center">
          <span className="fv-auth-eyebrow"><i/> ENGINEERING INTELLIGENCE</span>
          <h1>Better decisions.<br/><em>Built on evidence.</em></h1>
          <p>Explore your process, understand the economics, and build a clearer investment case — all in one workspace.</p>
          <div className="fv-auth-visual" aria-hidden="true">
            <div className="fv-auth-visual-grid"/>
            <div className="fv-auth-orbit fv-auth-orbit-one"/><div className="fv-auth-orbit fv-auth-orbit-two"/>
            <div className="fv-auth-visual-center">FV<span>↗</span></div>
            <span className="fv-auth-visual-float fv-auth-visual-float-one">PROCESS</span>
            <span className="fv-auth-visual-float fv-auth-visual-float-two">ECONOMICS</span>
          </div>
        </div>
        <div className="fv-auth-story-foot"><span>PROCESS</span><span className="fv-auth-story-line"/><span>VALUE</span><span className="fv-auth-story-line"/><span>INSIGHT</span></div>
      </section>

      <section className="fv-auth-card" aria-labelledby="fv-auth-title">
        <div className="fv-auth-form-wrap">
          <div className="fv-auth-tag">YOUR WORKSPACE <span>↗</span></div>
          <div className="fv-auth-heading">
            <h2 id="fv-auth-title">{mode === 'create' ? 'Create your account' : 'Welcome back'}</h2>
            <p>{mode === 'create' ? 'A new space for your next engineering idea.' : 'Sign in to continue your analysis.'}</p>
          </div>

          <div className="fv-auth-switch" role="group" aria-label="Account access">
            <button type="button" aria-pressed={mode === 'sign-in'} onClick={() => changeMode('sign-in')} disabled={busy}>Sign in</button>
            <button type="button" aria-pressed={mode === 'create'} onClick={() => changeMode('create')} disabled={busy}>Create an account</button>
          </div>

          {success ? <div className="fv-auth-complete" role="status">
            <span className="fv-auth-complete-icon" aria-hidden="true">✓</span>
            <h3>Check your email</h3>
            <p>{success}</p>
            <button className="fv-auth-submit" type="button" onClick={() => changeMode('sign-in')}>Back to sign in <span aria-hidden="true">↗</span></button>
          </div> : <form className="fv-auth-form" onSubmit={submit}>
            <label><span>Email address</span><input type="email" autoComplete="email" required maxLength={320} placeholder="you@company.com" value={email} onChange={e => setEmail(e.target.value)}/></label>
            <label><span>Password</span>
              <div className="fv-auth-password">
                <input type={showPassword ? 'text' : 'password'} autoComplete={mode === 'create' ? 'new-password' : 'current-password'} required minLength={mode === 'create' ? 12 : undefined} maxLength={mode === 'create' ? 128 : 4096} placeholder={mode === 'create' ? 'At least 12 characters' : 'Enter your password'} value={password} onChange={e => setPassword(e.target.value)}/>
                <button type="button" className="fv-auth-reveal" onClick={() => setShowPassword(v => !v)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? 'Hide' : 'Show'}</button>
              </div>
            </label>
            {mode === 'create' && <label><span>Confirm password</span><input type={showPassword ? 'text' : 'password'} autoComplete="new-password" required minLength={12} maxLength={128} placeholder="Repeat your password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)}/></label>}
            {mode === 'create' && <p className="fv-auth-note"><span aria-hidden="true">✦</span> An email confirmation may be required before you sign in.</p>}
            {error && <p className="fv-auth-error" role="alert">{error}</p>}
            <button className="fv-auth-submit" type="submit" disabled={busy} aria-busy={busy}>{busy ? <><span className="fv-auth-spinner" aria-hidden="true"/> {mode === 'create' ? 'Creating account…' : 'Signing in…'}</> : <>{mode === 'create' ? 'Create account' : 'Sign in to workspace'} <span aria-hidden="true">↗</span></>}</button>
          </form>}
          <p className="fv-auth-bottom">{mode === 'create' ? 'Already have an account?' : 'New to FlowValue?'} <button type="button" onClick={() => changeMode(mode === 'create' ? 'sign-in' : 'create')}>{mode === 'create' ? 'Sign in' : 'Create an account'}</button></p>
        </div>
        <p className="fv-auth-footer">FlowValue AI · Traceable engineering economics</p>
      </section>
    </div>
  </main>;
}
