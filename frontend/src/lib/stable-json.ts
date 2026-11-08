/** Compare saved JSON by values, independent of server object-key ordering. */
export function stableJson(value: unknown): string {
  return JSON.stringify(value, (_key, item) =>
    item !== null && typeof item === 'object' && !Array.isArray(item)
      ? Object.fromEntries(Object.entries(item).sort(([a], [b]) => a.localeCompare(b)))
      : item,
  );
}
