/** Friendly percentages at the UI boundary; canonical inputs remain fractions. */
export function displayInput(
  value: string | number | undefined,
  percent: boolean,
) {
  return percent && value !== "" && value !== undefined
    ? Number(value) * 100
    : (value ?? "");
}
export function storedInput(value: string, percent: boolean) {
  return percent && value !== "" ? String(Number(value) / 100) : value;
}
