from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from .videos import router as videos_router
from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Retry DB init to handle startup timing and DNS delays in containers.
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://vcm-52418.vm.duke.edu:5173",
        "http://vcm-52527.vm.duke.edu:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def read_root():
    return {"status":"ok","service":"videos"}
    
app.include_router(videos_router)