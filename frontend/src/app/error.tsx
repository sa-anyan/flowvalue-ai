'use client';

export default function ErrorPage({reset}: {error: Error & {digest?: string}; reset: () => void}) {
 return <main style={{maxWidth:600,margin:'10vh auto',padding:24}} role="alert">
  <h1>The workspace could not be displayed</h1>
  <p>Your saved project has not been reset. Try opening this page again.</p>
  <button type="button" onClick={reset}>Try again</button>{' '}
  <a href="">Reload page</a>
 </main>;
}
