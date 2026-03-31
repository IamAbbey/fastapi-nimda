# fastapi-nimda Architecture

## Current State

This project is an early-stage FastAPI admin framework for SQLAlchemy and SQLModel applications.

The current implementation already has a usable core:

- a dedicated admin application object (`FastAPINimda`) that mounts itself under `/admin`
- model registration through `register(model, modeladmin)`
- a `ModelAdmin` abstraction for per-model configuration
- server-rendered CRUD pages for list, add, view, edit, and delete flows
- Jinja-based templating with Tailwind/Flowbite-driven UI assets
- form/widget generation based on SQLAlchemy model inspection
- dependency-based resource and record loading through FastAPI `Depends`

At the same time, the repository still reads like a work in progress rather than a finished package:

- the README is only a short usage sketch and does not document the system
- there are multiple scratch/example files (`main.py`, `main2.py`, `test.py`, `admin copy.py`, template copies)
- there is little visible automated test coverage
- several constraints are hard-coded into the implementation
- some APIs and naming are still unstable or incomplete

In practical terms: the project has a clear direction and a functioning prototype, but it has not yet been hardened into a production-ready library.

## Author's Approach

The author is taking a "small Django admin for FastAPI" approach.

The design centers around a few ideas:

### 1. Mount a self-contained admin app inside an existing FastAPI app

`FastAPINimda` subclasses `FastAPI`, then mounts itself onto another app at `/admin`.

This means the admin behaves like a nested application with its own:

- routes
- templates
- static files
- model registry

That is a pragmatic approach because it keeps the admin surface isolated from the host application while still sharing the same process and database engine.

### 2. Use model introspection instead of handwritten CRUD

`ModelAdmin` inspects the SQLAlchemy mapper to discover:

- normal columns
- foreign-key columns
- relationships
- primary keys

From there, the framework generates list views, forms, and CRUD statements automatically. The implementation is intentionally metadata-driven rather than schema-declaration-heavy.

This keeps the user-facing API small:

1. define models
2. subclass `ModelAdmin`
3. register the model

### 3. Favor server-rendered HTML over a separate frontend

The UI is rendered with Jinja templates, not a SPA.

That choice keeps the stack simple:

- FastAPI handles routing and request lifecycle
- SQLAlchemy handles persistence
- Jinja handles rendering
- Tailwind/Flowbite handle presentation

This is a sensible fit for an admin product where speed of iteration and low complexity matter more than frontend sophistication.

### 4. Keep extension points class-based

The project borrows the class-based customization model from Django admin:

- `list_display`
- `fields`
- `readonly_fields`
- `exclude`
- `widgets`
- `page_size`
- `list_order_by`

That approach is easy to understand for users and keeps custom behavior colocated with each registered model.

## Implementation Model

The project currently breaks down into these major layers.

### Application Layer

File: `fastapi_nimda/app.py`

Responsibilities:

- perform startup environment checks
- own the model registry
- mount the admin app under `/admin`
- expose static assets
- attach the admin router
- keep a database `engine` on the app instance

This file is effectively the composition root of the framework.

### Registration and Metadata Layer

Files:

- `fastapi_nimda/app.py`
- `fastapi_nimda/types.py`
- `fastapi_nimda/admin.py`

Responsibilities:

- register models with admin configuration classes
- store resources in an internal registry
- instantiate `ModelAdmin` objects on demand
- validate that model/admin combinations are acceptable

The registration model is intentionally simple: an identity string maps to a model plus its admin class.

### Admin Configuration and Query Layer

File: `fastapi_nimda/admin.py`

This is the real core of the project.

It owns:

- model inspection
- field validation
- query construction for list/view/edit/delete
- insert/update/delete statement generation
- page-size and list-column policy
- form construction and rendering

The class is acting as both:

- a configuration object
- a runtime adapter over an ORM model

That keeps the implementation compact, but it also means `ModelAdmin` is carrying a lot of responsibility.

### Routing Layer

File: `fastapi_nimda/routing.py`

Responsibilities:

- define admin HTTP endpoints
- coordinate form handling
- execute persistence operations through SQLAlchemy sessions
- render templates
- redirect after successful writes
- surface simple success/error messages

The route handlers are thin enough to be readable, but they still contain a fair amount of business flow logic. There is not yet a separate service layer.

### Dependency Layer

File: `fastapi_nimda/depends.py`

Responsibilities:

- resolve a registered resource from the URL identity
- create the correct `ModelAdmin` instance for that resource
- fetch a single record or multiple records
- expose these objects to route handlers through FastAPI dependency injection

This is a good fit for FastAPI and keeps routing functions cleaner.

### Presentation Layer

Files:

- `fastapi_nimda/templates/*`
- `fastapi_nimda/templating/*`
- `fastapi_nimda/widgets.py`
- `fastapi_nimda/messaging.py`

Responsibilities:

- render admin pages
- render form controls
- supply template filters and shared template context
- display flash-style messages

The widget system is clearly inspired by Django forms. The author is building a reusable rendering abstraction rather than hardcoding HTML directly into each route.

### Persistence Assumptions

The current implementation assumes a fairly narrow ORM model:

- SQLAlchemy or SQLModel-backed models
- a conventional primary key access pattern
- limited foreign-key complexity
- no file upload handling yet
- no many-to-many admin workflow support beyond partial relationship awareness

There is also an explicit SQLite version requirement because inserts rely on `RETURNING`.

## Architectural Assessment

The architecture is coherent for the kind of package this wants to become.

Its strengths are:

- simple mental model
- low integration overhead
- strong use of FastAPI primitives
- class-based extension surface
- server-rendered approach that avoids unnecessary frontend complexity

Its current weaknesses are:

- responsibilities are concentrated heavily inside `ModelAdmin`
- the model registry uses generated string identities instead of stable names
- there is little separation between query generation, form generation, and view behavior
- error handling is still ad hoc
- feature support is constrained by assumptions embedded deep in inspection logic

## Suggestions

1. Stabilize the public API before adding more features.
Document the intended package surface clearly: app construction, model registration, supported model patterns, and extension hooks.

2. Split `ModelAdmin` into smaller internal collaborators.
The most obvious seams are:
- model inspection
- query building
- form building/validation
- field/widget resolution

3. Replace numeric registry identities with deterministic resource names.
Using model names or explicit route slugs would make URLs more stable and easier to reason about.

4. Add a real test suite before expanding feature scope.
Focus first on:
- model registration validation
- form generation from model metadata
- CRUD route behavior
- foreign-key and relationship edge cases

5. Tighten database support assumptions.
Either commit to SQLite-first behavior explicitly, or introduce clearer abstraction boundaries for database-specific behavior like `RETURNING` and error normalization.

6. Formalize unsupported cases.
Many-to-many editing, multi-column keys, multiple foreign keys on one column, file uploads, and richer relationship handling should be either implemented or explicitly rejected in documented ways.

7. Clean the repository structure.
Remove or quarantine scratch files, copied templates, and experiment files so the package structure reflects the intended product.

8. Improve developer documentation.
The project needs a proper README with:
- project goal
- supported stacks
- quickstart
- example model registration
- feature list
- current limitations

9. Introduce a service boundary for write operations.
Even a thin internal layer between routes and SQLAlchemy would make the code easier to test and evolve.

10. Define the long-term position of the project.
The main strategic choice is whether this should remain:
- a lightweight admin generator
- or a more complete Django-admin-style framework for FastAPI

The current architecture supports the first very well. Reaching the second will require more explicit boundaries and a more disciplined public API.
