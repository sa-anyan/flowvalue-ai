-- Cover the new composite foreign keys used for review ownership and resolution.
create index engineering_review_access_version_owner on public.engineering_review_access(version_id,owner_id);
create index engineering_review_events_parent_scope on public.engineering_review_events(parent_id,version_id,unit_id,parent_action);
drop index public.engineering_review_events_parent;
