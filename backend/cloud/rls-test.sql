begin;
select set_config('flowvalue.test_owner',(select id::text from auth.users order by created_at limit 1),true);
insert into public.flowvalue_rebuild_assessments(owner_id,id,revision,state,workbook)
values(current_setting('flowvalue.test_owner')::uuid,repeat('a',32),0,jsonb_build_object('id',repeat('a',32),'revision',0),'');
set local role authenticated;
select set_config('request.jwt.claim.sub',current_setting('flowvalue.test_owner'),true);
do $$ begin
 if (select count(*) from public.flowvalue_rebuild_assessments where id=repeat('a',32))<>1 then raise exception 'Owner cannot read own row'; end if;
 begin
  update public.flowvalue_rebuild_assessments set owner_id='00000000-0000-4000-8000-000000000002' where id=repeat('a',32);
  raise exception 'Ownership transfer unexpectedly allowed';
 exception when insufficient_privilege then null; end;
end $$;
select set_config('request.jwt.claim.sub','00000000-0000-4000-8000-000000000002',true);
do $$ begin
 if exists(select 1 from public.flowvalue_rebuild_assessments where id=repeat('a',32)) then raise exception 'Stranger can read row'; end if;
 begin
  insert into public.flowvalue_rebuild_assessments(owner_id,id,revision,state,workbook)
  values(current_setting('flowvalue.test_owner')::uuid,repeat('b',32),0,jsonb_build_object('id',repeat('b',32),'revision',0),'');
  raise exception 'Forged owner unexpectedly allowed';
 exception when insufficient_privilege then null; end;
end $$;
reset role;
set local role anon;
do $$ begin
 begin perform * from public.flowvalue_rebuild_assessments;raise exception 'Anonymous table access allowed';exception when insufficient_privilege then null;end;
end $$;
rollback;
