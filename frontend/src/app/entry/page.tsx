import { redirect } from 'next/navigation';
import ClassicEntry from '@/blocks/entry/page';
/** Entry opens the guided board; `?classic=1` keeps the previous single-page entry form. */
export default async function Page({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const query = await searchParams;
  if (query.classic === '1') return <ClassicEntry />;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (Array.isArray(value)) for (const item of value) params.append(key, item);
    else if (value !== undefined) params.set(key, value);
  }
  redirect('/flow' + (params.size ? '?' + params.toString() : ''));
}
