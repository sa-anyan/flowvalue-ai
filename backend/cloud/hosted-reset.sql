-- Hosted FlowValue workspace reset. Apply to the existing Supabase project
-- before deploying the backend endpoint. No table is dropped.
--
-- The authenticated user's JWT determines the owner; caller-supplied owner
-- IDs are never accepted. SECURITY INVOKER retains table grants and RLS.
-- The entire reset is one transaction (one PostgREST RPC request).
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

  -- Lock the caller's assessment rows, then check the saved running state.
  -- A concurrent assessment write cannot slip between the check and delete.
  perform 1 from public.flowvalue_rebuild_assessments
    where owner_id = this_owner for update;
  if exists (
    select 1 from public.flowvalue_rebuild_assessments
    where owner_id = this_owner and state->>'running' = 'true'
  ) then
    raise exception 'A calculation is still running. Let it finish, then reset.';
  end if;

  -- Versions reference assessments; delete children before parents.
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

-- A public-schema function is exposed by PostgREST, but only authenticated
-- callers may execute it; each DELETE also enforces the existing owner RLS.
revoke all on function public.flowvalue_rebuild_reset_history() from public, anon;
grant execute on function public.flowvalue_rebuild_reset_history() to authenticated;

-- The original schema intentionally granted no DELETE privilege. Add only
-- the minimum rights needed by the caller-scoped atomic function.
grant delete on public.flowvalue_rebuild_assessments,
                public.flowvalue_rebuild_versions,
                public.flowvalue_rebuild_cache to authenticated;
