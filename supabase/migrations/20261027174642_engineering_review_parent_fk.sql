-- Parent relationships are scoped by a composite FK, avoiding self-referential RLS.
create unique index engineering_review_events_parent_target on public.engineering_review_events(id,version_id,unit_id,action);
alter table public.engineering_review_events add column parent_action text generated always as (case when action='resolve' then 'challenge'::text else null::text end) stored;
alter table public.engineering_review_events add constraint review_event_parent_scope_fk foreign key(parent_id,version_id,unit_id,parent_action) references public.engineering_review_events(id,version_id,unit_id,action);
drop policy review_events_insert on public.engineering_review_events;
create policy review_events_insert on public.engineering_review_events for insert to authenticated with check (
 author_id=(select auth.uid()) and exists(select 1 from public.project_versions v where v.id=version_id)
 and (action<>'resolve' or exists(select 1 from public.project_versions v where v.id=version_id and v.user_id=(select auth.uid())))
);
