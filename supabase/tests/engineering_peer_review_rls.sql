-- Transactional synthetic identities only; always roll back. Never real account grants.
begin;
insert into auth.users(id,email,aud,role) values
 ('00000000-0000-4000-8000-00000000b001','flowvalue-rls-owner@example.invalid','authenticated','authenticated'),
 ('00000000-0000-4000-8000-00000000b002','flowvalue-rls-reviewer@example.invalid','authenticated','authenticated'),
 ('00000000-0000-4000-8000-00000000b003','flowvalue-rls-stranger@example.invalid','authenticated','authenticated');
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-00000000b001","role":"authenticated"}',true);
insert into public.project_heads(id,user_id,revision) values('00000000-0000-4000-8000-00000000c001',auth.uid(),2);
insert into public.project_versions(id,project_id,user_id,revision,name,payload) values
 ('00000000-0000-4000-8000-00000000d001','00000000-0000-4000-8000-00000000c001',auth.uid(),1,'Synthetic RLS v1','{"project":{}}'),
 ('00000000-0000-4000-8000-00000000d002','00000000-0000-4000-8000-00000000c001',auth.uid(),2,'Synthetic RLS v2','{"project":{}}');
insert into public.engineering_review_access(version_id,owner_id,reviewer_id) values('00000000-0000-4000-8000-00000000d001',auth.uid(),'00000000-0000-4000-8000-00000000b002');
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-00000000b002","role":"authenticated"}',true);
do $$ begin
 if (select count(*) from public.project_versions)<>1 then raise exception 'Reviewer must see exactly the granted revision'; end if;
 if exists(select 1 from public.project_heads) then raise exception 'Reviewer must not edit/read owner project head'; end if;
 begin update public.project_versions set name='FORBIDDEN'; raise exception 'Peer modified owner revision'; exception when insufficient_privilege then null; end;
 begin insert into public.engineering_review_access(version_id,owner_id,reviewer_id) values('00000000-0000-4000-8000-00000000d001',auth.uid(),'00000000-0000-4000-8000-00000000b003'); raise exception 'Peer re-shared owner revision'; exception when insufficient_privilege or foreign_key_violation then null; end;
 begin insert into public.engineering_review_events(version_id,unit_id,input_digest,action,message,author_id) values('00000000-0000-4000-8000-00000000d001','E1',repeat('a',64),'comment','Forged author','00000000-0000-4000-8000-00000000b001'); raise exception 'Peer forged author'; exception when insufficient_privilege then null; end;
end $$;
insert into public.engineering_review_events(version_id,unit_id,input_digest,action,message,author_id) values('00000000-0000-4000-8000-00000000d001','E1',repeat('a',64),'challenge','Synthetic challenge',auth.uid());
do $$ declare challenge uuid; begin
 select id into challenge from public.engineering_review_events where action='challenge';
 begin insert into public.engineering_review_events(version_id,unit_id,input_digest,action,message,author_id,parent_id) values('00000000-0000-4000-8000-00000000d001','E1',repeat('a',64),'resolve','Peer cannot resolve',auth.uid(),challenge); raise exception 'Peer resolved its own challenge'; exception when insufficient_privilege then null; end;
 begin update public.engineering_review_events set message='FORBIDDEN'; raise exception 'Review event was mutable'; exception when insufficient_privilege then null; end;
 begin delete from public.engineering_review_events; raise exception 'Review event was deletable'; exception when insufficient_privilege then null; end;
end $$;
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-00000000b003","role":"authenticated"}',true);
do $$ begin
 if exists(select 1 from public.project_versions) or exists(select 1 from public.engineering_review_events) or exists(select 1 from public.engineering_review_access) then raise exception 'Unassigned stranger can read review data'; end if;
end $$;
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-00000000b001","role":"authenticated"}',true);
do $$ declare challenge uuid; begin
 select id into challenge from public.engineering_review_events where action='challenge';
 begin insert into public.engineering_review_events(version_id,unit_id,input_digest,action,message,author_id,parent_id) values('00000000-0000-4000-8000-00000000d001','WRONG',repeat('a',64),'resolve','Wrong unit must fail',auth.uid(),challenge); raise exception 'Cross-unit resolution was allowed'; exception when foreign_key_violation then null; end;
 insert into public.engineering_review_events(version_id,unit_id,input_digest,action,message,author_id,parent_id) values('00000000-0000-4000-8000-00000000d001','E1',repeat('a',64),'resolve','Owner documented synthetic resolution',auth.uid(),challenge);
 if (select count(*) from public.engineering_review_events)<>2 then raise exception 'Owner resolution not recorded'; end if;
end $$;
update public.engineering_review_access set revoked_at=now() where reviewer_id='00000000-0000-4000-8000-00000000b002';
select set_config('request.jwt.claims','{"sub":"00000000-0000-4000-8000-00000000b002","role":"authenticated"}',true);
do $$ begin
 if exists(select 1 from public.project_versions) or exists(select 1 from public.engineering_review_events) then raise exception 'Revoked peer retained snapshot/event access'; end if;
 begin insert into public.engineering_review_events(version_id,unit_id,input_digest,action,message,author_id) values('00000000-0000-4000-8000-00000000d001','E1',repeat('a',64),'comment','FORBIDDEN after revoke',auth.uid()); raise exception 'Revoked peer posted event'; exception when insufficient_privilege then null; end;
end $$;
reset role;
do $$ begin
 if has_table_privilege('anon','public.engineering_review_events','select') or has_table_privilege('anon','public.engineering_review_access','select') then raise exception 'Anonymous review table access'; end if;
end $$;
rollback;
select 'PASS: grant scope, peer read-only, authorship, append-only events, owner resolution, stranger denial and revocation; all fixtures rolled back' as verification;
