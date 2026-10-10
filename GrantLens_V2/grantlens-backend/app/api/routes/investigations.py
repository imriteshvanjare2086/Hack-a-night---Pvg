"""Investigations HTTP endpoints; existing API contract preserved."""
from datetime import datetime, timezone
from fastapi import HTTPException, Query
from sqlalchemy import select, func
from app import db
from app.schemas import CaseUpdate, Page, CaseDetail
from fastapi import APIRouter
from app.api.dependencies import audit, records, public, case_data

PREFIX='/api/v1'
router=APIRouter()

@router.get(PREFIX+'/cases',response_model=Page)
def cases(audit_id:str|None=None,status:str|None=None,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=200)):
    aid=audit(audit_id).id
    conditions=[db.Case.audit_id==aid]
    if status: conditions.append(db.Case.status==status)
    with db.Session() as s:
        total=s.scalar(select(func.count()).select_from(db.Case).where(*conditions))
        rows=[case_data(c) for c in s.scalars(select(db.Case).where(*conditions).order_by(db.Case.id).offset(offset).limit(limit))]
    return {'items':public(rows),'total':total,'offset':offset,'limit':limit}


@router.get(PREFIX+'/cases/{case_id}',response_model=CaseDetail)
def case(case_id:str,audit_id:str|None=None):
    aid=audit(audit_id).id
    with db.Session() as s:
        item=s.get(db.Case,(aid,case_id))
        if not item: raise HTTPException(404,'Case not found')
        return public(case_data(item))


@router.patch(PREFIX+'/cases/{case_id}',response_model=CaseDetail)
def update_case(case_id:str,body:CaseUpdate,audit_id:str|None=None):
    aid=audit(audit_id).id
    with db.Session.begin() as s:
        item=s.get(db.Case,(aid,case_id))
        if not item: raise HTTPException(404,'Case not found')
        if body.status:
            item.status=body.status
            db.event(aid,'case_status_updated','Case status changed to '+body.status,case_id,session=s)
        if body.note:
            item.notes=[*item.notes,{'text':body.note,'created_at':datetime.now(timezone.utc).isoformat()}]
            db.event(aid,'reviewer_note_added','Reviewer note added',case_id,session=s)
        patch=body.model_dump(exclude_none=True,exclude={'status','note'})
        if patch: item.payload={**item.payload,**patch}
        db.event(aid,'case_updated','Updated '+', '.join(body.model_dump(exclude_none=True)),case_id,session=s)
    return case(case_id,aid)


@router.get(PREFIX+'/cases/{case_id}/report',response_model=CaseDetail)
def report(case_id:str,audit_id:str|None=None):
    aid=audit(audit_id).id; result=case(case_id,aid)
    ids=set(result['beneficiary_ids'])
    accounts={r['bank_account_id'] for r in records(aid,'beneficiary') if r['beneficiary_id'] in ids}
    return {**result,'generated_at':datetime.now(timezone.utc).isoformat(),
            'cycles':public([c for c in records(aid,'cycle') if accounts & set(c['accounts'])]),
            'notice':'Review priority only. Verify evidence and legitimate explanations before any action.'}


def get_case_record_data(aid: str, case_id: str, s) -> dict:
    item = s.get(db.Case, (aid, case_id))
    if item:
        return case_data(item)
    rec = s.get(db.Record, (aid, 'cluster', case_id))
    if rec:
        c = db.Case(audit_id=aid, id=case_id, status='Needs Review', notes=[], payload=rec.payload)
        s.add(c)
        s.flush()
        return case_data(c)
    raise HTTPException(404, f'Case {case_id} not found')


@router.post(PREFIX+'/cases/{case_id}/investigation')
@router.get(PREFIX+'/cases/{case_id}/investigation')
def get_or_create_investigation(case_id: str, audit_id: str | None = None):
    from uuid import uuid4
    from app.services.copilot import generate_questions_for_case
    aid = audit(audit_id).id
    with db.Session() as s:
        c_data = get_case_record_data(aid, case_id, s)
        inv = s.scalar(select(db.Investigation).where(db.Investigation.audit_id == aid, db.Investigation.case_id == case_id))
        if not inv:
            inv_id = str(uuid4())
            now = datetime.now(timezone.utc).isoformat()
            inv = db.Investigation(
                investigation_id=inv_id,
                case_id=case_id,
                audit_id=aid,
                status='Under Review',
                created_by='Local demo auditor',
                created_at=now,
                updated_at=now,
                notes='',
            )
            s.add(inv)
            generated = generate_questions_for_case(c_data)
            for q in generated:
                q_row = db.InvestigationQuestion(
                    question_id=q['question_id'],
                    investigation_id=inv_id,
                    template_id=q['template_id'],
                    category=q['category'],
                    question_text=q['question_text'],
                    evidence_refs=q['evidence_refs'],
                    rationale=q['rationale'],
                    verification_action=q['verification_action'],
                    priority=q['priority'],
                    status=q['status'],
                    officer_notes=q['officer_notes'],
                    updated_by='Local demo auditor',
                    updated_at=now,
                )
                s.add(q_row)
            s.commit()
            db.event(aid, 'investigation_prepared', f'Investigation Copilot workspace initialized for case {case_id}', case_id=case_id)
            inv = s.get(db.Investigation, inv_id)

        questions = s.scalars(
            select(db.InvestigationQuestion)
            .where(db.InvestigationQuestion.investigation_id == inv.investigation_id)
            .order_by(db.InvestigationQuestion.question_id)
        ).all()
        q_dicts = [
            {
                'question_id': q.question_id,
                'investigation_id': q.investigation_id,
                'template_id': q.template_id,
                'category': q.category,
                'question_text': q.question_text,
                'evidence_refs': q.evidence_refs,
                'rationale': q.rationale,
                'verification_action': q.verification_action,
                'priority': q.priority,
                'status': q.status,
                'officer_notes': q.officer_notes,
                'updated_by': q.updated_by,
                'updated_at': q.updated_at,
            }
            for q in questions
        ]
        inv_dict = {
            'investigation_id': inv.investigation_id,
            'case_id': inv.case_id,
            'audit_id': inv.audit_id,
            'status': inv.status,
            'created_by': inv.created_by,
            'created_at': inv.created_at,
            'updated_at': inv.updated_at,
            'notes': inv.notes,
        }
        return {'investigation': inv_dict, 'case': public(c_data), 'questions': q_dicts}


