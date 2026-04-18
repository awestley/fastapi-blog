import pathlib
from typing import Any

import jinja2
import yaml
from fastapi import APIRouter, FastAPI, HTTPException, Path, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from . import helpers
from .models import (
    SLUG_PATTERN,
    LoosePostPayload,
    StrictPostPayload,
    is_valid_slug,
    payload_model,
)


def _post_path(slug: str, posts_dirname: str) -> pathlib.Path:
    if not is_valid_slug(slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid slug. Allowed: lowercase letters, digits, hyphens (max 100).",
        )
    return pathlib.Path(posts_dirname) / f"{slug}.md"


def _serialize(payload: StrictPostPayload | LoosePostPayload) -> str:
    fm_dump = payload.frontmatter.model_dump(exclude_none=True)
    fm_yaml = yaml.safe_dump(fm_dump, sort_keys=False, allow_unicode=True)
    return f"---\n{fm_yaml}---\n\n{payload.content.rstrip()}\n"


def _parse_file(path: pathlib.Path) -> dict[str, Any]:
    raw = path.read_text()
    parts = raw.split("---")
    if len(parts) < 3:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Post file is malformed: {path.name}",
        )
    try:
        frontmatter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid YAML in {path.name}: {exc}",
        ) from exc
    content = "---".join(parts[2:]).lstrip("\n")
    return {"frontmatter": frontmatter, "content": content}


def add_editor_to_app(
    app: FastAPI,
    prefix: str = "/api/posts",
    posts_dirname: str = "posts",
    strict: bool = True,
    ui: bool = True,
    ui_prefix: str = "/admin/editor",
) -> FastAPI:
    api_router = APIRouter(prefix=prefix, tags=["editor"])
    Payload = payload_model(strict)
    slug_path = Path(pattern=SLUG_PATTERN, max_length=100)

    @api_router.get("/{slug}/raw")
    async def get_raw(slug: str = slug_path) -> dict[str, Any]:
        path = _post_path(slug, posts_dirname)
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post '{slug}' not found",
            )
        data = _parse_file(path)
        return {"slug": slug, **data}

    @api_router.post("/create/{slug}", status_code=status.HTTP_201_CREATED)
    async def create_post(
        payload: Payload,  # type: ignore[valid-type]
        slug: str = slug_path,
    ) -> dict[str, str]:
        path = _post_path(slug, posts_dirname)
        if path.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Post '{slug}' already exists",
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_serialize(payload))
        helpers.list_posts.cache_clear()
        return {"slug": slug, "status": "created"}

    @api_router.put("/update/{slug}")
    async def update_post(
        payload: Payload,  # type: ignore[valid-type]
        slug: str = slug_path,
    ) -> dict[str, str]:
        path = _post_path(slug, posts_dirname)
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post '{slug}' not found",
            )
        path.write_text(_serialize(payload))
        helpers.list_posts.cache_clear()
        return {"slug": slug, "status": "updated"}

    @api_router.delete("/delete/{slug}")
    async def delete_post(slug: str = slug_path) -> JSONResponse:
        path = _post_path(slug, posts_dirname)
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post '{slug}' not found",
            )
        path.unlink()
        helpers.list_posts.cache_clear()
        return JSONResponse({"slug": slug, "status": "deleted"})

    app.include_router(api_router)

    if ui:
        _add_ui_routes(
            app,
            api_prefix=prefix,
            ui_prefix=ui_prefix,
            posts_dirname=posts_dirname,
            strict=strict,
        )

    return app


def _add_ui_routes(
    app: FastAPI,
    api_prefix: str,
    ui_prefix: str,
    posts_dirname: str,
    strict: bool,
) -> None:
    env = jinja2.Environment(
        loader=jinja2.PackageLoader("fastapi_blog", "templates"),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )
    templates = Jinja2Templates(env=env)
    ui_router = APIRouter(prefix=ui_prefix, tags=["editor-ui"])
    slug_path = Path(pattern=SLUG_PATTERN, max_length=100)

    def _context(**extra: Any) -> dict[str, Any]:
        return {"admin_prefix": ui_prefix, "api_prefix": api_prefix, **extra}

    @ui_router.get("/", response_class=HTMLResponse)
    async def editor_index(request: Request) -> Any:
        posts = helpers.list_posts(
            posts_dirname=posts_dirname, strict=strict, published=True
        )
        drafts = helpers.list_posts(
            posts_dirname=posts_dirname, strict=strict, published=False
        )
        return templates.TemplateResponse(
            request=request,
            name="admin/list.html",
            context=_context(posts=list(posts) + list(drafts)),
        )

    @ui_router.get("/new", response_class=HTMLResponse)
    async def editor_new(request: Request) -> Any:
        return templates.TemplateResponse(
            request=request,
            name="admin/edit.html",
            context=_context(
                is_new=True,
                slug="",
                frontmatter={"title": "", "date": "", "tags": [], "published": False},
                content="",
            ),
        )

    @ui_router.get("/{slug}", response_class=HTMLResponse)
    async def editor_edit(request: Request, slug: str = slug_path) -> Any:
        path = _post_path(slug, posts_dirname)
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post '{slug}' not found",
            )
        data = _parse_file(path)
        return templates.TemplateResponse(
            request=request,
            name="admin/edit.html",
            context=_context(
                is_new=False,
                slug=slug,
                frontmatter=data["frontmatter"],
                content=data["content"],
            ),
        )

    app.include_router(ui_router)
