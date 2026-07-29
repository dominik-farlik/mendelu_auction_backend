import logging

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, users, groups

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="MENDELU Auction API")

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

master_router = APIRouter(prefix="/api")

master_router.include_router(auth.router)
master_router.include_router(users.router)
master_router.include_router(groups.router)

app.include_router(master_router)

@app.get("/")
def read_root():
    return {"message": "Backend aukčního systému běží!"}