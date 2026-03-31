# fastapi-nimda Plan

## Goal

Move `fastapi-nimda` from a functional prototype to a packageable, documented, and testable FastAPI admin library.

This plan is organized in the order that reduces risk first:

1. stabilize the package surface
2. improve structure and packaging
3. add tests around current behavior
4. expand features only after the core is reliable

## Phase 1: Define the Package Boundary

### Objectives

- decide what the public API is
- make import paths stable
- document what is supported and what is not

### Tasks

- define the intended top-level exports in `fastapi_nimda/__init__.py`
- decide whether the main public app class should be named `FastAPINimda`, `AdminApp`, or something similar and keep the naming consistent
- document the required integration flow:
  - create FastAPI app
  - create SQLAlchemy engine
  - create admin app
  - register models
- document supported ORM patterns and current limitations
- decide whether SQLModel is a first-class target or only a compatible layer on top of SQLAlchemy

### Deliverables

- cleaned public package exports
- documented supported use cases
- documented unsupported cases

## Phase 2: Restructure the Repository for Packaging

### Objectives

- make the repository look like a library rather than an experiment folder
- separate example code from package code
- make publishing and installation easier

### Recommended Target Structure

```text
fastapi-nimda/
├── fastapi_nimda/
│   ├── __init__.py
│   ├── app.py
│   ├── admin.py
│   ├── routing.py
│   ├── depends.py
│   ├── types.py
│   ├── constants.py
│   ├── helpers.py
│   ├── messaging.py
│   ├── paginator.py
│   ├── widgets.py
│   ├── templating/
│   ├── templates/
│   └── static/
├── examples/
│   ├── sqlmodel_demo/
│   │   └── main.py
│   └── sqlalchemy_demo/
│       └── main.py
├── tests/
│   ├── test_registration.py
│   ├── test_routes.py
│   ├── test_forms.py
│   └── test_relationships.py
├── docs/
│   ├── architecture.md
│   ├── roadmap.md
│   └── limitations.md
├── README.md
├── pyproject.toml
└── uv.lock
```

### Tasks

- move `main.py` and `main2.py` into `examples/`
- move `archetecture.md` into `docs/architecture.md` in a later cleanup pass
- remove or archive scratch files such as `test.py`, `admin copy.py`, `base copy.html`, and `table copy.html`
- decide whether sample databases should live in version control
- ensure package data includes templates and static assets during build/publish
- add classifiers, license, authorship, URLs, and a real description to `pyproject.toml`
- add build settings so wheel/sdist packaging is explicit and repeatable

### Deliverables

- cleaner repository layout
- example apps isolated from library code
- package metadata ready for publishing

## Phase 3: Split Internal Responsibilities

### Objectives

- reduce the amount of logic living inside `ModelAdmin`
- improve maintainability and testability

### Suggested Internal Refactor

Break `ModelAdmin` responsibilities into collaborators:

- `inspection.py`
  - model introspection
  - field classification
  - relationship validation
- `queries.py`
  - list/select/update/delete/insert statement construction
- `forms.py`
  - form assembly
  - input normalization
  - validation rules
- `registry.py`
  - registered resource storage
  - identity/slug generation
- `services.py`
  - write operations
  - error mapping
  - transaction handling

`ModelAdmin` can remain the public extension point while delegating work internally.

### Tasks

- identify logic in `admin.py` that is framework-internal rather than user-configurable
- extract stable helper objects without changing external behavior
- keep route handlers thin by moving write flows into service functions
- centralize ORM and DB error normalization

### Deliverables

- smaller units with clearer ownership
- easier testing around isolated behavior

## Phase 4: Stabilize URL and Registry Design

### Objectives

- make admin URLs deterministic
- avoid fragile numeric identities

### Tasks

- replace generated numeric keys like `"1"`, `"2"` with stable slugs
- default slug candidates:
  - explicit `ModelAdmin.slug`
  - model table name
  - model class name lowercased
- validate uniqueness during registration
- ensure the slug is what appears in URLs and templates

### Deliverables

- predictable URLs
- safer registration behavior

## Phase 5: Build a Real Test Suite

### Objectives

- protect current behavior before feature growth
- make refactoring safe

### Priority Test Areas

- registration validation
- field and attribute validation
- list rendering behavior
- add/edit/view/delete route behavior
- primary key handling
- foreign-key relationship handling
- widget rendering and form binding
- error rendering after invalid writes

### Suggested Test Stack

- `pytest`
- FastAPI `TestClient`
- temporary SQLite databases

### Tasks

- create shared fixtures for app, engine, and models
- test both SQLAlchemy and SQLModel examples if both are meant to be supported
- add regression tests for every currently known limitation or edge case

### Deliverables

- baseline confidence for refactors
- regression safety net

## Phase 6: Improve Documentation

### Objectives

- make the project understandable to new users
- reduce hidden assumptions

### README should include

- project overview
- why this exists
- installation
- quickstart example
- supported model patterns
- screenshots or minimal UI examples
- limitations
- development workflow

### Additional docs worth having

- `docs/limitations.md`
- `docs/customization.md`
- `docs/widgets.md`
- `docs/relationships.md`
- `docs/release-process.md`

### Deliverables

- usable onboarding docs
- lower maintenance cost from fewer implicit decisions

## Phase 7: Hardening and Behavior Corrections

### Objectives

- remove prototype assumptions that will create bugs later

### Tasks

- review composite primary key support end to end
- review many-to-many behavior and decide whether to support or explicitly reject it
- review file upload fields and either support them or block them with clear messaging
- replace brittle error parsing with more structured handling where possible
- review session lifecycle and transaction boundaries
- review typing across the package
- audit naming consistency, including `FastAPINimda` versus package branding

### Deliverables

- fewer hidden edge cases
- more predictable runtime behavior

## Phase 8: Good-to-Have Features

These should come after packaging, tests, and API stabilization.

### Admin UX Features

- search box on list pages
- column sorting from the UI
- list filters for common field types
- bulk actions beyond delete
- inline relationship display for foreign-key relations
- breadcrumbs and clearer model navigation
- better empty states and validation feedback

### Customization Features

- model-level permissions hooks
- custom form field overrides
- custom list/query hooks
- pre-save and post-save hooks
- custom action buttons per model
- configurable labels, icons, and navigation grouping

### Data Features

- many-to-many editing support
- composite key support where practical
- richer foreign-key widgets with search/autocomplete
- soft-delete aware admin behavior
- audit/history view for changes

### Operational Features

- proper release/versioning workflow
- changelog management
- CI for tests and linting
- package publishing automation

## Phase 9: Packaging and Release Readiness

### Objectives

- make the project installable and publishable with confidence

### Tasks

- verify package data inclusion for templates/static assets
- add semantic versioning policy
- add CI checks for lint, tests, and build
- build and inspect wheel/sdist locally
- test installation into a clean virtual environment
- publish an initial pre-1.0 release only after docs and tests exist

### Deliverables

- reliable package artifacts
- repeatable release process

## Suggested Execution Order

1. define public API and supported scope
2. restructure repository for packaging
3. add tests around current behavior
4. refactor internals behind the same API
5. stabilize slugs and route identities
6. improve docs
7. harden edge cases
8. add convenience features
9. ship a pre-1.0 package

## Immediate Next Actions

If this were executed as a short-term roadmap, the highest-value next steps would be:

1. clean `pyproject.toml` and package exports
2. move example apps out of the repo root
3. create `tests/` and lock in current CRUD behavior
4. replace numeric resource identities with stable slugs
5. rewrite the README into a real quickstart and limitations guide
