import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import auth, users, groups, products, ws
from utils.auction_end_checker import auction_ender_task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(auction_ender_task())
    yield
    task.cancel()

app = FastAPI(title="MENDELU Auction API", lifespan=lifespan)

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