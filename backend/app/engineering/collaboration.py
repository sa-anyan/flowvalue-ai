"""Saved-revision peer review under the caller's bearer token and RLS."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field

from app.auth import authenticated_user, project_rest
from app.engine.costing import Model
from app.engineering.investigation import investigate
from app.engineering.review import filter_value, open_challenges

router = APIRouter(prefix="/api/engineering/reviews")


async def saved_version(request, version_id):
    rows = await project_rest(
        request, "GET", f"project_versions?id=eq.{version_id}&select=*"
    )
    if not rows:
        raise HTTPException(404, "Saved revision not found or access revoked")
    return rows[0]


@router.get("/identity")
async def identity(user: Annotated[dict, Depends(authenticated_user)]):
    return {
        "account_id": user["id"],
        "notice": "Give this account ID to a project owner to request review access. It is not an API key.",
    }


@router.get("/{version_id}")
async def review_snapshot(
    version_id: UUID,
    request: Request,
    user: Annotated[dict, Depends(authenticated_user)],
):
    from app.main import AssessmentRequest

    row = await saved_version(request, version_id)
    project = AssessmentRequest.model_validate(row["payload"]["project"])
    unit_ids = list(
        dict.fromkeys(
            [e.unit_id for e in project.costing.equipment]
            + [
                c.unit_id
                for c in (project.study.engineering_cases if project.study else [])
            ]
        )
    )
    events = await project_rest(
        request,
        "GET",
        f"engineering_review_events?version_id=eq.{version_id}&order=created_at.asc&limit=1000",
    )
    access = await project_rest(
        request,
        "GET",
        f"engineering_review_access?version_id=eq.{version_id}&order=created_at.asc&limit=200",
    )
    reports = [investigate(project, id) for id in unit_ids]
    return {
        "version": {
            k: row[k]
            for k in ("id", "project_id", "user_id", "name", "revision", "created_at")
        },
        "is_owner": row["user_id"] == user["id"],
        "account_id": user["id"],
        "units": reports,
        "events": events,
        "access": access,
        "open_challenges": open_challenges(events),
        "notice": "Review of this saved revision only. Changes in the working model require a new saved revision and a new explicit grant. Agreement is not engineering certification.",
    }


class AccessRequest(Model):
    reviewer_id: UUID
    confirm_snapshot_access: bool = False


@router.post("/{version_id}/access")
async def grant_access(
    version_id: UUID,
    body: AccessRequest,
    request: Request,
    user: Annotated[dict, Depends(authenticated_user)],
):
    row = await saved_version(request, version_id)
    if row["user_id"] != user["id"]:
        raise HTTPException(403, "Only the revision owner can grant review access")
    if not body.confirm_snapshot_access:
        raise HTTPException(
            422,
            "Confirm that the named account may read the entire saved revision, including financials and streams",
        )
    if str(body.reviewer_id) == user["id"]:
        raise HTTPException(
            422, "The owner already has access; choose a different reviewer account"
        )
    return await project_rest(
        request,
        "POST",
        "engineering_review_access",
        body={
            "version_id": str(version_id),
            "owner_id": user["id"],
            "reviewer_id": str(body.reviewer_id),
        },
    )


class RevokeRequest(Model):
    access_id: UUID


@router.post("/{version_id}/revoke")
async def revoke_access(
    version_id: UUID,
    body: RevokeRequest,
    request: Request,
    user: Annotated[dict, Depends(authenticated_user)],
):
    from datetime import UTC, datetime

    row = await saved_version(request, version_id)
    if row["user_id"] != user["id"]:
        raise HTTPException(403, "Only the revision owner can revoke review access")
    rows = await project_rest(
        request,
        "PATCH",
        f"engineering_review_access?id=eq.{body.access_id}&version_id=eq.{version_id}&owner_id=eq.{user['id']}&revoked_at=is.null",
        body={"revoked_at": datetime.now(UTC).isoformat()},
    )
    if not rows:
        raise HTTPException(404, "Active review grant not found")
    return {
        "revoked": True,
        "notice": "Future access revoked. Previously downloaded data cannot be recalled.",
    }


class ReviewEventRequest(Model):
    unit_id: str = Field(min_length=1, max_length=100)
    action: Literal["comment", "challenge", "resolve", "agree"]
    message: str = Field(min_length=1, max_length=3000, pattern=r"\S")
    parent_id: UUID | None = None


@router.post("/{version_id}/events")
async def add_event(
    version_id: UUID,
    body: ReviewEventRequest,
    request: Request,
    user: Annotated[dict, Depends(authenticated_user)],
):
    from app.main import AssessmentRequest

    row = await saved_version(request, version_id)
    try:
        report = investigate(
            AssessmentRequest.model_validate(row["payload"]["project"]), body.unit_id
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if body.action == "resolve":
        if row["user_id"] != user["id"]:
            raise HTTPException(403, "Only the owner can resolve a challenge")
        if body.parent_id is None:
            raise HTTPException(422, "Choose the challenge being resolved")
        parent = await project_rest(
            request,
            "GET",
            f"engineering_review_events?id=eq.{body.parent_id}&version_id=eq.{version_id}&unit_id=eq.{filter_value(body.unit_id)}&action=eq.challenge&select=id",
        )
        if not parent:
            raise HTTPException(
                422, "Resolution must reference a challenge for the same saved unit"
            )
    elif body.parent_id is not None:
        raise HTTPException(422, "Only resolutions can reference a parent challenge")
    return await project_rest(
        request,
        "POST",
        "engineering_review_events",
        body={
            "version_id": str(version_id),
            "unit_id": body.unit_id,
            "input_digest": report["digest"],
            "action": body.action,
            "message": body.message.strip(),
            "author_id": user["id"],
            "parent_id": str(body.parent_id) if body.parent_id else None,
        },
    )
