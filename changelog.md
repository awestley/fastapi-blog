# Changelog

## 0.7.0 - 2025-09-18

**Major Update: Modernized Dependencies and Development Environment**

* Updated Python requirement to 3.12+ (added Python 3.13 support)
* Updated all dependencies to latest versions:
  - FastAPI: 0.109.2 → 0.115.0+
  - Uvicorn: 0.27.1 → 0.35.0+
  - Ruff: 0.2.2 → 0.8.0+
  - MyPy: 1.8.0 → 1.13.0+
  - Pytest: 8.0.1 → 8.3.0+
  - Coverage: 7.4.1 → 7.6.0+
* Modernized ruff configuration with latest linting rules
* Added comprehensive GitHub Actions CI/CD workflow
* Added security scanning with safety and bandit
* Improved development tooling and code quality checks
* Full compatibility with Python 3.13.7

## 0.6.0 - 2023-03-24

* Remove staticfiles and encourage self config. PR [#40](https://github.com/pydanny/fastapi-blog/pull/40) by [@pydanny](https://github.com/pydanny).
* Posts with zero tags no longer generate errors. PR [#39](https://github.com/pydanny/fastapi-blog/pull/39) by [@pydanny](https://github.com/pydanny).

## 0.6.0 - 2023-03-24

* Add tutorial for pages. PR [#36](https://github.com/pydanny/fastapi-blog/pull/36) by [@pydanny](https://github.com/pydanny).
* Add tutorial for blog entries. PR [#35](https://github.com/pydanny/fastapi-blog/pull/35) by [@pydanny](https://github.com/pydanny).
* Allow for control over if statics are mounted. PR [#31](https://github.com/pydanny/fastapi-blog/pull/31) by [@pydanny](https://github.com/pydanny).
* Fix markdown issue with pygments (#22). Thanks to @pydanny
* Add header permalinks to rendered markdown (#22). Thanks to @pydanny

## 0.5.0 - 2023-03-08

- Added continuous integration (#19). Thanks to @pydanny
- Remove RSS feed as it needs a complete rebuild. Thanks to @pydanny
- Use uv for local installation. Thanks to @pydanny
- Inform PyPI the changelog is at changelog.md, not CHANGELOG. Thanks to @pydanny

## 0.4.0 - 2024-03-01

- Document how to use pages (#3) and added sample `about.md` page. Thanks to @pydanny
- Standardize path arguments with `_id` suffix (#7) Thanks to @pydanny
- Initial tests for helpers.py, for #10. Thanks to @pydanny!
- Remove hardcoded favorites list, issue #13. Thanks to @pydanny!

## 0.3.0 - 2024-02-29

- Docker thanks to @audreyfeldroy!
- Installation and usage instructions for localdev and docker. Thanks to @audreyfeldroy!
- Made templates overloadable (issue #2) thanks to @pydanny!
- Added more example apps thanks to @pydanny!

## 0.2.0 - 2024-02-25

- Cleanup

## 0.1.0 - 2024-02-25

- Inception
