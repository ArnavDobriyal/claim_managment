from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models import Base
from database import engine, AsyncSessionLocal
from pydantic import BaseModel
import crud
import uvicorn

app = FastAPI()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class PolicyholderCreate(BaseModel):
    name: str
    email: str

class PolicyholderUpdate(BaseModel):
    name: str
    email: str

class PolicyCreate(BaseModel):
    coverage: float
    status: str

class PolicyUpdate(BaseModel):
    coverage: float
    status: str

class ClaimCreate(BaseModel):
    amount: float

class ClaimUpdate(BaseModel):
    status: str

@app.post("/policyholders/")
async def create_policyholder(data: PolicyholderCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_policyholder(db, data.name, data.email)

@app.put("/policyholders/{policyholder_id}")
async def update_policyholder(policyholder_id: int, data: PolicyholderUpdate, db: AsyncSession = Depends(get_db)):
    return await crud.update_policyholder(db, policyholder_id, data.name, data.email)

@app.post("/policyholders/{policyholder_id}/policies/")
async def create_policy(policyholder_id: int, data: PolicyCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_policy(db, policyholder_id, data.coverage, data.status)

@app.put("/policyholders/{policyholder_id}/policies/{policy_id}")
async def update_policy(policyholder_id: int, policy_id: int, data: PolicyUpdate, db: AsyncSession = Depends(get_db)):
    return await crud.update_policy(db, policyholder_id, policy_id, data.coverage, data.status)

@app.delete("/policyholders/{policyholder_id}/policies/{policy_id}")
async def delete_policy(policyholder_id: int, policy_id: int, db: AsyncSession = Depends(get_db)):
    return await crud.delete_policy(db, policyholder_id, policy_id)

@app.post("/policyholders/{policyholder_id}/claims/{policy_id}")
async def create_claim(policyholder_id: int, policy_id: int, data: ClaimCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_claim(db, policyholder_id, policy_id, data.amount)

@app.put("/policyholders/{policyholder_id}/claims/{policy_id}/{claim_id}")
async def update_claim_status(
    policyholder_id: int, policy_id: int, claim_id: int, data: ClaimUpdate, db: AsyncSession = Depends(get_db)
):
    return await crud.update_claim_status(db, policyholder_id, policy_id, claim_id, data.status)

@app.delete("/policyholders/{policyholder_id}/claims/{policy_id}/{claim_id}")
async def delete_claim(policyholder_id: int, policy_id: int, claim_id: int, db: AsyncSession = Depends(get_db)):
    return await crud.delete_claim(db, policyholder_id, policy_id, claim_id)

@app.delete("/policyholders/{policyholder_id}")
async def delete_policyholder(policyholder_id: int, db: AsyncSession = Depends(get_db)):
    return await crud.delete_policyholder(db, policyholder_id)

@app.get("/")
def read_root():
    return {"message": "Service is running"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
