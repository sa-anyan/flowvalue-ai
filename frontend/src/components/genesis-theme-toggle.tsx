'use client';

import {useSyncExternalStore} from 'react';

const key = 'flowvalue-genesis-theme';
const event = 'flowvalue-theme-changed';

function readTheme() {
  try {
    return (localStorage.getItem(key) ?? localStorage.getItem('flowvalue-theme')) === 'dark';
  } catch {
    return document.documentElement.dataset.genesisTheme === 'dark';
  }
}

function subscribe(update: () => void) {
  function sync() {
    document.documentElement.dataset.genesisTheme = readTheme() ? 'dark' : 'light';
    update();
  }
  sync();
  window.addEventListener(event, sync);
  window.addEventListener('storage', sync);
  return () => {
    window.removeEventListener(event, sync);
    window.removeEventListener('storage', sync);
  };
}

export function GenesisThemeToggle({inline = false}: {inline?: boolean}) {
  const dark = useSyncExternalStore(subscribe, readTheme, () => false);
  function toggle() {
    const next = dark ? 'light' : 'dark';
    document.documentElement.dataset.genesisTheme = next;
    try { localStorage.setItem(key, next); } catch {}
    window.dispatchEvent(new Event(event));
  }
  return <button type="button" className={`genesis-theme-toggle${inline ? ' genesis-theme-inline' : ''}`} onClick={toggle} aria-label="Dark theme" aria-pressed={dark}>
    <span aria-hidden="true">{dark ? '☀' : '☾'}</span>
    <span>{dark ? 'Light mode' : 'Dark mode'}</span>
  </button>;
}
