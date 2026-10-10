from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_copilot_investigation_lifecycle():
    # 1. Get an existing completed audit
    audits_res = client.get("/api/v1/audits")
    assert audits_res.status_code == 200
    audits = audits_res.json()
    assert len(audits) > 0
    aid = audits[0]["audit_id"]

    # 2. Get a case
    cases_res = client.get(f"/api/v1/cases?audit_id={aid}&limit=1")
    assert cases_res.status_code == 200
    cases_data = cases_res.json()
    assert cases_data["total"] > 0
    case_item = cases_data["items"][0]
    cid = case_item["case_id"]

    # 3. Initialize or fetch investigation workspace
    res = client.post(f"/api/v1/cases/{cid}/investigation?audit_id={aid}")
    assert res.status_code == 200
    data = res.json()
    assert "investigation" in data
    assert "questions" in data
    assert "case" in data
    inv_id = data["investigation"]["investigation_id"]
    assert inv_id
    assert len(data["questions"]) > 0

    first_q = data["questions"][0]
    qid = first_q["question_id"]
    assert first_q["status"] in ["Pending", "Verified", "Needs Follow-up", "Not Applicable"]
    assert "question_text" in first_q
    assert "rationale" in first_q
    assert "verification_action" in first_q

    # 4. Update question status and notes
    patch_q = client.patch(
        f"/api/v1/investigations/{inv_id}/questions/{qid}",
        json={"status": "Needs Follow-up", "officer_notes": "Pending response from university registrar"}
    )
    assert patch_q.status_code == 200
    assert patch_q.json()["status"] == "success"

    # 5. Update investigation observations and status
    patch_inv = client.patch(
        f"/api/v1/investigations/{inv_id}",
        json={"status": "In Progress", "notes": "Initial inquiry sent to nodal officer."}
    )
    assert patch_inv.status_code == 200
    assert patch_inv.json()["status"] == "success"

    # 6. Verify updates persisted
    fetch_again = client.get(f"/api/v1/cases/{cid}/investigation?audit_id={aid}")
    assert fetch_again.status_code == 200
    refetched = fetch_again.json()
    assert refetched["investigation"]["status"] == "In Progress"
    assert refetched["investigation"]["notes"] == "Initial inquiry sent to nodal officer."
    q_updated = next(q for q in refetched["questions"] if q["question_id"] == qid)
    assert q_updated["status"] == "Needs Follow-up"
    assert q_updated["officer_notes"] == "Pending response from university registrar"

    # 7. Generate and download PDF
    pdf_res = client.get(f"/api/v1/investigations/{inv_id}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000
    assert pdf_res.content.startswith(b"%PDF")
