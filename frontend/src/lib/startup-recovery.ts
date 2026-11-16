/** Runs as a native inline script, independently of Next/React application chunks.
 * Only an uninitialized page may recover automatically. Never reload an active
 * session with potentially unsaved inputs, and never loop if storage is blocked.
 */
export const startupRecoveryScript = String.raw`(function () {
  var ready = false;
  var key = 'flowvalue-startup-recovery:' + location.pathname + location.search;
  var timer;
  function slow() { document.documentElement.setAttribute('data-fv-startup', 'slow'); }
  function recover() {
    if (ready) return;
    slow();
    try {
      var previous = Number(sessionStorage.getItem(key));
      if (previous && Date.now() - previous < 120000) return;
      sessionStorage.setItem(key, String(Date.now()));
    } catch (_) { return; }
    location.reload();
  }
  function started() {
    ready = true;
    clearTimeout(timer);
    document.documentElement.removeAttribute('data-fv-startup');
    window.removeEventListener('error', failed, true);
    window.removeEventListener('unhandledrejection', rejected);
  }
  function failed(event) {
    var target = event.target;
    if (!ready && target && target.tagName === 'SCRIPT' && String(target.src).indexOf('/_next/') !== -1) recover();
  }
  function rejected(event) {
    var message = String(event.reason && (event.reason.message || event.reason));
    if (!ready && /ChunkLoadError|Loading chunk .*failed|Failed to fetch dynamically imported module/i.test(message)) recover();
  }
  window.addEventListener('flowvalue-started', started, {once: true});
  window.addEventListener('error', failed, true);
  window.addEventListener('unhandledrejection', rejected);
  timer = setTimeout(recover, 20000);
})();`;
