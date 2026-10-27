-- Explicit access to one immutable saved revision; no access is granted by default.
create table public.engineering_review_access (
 id uuid primary key default gen_random_uuid(),
 version_id uuid not null references public.project_versions(id) on delete cascade,
 owner_id uuid not null references auth.users(id) on delete cascade,
 reviewer_id uuid not null references auth.users(id) on delete cascade,
 created_at timestamptz not null default now(),
 revoked_at timestamptz,
 check(owner_id<>reviewer_id)
);
create unique index engineering_review_access_active on public.engineering_review_access(version_id,reviewer_id) where revoked_at is null;
create index engineering_review_access_reviewer on public.engineering_review_access(reviewer_id,version_id) where revoked_at is null;
create index engineering_review_access_owner on public.engineering_review_access(owner_id);
alter table public.engineering_review_access enable row level security;
revoke all on public.engineering_review_access from public,anon,authenticated;
grant select on public.engineering_review_access to authenticated;
grant insert(version_id,owner_id,reviewer_id) on public.engineering_review_access to authenticated;
grant update(revoked_at) on public.engineering_review_access to authenticated;
create policy review_access_read on public.engineering_review_access for select to authenticated using ((select auth.uid())=owner_id or (select auth.uid())=reviewer_id);
create policy review_access_insert on public.engineering_review_access for insert to authenticated with check (
 (select auth.uid())=owner_id and exists(select 1 from public.project_versions v where v.id=version_id and v.user_id=(select auth.uid()))
);
create policy review_access_revoke on public.engineering_review_access for update to authenticated using ((select auth.uid())=owner_id) with check ((select auth.uid())=owner_id and revoked_at is not null);
alter policy versions_read on public.project_versions to authenticated using (
 (select auth.uid())=user_id or exists(select 1 from public.engineering_review_access a where a.version_id=project_versions.id and a.reviewer_id=(select auth.uid()) and a.revoked_at is null)
);

create table public.engineering_review_events (
 id uuid primary key default gen_random_uuid(),
 version_id uuid not null references public.project_versions(id) on delete cascade,
 unit_id text not null check(length(unit_id) between 1 and 100),
 input_digest text not null check(input_digest ~ '^[0-9a-f]{64}$'),
 action text not null check(action in ('comment','challenge','resolve','agree')),
 message text not null check(length(btrim(message)) between 1 and 3000),
 author_id uuid not null references auth.users(id) on delete cascade,
 parent_id uuid references public.engineering_review_events(id),
 created_at timestamptz not null default now(),
 check((action='resolve' and parent_id is not null) or (action<>'resolve' and parent_id is null))
);
create index engineering_review_events_version on public.engineering_review_events(version_id,unit_id,created_at);
create index engineering_review_events_author on public.engineering_review_events(author_id);
create index engineering_review_events_parent on public.engineering_review_events(parent_id);
alter table public.engineering_review_events enable row level security;
revoke all on public.engineering_review_events from public,anon,authenticated;
grant select on public.engineering_review_events to authenticated;
grant insert(version_id,unit_id,input_digest,action,message,author_id,parent_id) on public.engineering_review_events to authenticated;
create policy review_events_read on public.engineering_review_events for select to authenticated using (
 exists(select 1 from public.project_versions v where v.id=version_id)
);
create policy review_events_insert on public.engineering_review_events for insert to authenticated with check (
 author_id=(select auth.uid()) and exists(select 1 from public.project_versions v where v.id=version_id)
 and (action<>'resolve' or (
   exists(select 1 from public.project_versions v where v.id=version_id and v.user_id=(select auth.uid()))
   and exists(select 1 from public.engineering_review_events p where p.id=engineering_review_events.parent_id and p.version_id=engineering_review_events.version_id and p.unit_id=engineering_review_events.unit_id and p.action='challenge')
 ))
);
-- No UPDATE/DELETE grants or policies on events. No SECURITY DEFINER functions.
