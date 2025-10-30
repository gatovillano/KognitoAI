import uuid
from pydantic import BaseModel

class ProfileLinkRequest(BaseModel):
    profile_id: uuid.UUID
