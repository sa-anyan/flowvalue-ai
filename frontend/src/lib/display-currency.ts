/** Presentation only: retain the amount, sign, precision and missing-value label. */
const symbols: Record<string, string> = { USD: '$', GBP: '£', EUR: '€', CAD: 'C$', AUD: 'A$', NZD: 'NZ$', JPY: '¥', CNY: 'CN¥', INR: '₹', KRW: '₩', CHF: 'CHF ', SGD: 'S$', HKD: 'HK$', ZAR: 'R ', NGN: '₦' };
export function withCurrency(formatted: string, currency: unknown): string {
  const code = typeof currency === 'string' ? currency.trim().toUpperCase() : '';
  if (!code || !/^[+-]?\d/.test(formatted)) return formatted;
  const prefix = symbols[code] || code + ' ';
  return formatted.replace(/^([+-]?)(?=\d)/, (_, sign: string) => sign + prefix);
}
