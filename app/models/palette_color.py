from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select
from datetime import datetime

class Palette_Color(SQLModel, table=True):
    id: int = Field(primary_key=True, nullable=False),
