def pretty_name(value: str):
    """Convert 'first_name' to 'First name'."""
    if not value:
        return ""
    return value.replace("_", " ").capitalize()
