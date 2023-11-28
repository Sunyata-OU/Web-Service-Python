from typing import Dict
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.routes import index, s3
from src.logger import logger
from src.utils import get_current_date_time

app = FastAPI()
app.mount("/static", StaticFiles(directory="src/static"), name="static")
app.include_router(index.router)
app.include_router(s3.router)
logger.info("App started.")


@app.get("/test", response_model=Dict[str, str])
async def test() -> Dict[str, str]:
    return {
        "result": "success",
        "msg": f"It works!{get_current_date_time()}",
    }
