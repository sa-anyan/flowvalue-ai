-- Separate tables; the previous production project's tables are untouched.
create table public.flowvalue_rebuild_assessments (
 owner_id uuid not null references auth.users(id),
 id text not null check(id ~ '^[a-f0-9]{32}$'),
 revision integer not null check(revision >= 0),
 state jsonb not null,
 workbook text not null,
 created_at timestamptz not null default now(),
 primary key(owner_id,id),
 check(state->>'id' = id),
 check((state->>'revision')::integer = revision)
);
create table public.flowvalue_rebuild_versions (
 owner_id uuid not null references auth.users(id),
 id text not null check(id ~ '^[a-f0-9]{32}$'),
 assessment_id text not null,
 name text not null check(length(name) between 1 and 120),
 state jsonb not null,
 created_at timestamptz not null default now(),
 primary key(owner_id,id),
 foreign key(owner_id,assessment_id) references public.flowvalue_rebuild_assessments(owner_id,id)
);
create table public.flowvalue_rebuild_cache (
 owner_id uuid not null references auth.users(id),
 key text not null,
 value jsonb not null,
 primary key(owner_id,key)
);
alter table public.flowvalue_rebuild_assessments enable row level security;
alter table public.flowvalue_rebuild_versions enable row level security;
alter table public.flowvalue_rebuild_cache enable row level security;
create policy rebuild_assessments_owner on public.flowvalue_rebuild_assessments to authenticated using ((select auth.uid())=owner_id) with check ((select auth.uid())=owner_id);
create policy rebuild_versions_owner on public.flowvalue_rebuild_versions to authenticated using ((select auth.uid())=owner_id) with check ((select auth.uid())=owner_id);
create policy rebuild_cache_owner on public.flowvalue_rebuild_cache to authenticated using ((select auth.uid())=owner_id) with check ((select auth.uid())=owner_id);
revoke all on public.flowvalue_rebuild_assessments,public.flowvalue_rebuild_versions,public.flowvalue_rebuild_cache from anon;
grant select,insert,update on public.flowvalue_rebuild_assessments,public.flowvalue_rebuild_cache to authenticated;
grant select,insert on public.flowvalue_rebuild_versions to authenticated;
create index rebuild_versions_owner_created on public.flowvalue_rebuild_versions(owner_id,created_at desc);


-- Hosted reset capability (for first-time schema installation).
-- Existing deployments: apply backend/cloud/hosted-reset.sql instead.
create or replace function public.flowvalue_rebuild_reset_history()
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  this_owner uuid := (select auth.uid());
  deleted_versions integer := 0;
  deleted_assessments integer := 0;
  deleted_cache integer := 0;
begin
  if this_owner is null then
    raise exception 'Sign in required';
  end if;
  perform 1 from public.flowvalue_rebuild_assessments
    where owner_id = this_owner for update;
  if exists (
    select 1 from public.flowvalue_rebuild_assessments
    where owner_id = this_owner and state->>'running' = 'true'
  ) then
    raise exception 'A calculation is still running. Let it finish, then reset.';
  end if;
  delete from public.flowvalue_rebuild_versions where owner_id = this_owner;
  get diagnostics deleted_versions = row_count;
  delete from public.flowvalue_rebuild_assessments where owner_id = this_owner;
  get diagnostics deleted_assessments = row_count;
  delete from public.flowvalue_rebuild_cache where owner_id = this_owner;
  get diagnostics deleted_cache = row_count;
  return jsonb_build_object(
    'assessments', deleted_assessments,
    'versions', deleted_versions,
    'ai_cache', deleted_cache
  );
end;
$$;
revoke all on function public.flowvalue_rebuild_reset_history() from public, anon;
grant execute on function public.flowvalue_rebuild_reset_history() to authenticated;
grant delete on public.flowvalue_rebuild_assessments,
                public.flowvalue_rebuild_versions,
                public.flowvalue_rebuild_cache to authenticated;
