import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.api import auth,workspaces,documents,chat,compare,datasets,google_auth

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(name)s %(message)s")
app=FastAPI(title="Document & Data Intelligence Platform",version="2.0.0")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
for r in (auth.router,google_auth.router,workspaces.router,documents.router,chat.router,compare.router,datasets.router): app.include_router(r)

@app.get("/health")
def health(): return {"status":"ok"}
