from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import fastapi_blog


app = FastAPI()
# Existing example posts use extra frontmatter fields and raw HTML,
# so strict validation and HTML sanitization are disabled here.
app = fastapi_blog.add_blog_to_fastapi(
    app, strict_frontmatter=False, sanitize_html=False
)
app = fastapi_blog.add_editor_to_app(app, strict=False)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index() -> dict:
    return {
        "message": "Blog at /blog, editor API at /api/posts (see /docs)",
        "blog": "http://localhost:8000/blog",
        "api_docs": "http://localhost:8000/docs",
    }
