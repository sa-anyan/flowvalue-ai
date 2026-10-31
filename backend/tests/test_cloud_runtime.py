"""Hosted isolation, caller-token transport and background context boundaries."""
import unittest
from unittest.mock import patch,Mock
from fastapi.testclient import TestClient
from backend.cloud.runtime import workspace,WorkspaceProxy,ContextExecutor
from backend.cloud.store import CloudStore

class CloudRuntimeTests(unittest.TestCase):
 def test_proxy_fails_closed_without_tenant(self):
  with self.assertRaises(PermissionError):WorkspaceProxy().get('anything')
 def test_worker_preserves_its_own_tenant(self):
  with ContextExecutor(max_workers=1) as executor:
   first=workspace.set('owner-a');future=executor.submit(workspace.get);workspace.reset(first)
   second=workspace.set('owner-b');other=executor.submit(workspace.get);workspace.reset(second)
   self.assertEqual(future.result(),'owner-a');self.assertEqual(other.result(),'owner-b')
   self.assertIsNone(workspace.get())
 def test_store_revision_conflict(self):
  store=CloudStore('https://example.supabase.co','publishable','caller-token','owner-a')
  with patch.object(store,'request',return_value=[]):
   with self.assertRaises(ValueError):store.put({'id':'a'*32,'revision':4},4)
 def test_no_foreign_record_fallback(self):
  store=CloudStore('https://example.supabase.co','publishable','caller-token','owner-a')
  with patch.object(store,'request',return_value=[]):
   with self.assertRaises(KeyError):store.get('b'*32)
 def test_hosted_api_rejects_missing_session(self):
  import backend.api.app as api
  with patch.object(api,'CLOUD',True),TestClient(api.app,base_url='https://host.example') as client:
   self.assertEqual(client.get('/api/versions').status_code,401)
   self.assertEqual(client.get('/api/health').status_code,200)
 def test_hosted_request_uses_verified_owner_store(self):
  import backend.api.app as api
  scoped=Mock();scoped.all_versions.return_value=[{'id':'owner-only'}]
  with patch.object(api,'CLOUD',True),patch.object(api,'store',WorkspaceProxy()),patch('backend.cloud.runtime.verified_workspace',return_value=scoped) as verify,TestClient(api.app,base_url='https://host.example') as client:
   response=client.get('/api/versions',headers={'Authorization':'Bearer user-token'})
   self.assertEqual(response.json(),[{'id':'owner-only'}]);verify.assert_called_once_with('user-token')
  self.assertIsNone(workspace.get())
 def test_invalid_token_is_not_local_access(self):
  import backend.api.app as api
  with patch.object(api,'CLOUD',True),patch('backend.cloud.runtime.verified_workspace',side_effect=PermissionError('Invalid')),TestClient(api.app,base_url='https://host.example') as client:
   self.assertEqual(client.get('/api/versions',headers={'Authorization':'Bearer forged'}).status_code,401)
