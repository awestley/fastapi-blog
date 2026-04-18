import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_blog import add_blog_to_fastapi, add_editor_to_app, helpers


@pytest.fixture
def app_dir(tmp_path, monkeypatch):
    (tmp_path / "posts").mkdir()
    (tmp_path / "pages").mkdir()
    monkeypatch.chdir(tmp_path)
    helpers.list_posts.cache_clear()
    yield tmp_path
    helpers.list_posts.cache_clear()


@pytest.fixture
def client(app_dir):
    app = FastAPI()
    app = add_blog_to_fastapi(app, prefix="blog")
    app = add_editor_to_app(app)
    return TestClient(app)


@pytest.fixture
def loose_client(app_dir):
    app = FastAPI()
    app = add_blog_to_fastapi(
        app, prefix="blog", strict_frontmatter=False, sanitize_html=False
    )
    app = add_editor_to_app(app, strict=False)
    return TestClient(app)


VALID_PAYLOAD = {
    "frontmatter": {
        "title": "Hello World",
        "date": "2026-04-18",
        "published": True,
        "tags": ["greeting"],
        "description": "First post",
    },
    "content": "# Hello\n\nThis is a test post.",
}


def test_create_post_success(client, app_dir):
    response = client.post("/api/posts/create/hello-world", json=VALID_PAYLOAD)
    assert response.status_code == 201
    assert response.json() == {"slug": "hello-world", "status": "created"}
    assert (app_dir / "posts" / "hello-world.md").is_file()


def test_create_post_conflict(client, app_dir):
    (app_dir / "posts" / "hello-world.md").write_text(
        "---\ntitle: x\ndate: '2026-01-01'\n---\nbody\n"
    )
    response = client.post("/api/posts/create/hello-world", json=VALID_PAYLOAD)
    assert response.status_code == 409


def test_create_post_invalid_slug(client):
    response = client.post("/api/posts/create/Bad_Slug", json=VALID_PAYLOAD)
    assert response.status_code == 422


def test_create_post_path_traversal(client):
    response = client.post(
        "/api/posts/create/..%2F..%2Fetc%2Fpasswd", json=VALID_PAYLOAD
    )
    assert response.status_code in {404, 422}


def test_create_post_invalid_frontmatter(client):
    bad = {"frontmatter": {"title": "x"}, "content": "body"}  # missing date
    response = client.post("/api/posts/create/missing-date", json=bad)
    assert response.status_code == 422


def test_create_post_strict_rejects_extras(client):
    bad = {
        "frontmatter": {**VALID_PAYLOAD["frontmatter"], "image": "/x.png"},
        "content": "body",
    }
    response = client.post("/api/posts/create/with-extra", json=bad)
    assert response.status_code == 422


def test_create_post_loose_accepts_extras(loose_client, app_dir):
    body = {
        "frontmatter": {**VALID_PAYLOAD["frontmatter"], "image": "/x.png"},
        "content": "body",
    }
    response = loose_client.post("/api/posts/create/with-extra", json=body)
    assert response.status_code == 201
    saved = (app_dir / "posts" / "with-extra.md").read_text()
    assert "image: /x.png" in saved


def test_get_raw_success(client, app_dir):
    client.post("/api/posts/create/hello-world", json=VALID_PAYLOAD)
    response = client.get("/api/posts/hello-world/raw")
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "hello-world"
    assert body["frontmatter"]["title"] == "Hello World"
    assert "# Hello" in body["content"]


def test_get_raw_not_found(client):
    response = client.get("/api/posts/missing/raw")
    assert response.status_code == 404


def test_update_post_success(client, app_dir):
    client.post("/api/posts/create/hello-world", json=VALID_PAYLOAD)
    updated = {
        **VALID_PAYLOAD,
        "frontmatter": {**VALID_PAYLOAD["frontmatter"], "title": "Updated"},
        "content": "new body",
    }
    response = client.put("/api/posts/update/hello-world", json=updated)
    assert response.status_code == 200
    saved = (app_dir / "posts" / "hello-world.md").read_text()
    assert "title: Updated" in saved
    assert "new body" in saved


def test_update_post_not_found(client):
    response = client.put("/api/posts/update/missing", json=VALID_PAYLOAD)
    assert response.status_code == 404


def test_delete_post_success(client, app_dir):
    client.post("/api/posts/create/hello-world", json=VALID_PAYLOAD)
    response = client.delete("/api/posts/delete/hello-world")
    assert response.status_code == 200
    assert not (app_dir / "posts" / "hello-world.md").exists()


def test_delete_post_not_found(client):
    response = client.delete("/api/posts/delete/missing")
    assert response.status_code == 404


def test_create_invalidates_cache(client, app_dir):
    # populate cache with empty list
    assert helpers.list_posts(posts_dirname="posts") == ()
    client.post("/api/posts/create/hello-world", json=VALID_PAYLOAD)
    posts = helpers.list_posts(posts_dirname="posts")
    assert len(posts) == 1
    assert posts[0]["title"] == "Hello World"


def test_blog_index_after_create(client):
    client.post("/api/posts/create/hello-world", json=VALID_PAYLOAD)
    response = client.get("/blog/posts")
    assert response.status_code == 200
    assert "Hello World" in response.text


def test_ui_list_empty(client):
    response = client.get("/admin/editor/")
    assert response.status_code == 200
    assert "No posts yet" in response.text


def test_ui_list_shows_posts(client):
    client.post("/api/posts/create/hello-world", json=VALID_PAYLOAD)
    response = client.get("/admin/editor/")
    assert response.status_code == 200
    assert "Hello World" in response.text
    assert "hello-world" in response.text


def test_ui_new_page(client):
    response = client.get("/admin/editor/new")
    assert response.status_code == 200
    assert "easymde" in response.text.lower()
    assert 'id="slug"' in response.text


def test_ui_edit_page_prefills(client):
    client.post("/api/posts/create/hello-world", json=VALID_PAYLOAD)
    response = client.get("/admin/editor/hello-world")
    assert response.status_code == 200
    assert "Hello World" in response.text
    assert "greeting" in response.text
    assert "readonly" in response.text


def test_ui_edit_404_for_missing(client):
    response = client.get("/admin/editor/does-not-exist")
    assert response.status_code == 404


def test_ui_disabled(app_dir):
    from fastapi import FastAPI

    app = FastAPI()
    app = add_blog_to_fastapi(app, prefix="blog")
    app = add_editor_to_app(app, ui=False)
    ui_client = TestClient(app)
    response = ui_client.get("/admin/editor/")
    assert response.status_code == 404
