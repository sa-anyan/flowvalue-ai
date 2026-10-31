/** Explicit assessment URLs prevent another tab's localStorage from selecting a different study. */
const validId=(value:string|null|undefined):value is string=>Boolean(value&&/^[a-f0-9]{32}$/.test(value));
export function assessmentHref(path:string,id:string|null|undefined):string {
  if(!validId(id))return path;
  const url=new URL(path,'http://flowvalue.local');
  if(url.origin!=='http://flowvalue.local')throw new Error('Assessment navigation must stay local');
  url.searchParams.set('assessment',id);
  return url.pathname+url.search+url.hash;
}
export function assessmentFromUrl(url:string,stored:string|null):string {
  const requested=new URL(url,'http://flowvalue.local').searchParams.get('assessment');
  return validId(requested)?requested:validId(stored)?stored:'';
}
