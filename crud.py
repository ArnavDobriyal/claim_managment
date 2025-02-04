from sqlalchemy import func, select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import Policyholder, Policy, Claim
from fastapi import HTTPException
import uuid
import re

def validate_email(email: str):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email):
        raise HTTPException(status_code=400, detail="Invalid email format")

def validate_coverage(coverage: float):
    if coverage <= 0:
        raise HTTPException(status_code=400, detail="Coverage must be greater than zero")

def validate_amount(amount: float):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Claim amount must be greater than zero")

async def generate_policyholder_id(db: AsyncSession) -> int:
    while True:
        new_id = uuid.uuid4().int & ((1 << 31) - 1)
        result = await db.execute(select(Policyholder).filter_by(id=new_id))
        if not result.scalar_one_or_none():
            return new_id

async def get_policyholder(db: AsyncSession, policyholder_id: int):
    result = await db.execute(select(Policyholder).where(Policyholder.id == policyholder_id))
    return result.scalar_one_or_none()

async def create_policyholder(db: AsyncSession, name: str, email: str):
    validate_email(email)
    new_id = await generate_policyholder_id(db)
    policyholder = Policyholder(id=new_id, name=name, email=email)
    db.add(policyholder)
    await db.commit()
    await db.refresh(policyholder)
    return policyholder

async def create_policy(db: AsyncSession, policyholder_id: int, coverage: float, status: str):
    validate_coverage(coverage)
    max_policy_id = await db.execute(select(func.max(Policy.policy_id)).where(Policy.policyholder_id == policyholder_id))
    new_policy_id = (max_policy_id.scalar() or 0) + 1
    policy = Policy(policyholder_id=policyholder_id, policy_id=new_policy_id, coverage=coverage, status=status)
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy

async def create_claim(db: AsyncSession, policyholder_id: int, policy_id: int, amount: float):
    validate_amount(amount)
    total_claims = await db.execute(
        select(func.sum(Claim.amount)).where(Claim.policyholder_id == policyholder_id, Claim.policy_id == policy_id, Claim.status != "rejected")
    )
    total = total_claims.scalar() or 0
    policy_result = await db.execute(select(Policy).where(Policy.policy_id == policy_id, Policy.policyholder_id == policyholder_id))
    policy = policy_result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    if total + amount > policy.coverage:
        raise HTTPException(status_code=400, detail="Claim exceeds available coverage")
    max_claim_id = await db.execute(select(func.max(Claim.claim_id)).where(Claim.policyholder_id == policyholder_id, Claim.policy_id == policy_id))
    new_claim_id = (max_claim_id.scalar() or 0) + 1
    status = "flagged" if amount > 10000 else "pending"
    claim = Claim(policyholder_id=policyholder_id, policy_id=policy_id, claim_id=new_claim_id, amount=amount, status=status)
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return claim

async def update_claim_status(db: AsyncSession, policyholder_id: int, policy_id: int, claim_id: int, status: str):
    result = await db.execute(
        update(Claim)
        .where(
            Claim.policyholder_id == policyholder_id,
            Claim.policy_id == policy_id,
            Claim.claim_id == claim_id
        )
        .values(status=status)
        .returning(
            Claim.policyholder_id, Claim.policy_id, Claim.claim_id, Claim.amount, Claim.status
        )
    )
    updated_claim = result.fetchone()
    if not updated_claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    await db.commit()

    # Convert Row to Dictionary
    return {
        "policyholder_id": updated_claim.policyholder_id,
        "policy_id": updated_claim.policy_id,
        "claim_id": updated_claim.claim_id,
        "amount": updated_claim.amount,
        "status": updated_claim.status
    }

async def delete_policyholder(db: AsyncSession, policyholder_id: int):
    policyholder = await db.get(Policyholder, policyholder_id)
    if not policyholder:
        raise HTTPException(status_code=404, detail="Policyholder not found")
    await db.delete(policyholder)
    await db.commit()
    return {"message": "Policyholder deleted successfully"}

async def update_policy(db: AsyncSession, policyholder_id: int, policy_id: int, coverage: float, status: str):
    validate_coverage(coverage)
    policy = await db.execute(select(Policy).where(Policy.policy_id == policy_id, Policy.policyholder_id == policyholder_id))
    policy = policy.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy.coverage = coverage
    policy.status = status
    await db.commit()
    await db.refresh(policy)
    return policy

async def delete_claim(db: AsyncSession, policyholder_id: int, policy_id: int, claim_id: int):
    result = await db.execute(delete(Claim).where(Claim.policyholder_id == policyholder_id, Claim.policy_id == policy_id, Claim.claim_id == claim_id).returning(Claim.claim_id))
    deleted_claim = result.scalar_one_or_none()
    if not deleted_claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    await db.commit()
    return {"message": f"Claim {claim_id} deleted successfully"}

async def delete_policy(db: AsyncSession, policyholder_id: int, policy_id: int):
    policy = await db.get(Policy, policy_id)
    if not policy or policy.policyholder_id != policyholder_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    await db.execute(delete(Claim).where(Claim.policyholder_id == policyholder_id, Claim.policy_id == policy_id))
    await db.execute(delete(Policy).where(Policy.policyholder_id == policyholder_id, Policy.policy_id == policy_id))
    await db.commit()
    return {"message": f"Policy {policy_id} and related claims deleted successfully"}

async def update_policyholder(db: AsyncSession, policyholder_id: int, name: str, email: str):
    policyholder = await db.get(Policyholder, policyholder_id)
    if not policyholder:
        raise HTTPException(status_code=404, detail="Policyholder not found")
    policyholder.name = name
    policyholder.email = email
    await db.commit()
    return policyholder