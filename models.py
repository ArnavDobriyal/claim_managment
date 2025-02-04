import uuid
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, Session
from database import Base, AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select



class Policyholder(Base):
    __tablename__ = "policyholders"
    id = Column(Integer, primary_key=True, unique=True)  # Remove `default=`
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    policies = relationship("Policy", back_populates="policyholder", cascade="all, delete")
    claims = relationship("Claim", back_populates="policyholder", cascade="all, delete")


class Policy(Base):
    __tablename__ = "policies"
    policy_id = Column(Integer, primary_key=True, autoincrement=True)
    policyholder_id = Column(Integer, ForeignKey("policyholders.id"), nullable=False)
    coverage = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    
    policyholder = relationship("Policyholder", back_populates="policies")
    claims = relationship("Claim", back_populates="policy", cascade="all, delete")

class Claim(Base):
    __tablename__ = "claims"
    claim_id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(Integer, ForeignKey("policies.policy_id"), nullable=False)
    policyholder_id = Column(Integer, ForeignKey("policyholders.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    
    policy = relationship("Policy", back_populates="claims")
    policyholder = relationship("Policyholder", back_populates="claims")
