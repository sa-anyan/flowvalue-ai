-- Enforce snapshot ownership with a composite foreign key, avoiding cyclic RLS queries.
create unique index project_versions_id_owner on public.project_versions(id,user_id);
alter table public.engineering_review_access add constraint review_access_version_owner_fk foreign key(version_id,owner_id) references public.project_versions(id,user_id) on delete cascade;
drop policy review_access_insert on public.engineering_review_access;
create policy review_access_insert on public.engineering_review_access for insert to authenticated with check ((select auth.uid())=owner_id);
