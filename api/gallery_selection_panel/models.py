# Re-export models from the canonical extension location.
# This avoids defining the same SQLAlchemy classes twice in the same
# declarative base registry (which causes "Multiple classes found" errors).
from extensions.gallery_selection_panel.backend.models import (
    SelectionShareLink,
    SelectionSubmission,
    SelectionItem,
)

__all__ = ["SelectionShareLink", "SelectionSubmission", "SelectionItem"]
