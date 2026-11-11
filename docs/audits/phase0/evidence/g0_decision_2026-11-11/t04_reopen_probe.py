import hashlib, json, os, sqlite3, sys
db = sys.argv[1]
def snapshot():
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    a = {r[0]: (r[1], hashlib.sha256(r[2].encode()).hexdigest(), hashlib.sha256(r[3] or b"").hexdigest()) for r in c.execute("select id,revision,state,workbook from assessments")}
    v = {r[0]: (r[1], hashlib.sha256(r[2].encode()).hexdigest()) for r in c.execute("select id,assessment_id,state from versions")}
    c.close(); return a, v
before_a, before_v = snapshot()
os.environ.update(FLOWVALUE_ASSESSMENT_DB=db, FLOWVALUE_CLOUD="false", AI_ENABLED="false")
from fastapi.testclient import TestClient
from backend.api.app import app
client = TestClient(app)
get_ok = get_fail = 0; failures = []
for key in before_a:
    r = client.get(f"/api/assessments/{key}")
    if r.status_code == 200: get_ok += 1
    else: get_fail += 1; failures.append((key[:8], r.status_code, r.text[:120]))
opened = []
for vid in before_v:
    r = client.post(f"/api/versions/{vid}/open")
    opened.append((vid[:8], r.status_code, (r.json() or {}).get("parent_version", "")[:8] if r.status_code == 200 else r.text[:120]))
after_a, after_v = snapshot()
changed_a = [k[:8] for k in before_a if after_a.get(k) != before_a[k]]
changed_v = [k[:8] for k in before_v if after_v.get(k) != before_v[k]]
print(json.dumps({"assessments": len(before_a), "versions": len(before_v), "get_ok": get_ok, "get_fail": get_fail,
  "failures": failures, "versions_opened": opened, "new_assessments_created": len(after_a) - len(before_a),
  "original_assessments_changed": changed_a, "original_versions_changed": changed_v}, indent=1))