@router.patch(PREFIX+'/investigations/{investigation_id}')
def update_investigation(investigation_id: str, body: dict):
    with db.Session.begin() as s:
        inv = s.get(db.Investigation, investigation_id)
        if not inv:
            raise HTTPException(404, 'Investigation not found')
        now = datetime.now(timezone.utc).isoformat()
        if 'status' in body and body['status']:
            inv.status = body['status']
        if 'notes' in body and body['notes'] is not None:
            inv.notes = body['notes']
        inv.updated_at = now
        db.event(inv.audit_id, 'investigation_updated', f'Investigation {investigation_id} updated: status={inv.status}', case_id=inv.case_id, session=s)
    return {'status': 'success', 'investigation_id': investigation_id}


@router.patch(PREFIX+'/investigations/{investigation_id}/questions/{question_id}')
def update_question(investigation_id: str, question_id: str, body: dict):
    with db.Session.begin() as s:
        q = s.scalar(select(db.InvestigationQuestion).where(
            db.InvestigationQuestion.investigation_id == investigation_id,
            db.InvestigationQuestion.question_id == question_id
        ))
        if not q:
            raise HTTPException(404, 'Investigation question not found')
        now = datetime.now(timezone.utc).isoformat()
        if 'status' in body and body['status']:
            q.status = body['status']
        if 'officer_notes' in body and body['officer_notes'] is not None:
            q.officer_notes = body['officer_notes']
        if 'verification_action' in body and body['verification_action'] is not None:
            q.verification_action = body['verification_action']
        q.updated_at = now
        inv = s.get(db.Investigation, investigation_id)
        if inv:
            inv.updated_at = now
        db.event(inv.audit_id if inv else '', 'investigation_question_updated', f'Question {question_id} updated to {q.status}', case_id=inv.case_id if inv else None, session=s)
    return {'status': 'success', 'question_id': question_id}


@router.get(PREFIX+'/investigations/{investigation_id}/pdf')
def download_investigation_pdf(investigation_id: str):
    from fastapi.responses import Response
    from app.services.copilot import generate_investigation_pdf
    with db.Session() as s:
        inv = s.get(db.Investigation, investigation_id)
        if not inv:
            raise HTTPException(404, 'Investigation not found')
        c_data = get_case_record_data(inv.audit_id, inv.case_id, s)
        questions = s.scalars(
            select(db.InvestigationQuestion)
            .where(db.InvestigationQuestion.investigation_id == investigation_id)
            .order_by(db.InvestigationQuestion.question_id)
        ).all()
        q_dicts = [
            {
                'question_id': q.question_id,
                'template_id': q.template_id,
                'category': q.category,
                'question_text': q.question_text,
                'evidence_refs': q.evidence_refs,
                'rationale': q.rationale,
                'verification_action': q.verification_action,
                'priority': q.priority,
                'status': q.status,
                'officer_notes': q.officer_notes,
            }
            for q in questions
        ]
        inv_dict = {
            'investigation_id': inv.investigation_id,
            'case_id': inv.case_id,
            'audit_id': inv.audit_id,
            'status': inv.status,
            'notes': inv.notes,
            'created_at': inv.created_at,
        }
        pdf_bytes = generate_investigation_pdf(c_data, inv_dict, q_dicts)
        filename = f"investigation-{inv.case_id}.pdf"
        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )


@router.get(PREFIX+'/cases/{case_id}/investigation/pdf')
def download_case_investigation_pdf(case_id: str, audit_id: str | None = None):
    # Retrieve or initialize first, then return pdf
    data = get_or_create_investigation(case_id, audit_id)
    return download_investigation_pdf(data['investigation']['investigation_id'])

