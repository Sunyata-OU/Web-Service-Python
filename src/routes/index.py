from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.templating import _TemplateResponse
from src.templates import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> _TemplateResponse:
    """Index page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Title",
        },
    )
