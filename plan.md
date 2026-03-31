# fastapi-nimda Plan

## Goal

Move `fastapi-nimda` from a functional prototype to a packageable, documented, and testable FastAPI admin library.

This plan is organized in the order that reduces risk first:

1. stabilize the package surface
2. improve structure and packaging
3. add tests around current behavior
4. expand features only after the core is reliable

## DONE Phase 1: Define the Package Boundary

Status: complete

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

Completed so far:

- define the intended top-level exports in `fastapi_nimda/__init__.py`
- decide that `FastAPINimda` is the canonical public app class name and `Admin` is a compatibility alias
- document the required integration flow in `README.md`
- document supported ORM patterns and current limitations in `README.md`
- decide that SQLAlchemy declarative models are the core support target and SQLModel table models are a first-class supported integration when they fit the same ORM shape

### Deliverables

- cleaned public package exports
- documented supported use cases
- documented unsupported cases

## DONE Phase 2: Restructure the Repository for Packaging

Status: complete

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

Completed so far:

- move `main.py` and `main2.py` into `examples/`
- move `archetecture.md` into `docs/architecture.md`
- archive scratch files such as `test.py`, `admin copy.py`, `base copy.html`, and `table copy.html`
- decide that generated sample databases should not live at the repository root and should be ignored from version control going forward
- ensure package data includes templates and static assets during build/publish
- add classifiers, license, authorship, and a real description to `pyproject.toml`
- add build settings so wheel/sdist packaging is explicit and repeatable

Note:

- project URLs were not added because there is no configured upstream repository URL in local git metadata yet

### Deliverables

- cleaner repository layout
- example apps isolated from library code
- package metadata ready for publishing

## DONE Phase 3: Split Internal Responsibilities

Status: complete

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

Completed so far:

- extract model inspection into `fastapi_nimda/inspection.py`
- extract query construction into `fastapi_nimda/queries.py`
- extract form assembly and validation into `fastapi_nimda/forms.py`
- extract registry behavior into `fastapi_nimda/registry.py`
- extract write flows into `fastapi_nimda/services.py`
- reduce `fastapi_nimda/admin.py` to the public configuration facade over internal collaborators
- keep route handlers thinner by delegating add and edit write operations to the service layer
- keep the public `ModelAdmin` API intact while moving framework-internal behavior behind it

### Deliverables

- smaller units with clearer ownership
- easier testing around isolated behavior

## DONE Phase 4: Stabilize URL and Registry Design

Status: complete

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

Completed so far:

- replace generated numeric keys with deterministic registry slugs
- support slug selection in this order:
  - explicit `ModelAdmin.slug`
  - model table name
  - model class name lowercased and slugified
- validate slug uniqueness during registration
- propagate the chosen slug into registered resources and modeladmin instances
- keep the slug as the identity used by routes, dependencies, and templates

### Deliverables

- predictable URLs
- safer registration behavior

## Phase 5: Build a Real Test Suite

Status: not started

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

Status: in progress

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

## DONE Phase 7: Hardening and Behavior Corrections

Status: complete

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

Completed so far:

- explicitly reject composite primary keys during model inspection with a package-level configuration error
- explicitly reject unsupported many-to-many and one-to-many form fields instead of silently skipping them
- block file uploads with clear request-time messaging and reject file widgets at admin configuration time
- replace the old table-name string splitting with structured SQLite-oriented database error summaries for unique, not-null, foreign-key, and check constraint failures
- tighten write transaction handling so failed add and edit flows roll back the active session before returning an error state
- move the active package codebase to Python 3.10+ typing syntax and require Python 3.10 or newer in package metadata
- standardize naming around `FastAPINimda` as the canonical class name while keeping `Admin` as a compatibility alias in the public surface and documentation

### Deliverables

- fewer hidden edge cases
- more predictable runtime behavior

## Phase 8: Good-to-Have Features

Status: Admin UX Features and Customization Features complete

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

Completed so far:

- add real list-page search, sorting, and filter controls with query-param persistence
- support custom bulk actions in addition to the existing delete flow
- improve list empty states and form validation feedback
- render foreign-key values with inline related-object labels on list pages
- expose configurable labels, icons, and navigation grouping in the admin UI
- add model-level permission hooks for list, view, add, edit, delete, and custom actions
- add model hooks for custom list queries plus pre-save and post-save behavior
- support model-defined custom object action buttons
- support type-based form field overrides alongside existing per-field widget overrides

## Phase 9: Packaging and Release Readiness

Status: not started

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

1. DONE: clean `pyproject.toml` and package exports
2. DONE: move example apps out of the repo root
3. create `tests/` and lock in current CRUD behavior
4. replace numeric resource identities with stable slugs
5. DONE: rewrite the README into a real quickstart and limitations guide
