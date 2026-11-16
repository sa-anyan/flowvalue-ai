/** Clear application data without touching sign-in credentials or theme preference. */
export const freshEntryUrl = '/flow?new=1&stage=entry';

export function clearFlowValueHistory(local: Storage, session: Storage) {
  for (const storage of [local, session]) {
    const keys = Array.from({ length: storage.length }, (_, i) => storage.key(i));
    for (const key of keys) {
      if (key?.startsWith('flowvalue-') && key !== 'flowvalue-theme') storage.removeItem(key);
    }
  }
  // Other open guided tabs must also leave the deleted assessment.
  local.setItem('flowvalue-reset-at', crypto.randomUUID());
}
