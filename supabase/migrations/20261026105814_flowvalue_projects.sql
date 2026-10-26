create table public.project_heads (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 revision integer not null default 0 check(revision>=0),
 unique(id,user_id)
);
create table public.project_versions (
 id uuid primary key default gen_random_uuid(),
 project_id uuid not null,
 user_id uuid not null references auth.users(id) on delete cascade,
 revision integer not null check(revision>0),
 name text not null check(length(name) between 1 and 120),
 payload jsonb not null check(jsonb_typeof(payload)='object' and octet_length(payload::text)<=2000000),
 created_at timestamptz not null default now(),
 foreign key(project_id,user_id) references public.project_heads(id,user_id) on delete cascade,
 unique(project_id,revision)
);
create index project_versions_owner_time on public.project_versions(user_id,created_at desc);
alter table public.project_heads enable row level security;
alter table public.project_versions enable row level security;
revoke all on public.project_heads,public.project_versions from anon,authenticated;
grant select,insert,update on public.project_heads to authenticated;
grant select,insert on public.project_versions to authenticated;
create policy heads_read on public.project_heads for select to authenticated using ((select auth.uid())=user_id);
create policy heads_insert on public.project_heads for insert to authenticated with check ((select auth.uid())=user_id);
create policy heads_update on public.project_heads for update to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id);
create policy versions_read on public.project_versions for select to authenticated using ((select auth.uid())=user_id);
create policy versions_insert on public.project_versions for insert to authenticated with check ((select auth.uid())=user_id);
create function public.save_project_version(p_name text,p_project_id uuid,p_expected_revision integer,p_payload jsonb)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare project_uuid uuid; next_revision integer; output public.project_versions;
begin
 if auth.uid() is null then raise exception 'Authentication required'; end if;
 if p_project_id is null then
   insert into public.project_heads(user_id) values(auth.uid()) returning id into project_uuid;
 else
   project_uuid := p_project_id;
 end if;
 select revision+1 into next_revision from public.project_heads where id=project_uuid and user_id=auth.uid() for update;
 if next_revision is null then raise exception 'Project unavailable'; end if;
 if next_revision<>p_expected_revision+1 then raise exception 'Revision conflict: refresh history or save as new project'; end if;
 insert into public.project_versions(project_id,user_id,revision,name,payload) values(project_uuid,auth.uid(),next_revision,p_name,p_payload) returning * into output;
 update public.project_heads set revision=next_revision where id=project_uuid and user_id=auth.uid();
 return to_jsonb(output);
end $$;
revoke all on function public.save_project_version(text,uuid,integer,jsonb) from public,anon;
grant execute on function public.save_project_version(text,uuid,integer,jsonb) to authenticated;
