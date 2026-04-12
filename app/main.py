from fastapi import FastAPI

app = FastAPI()

# si le savoir est une arme, alors le savoir est une arme
@app.get("/")
async def root():
    return {"message": "Welcome to RGBAST ! If cou can read this, you can read this."}
