import { stableJson } from './stable-json';

export const unsavedRevenueMessage = 'Your revenue changes are not saved. Leave without saving? Choose Cancel to stay and save your revenue.';

export function revenueDraftSignature(sales: unknown, currency: string, days: string, hours: string) {
  return stableJson({ sales, currency, days, hours });
}

export function allowRevenueLeave(dirty: boolean, confirm: (message: string) => boolean) {
  return !dirty || confirm(unsavedRevenueMessage);
}
