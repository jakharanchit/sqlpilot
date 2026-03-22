from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from tools.migrator import (
    list_migrations,
    mark_applied,
    mark_rolled_back,
    get_pending_migrations,
)

router = APIRouter(prefix="/api/migrations", tags=["migrations"])


class ApplyRequest(BaseModel):
    client: Optional[str] = None


@router.get("")
def list_all(status: str = None):
    return list_migrations(status_filter=status)


@router.get("/{number}")
def get_migration(number: int):
    all_migs = list_migrations()
    match = next((m for m in all_migs if m["number"] == number), None)
    if not match:
        raise HTTPException(404, f"Migration {number:03d} not found")
    return match


@router.post("/{number}/apply")
def apply_migration(number: int, body: ApplyRequest = ApplyRequest()):
    success = mark_applied(number, body.client)
    if not success:
        raise HTTPException(404, f"Migration {number:03d} not found")
    mig = next((m for m in list_migrations() if m["number"] == number), None)
    return {"success": True, "migration": mig}


@router.post("/{number}/rollback")
def rollback_migration(number: int):
    success = mark_rolled_back(number)
    if not success:
        raise HTTPException(404, f"Migration {number:03d} not found")
    mig = next((m for m in list_migrations() if m["number"] == number), None)
    return {"success": True, "migration": mig}
