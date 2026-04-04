from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.upload import router as upload_router
from backend.api.chat import router as chat_router
from backend.api.delete import router as delete_router




app = FastAPI(
    title="Document Intelligence Platform",
    description="Privacy-first document summarization and Q&A",
    version="0.1.0"
)

# Allow frontend (Dash) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(delete_router)



@app.get("/")
def health_check():
    return {"status": "ok", "message": "Backend is running"}
# @app.get("/")
# def health_check():
#     print("ROOT HIT")
#     return "BACKEND IS ALIVE"

