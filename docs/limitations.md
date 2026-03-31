# Limitations

## Current Technical Limits

- Python 3.10 or newer is required
- only single-column primary keys are supported
- file uploads are not supported in admin forms
- many-to-many editing is explicitly unsupported
- one-to-many collection fields are not supported in admin forms
- foreign-key handling is intentionally conservative
- some error handling still assumes SQLite-oriented behavior

## Repository and Packaging Notes

- generated SQLite database files should not live at the repository root
- example applications should create their own local database files inside their example directories
- generated `.db` files are ignored via `.gitignore`

## Metadata Note

Project URLs have not been added to `pyproject.toml` yet because there is no configured upstream repository URL in local git metadata.
