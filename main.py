import logging
import os

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import auth, users, groups, products, ws

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

os.makedirs("static", exist_ok=True)

# Namapování složky
app.mount("/static", StaticFiles(directory="static"), name="static")

master_router = APIRouter(prefix="/api")

master_router.include_router(auth.router)
master_router.include_router(users.router)
master_router.include_router(groups.router)
master_router.include_router(products.router)

app.include_router(ws.ws_router)
app.include_router(master_router)

@app.get("/")
def read_root():
    return {"message": "Backend aukčního systému běží!"}