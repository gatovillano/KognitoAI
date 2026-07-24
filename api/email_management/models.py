# Re-export models from the canonical extension location.
# This avoids defining the same SQLAlchemy classes twice in the same
# declarative base registry (which causes "Multiple classes found" errors).
from extensions.email_management.backend.models import UserEmailConfig

__all__ = ["UserEmailConfig"]
