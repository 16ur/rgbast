from fastapi import FastAPI
from fastapi.security import HTTPBearer
from app.api import palettes, users, auth
from app.scripts.init_db import create_db_and_tables

app = FastAPI(title="RGBAST API")
create_db_and_tables()

bearer_scheme = HTTPBearer()
# si le savoir est une arme, alors le savoir est une arme
app.include_router(users.router, tags=["users"])
app.include_router(auth.router, tags=["auth"])
app.include_router(palettes.router, tags=["palettes"])


@app.get("/")
async def root():
    return {"message": "Welcome to RGBAST ! If cou can read this, you can read this."}
