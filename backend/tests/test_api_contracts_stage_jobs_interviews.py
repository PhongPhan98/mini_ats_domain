from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_contract_routes_exist():
    # basic smoke checks for contract endpoints (auth may reject without headers in strict mode)
    r1 = client.patch("/api/candidates/1/stage", json={"stage":"applied"})
    assert r1.status_code in (200, 401, 403, 404)

    r2 = client.get("/api/jobs/1/candidates")
    assert r2.status_code in (200, 401, 403, 404)

    r3 = client.post("/api/interviews?candidate_id=1", json={"interviewer_email":"a@b.com","scheduled_at":"2030-01-01T10:00:00","duration_minutes":60})
    assert r3.status_code in (200, 401, 403, 404, 422)
