import pathlib
from typing import Any

import yaml
from fastapi import APIRouter, FastAPI, HTTPException, Path, status
from fastapi.responses import JSONResponse

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
) -> FastAPI:
    router = APIRouter(prefix=prefix, tags=["editor"])
    Payload = payload_model(strict)
    slug_path = Path(pattern=SLUG_PATTERN, max_length=100)

    @router.get("/{slug}/raw")
    async def get_raw(slug: str = slug_path) -> dict[str, Any]:
        path = _post_path(slug, posts_dirname)
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post '{slug}' not found",
            )
        data = _parse_file(path)
        return {"slug": slug, **data}

    @router.post("/create/{slug}", status_code=status.HTTP_201_CREATED)
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

    @router.put("/update/{slug}")
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

    @router.delete("/delete/{slug}")
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

    app.include_router(router)
    return app
