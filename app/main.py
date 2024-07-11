from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from .routers import router
from .database import engine
from .cashe import redis

app = FastAPI()

app.include_router(router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
async def startup_event():
    print("Starting up...")

    try:
        await redis.ping()
        print("Redis connected.")
    except Exception as e:
        print(f"Redis connection failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down...")
    await engine.dispose()
    print("Database connection closed.")

    await redis.close()
    await redis.wait_closed()
    print("Redis connection closed.")
