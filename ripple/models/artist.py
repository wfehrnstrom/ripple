from typing import Optional

class Artist:
    schema_version: str = "1.0.0"
    rb_id: Optional[str]
    streaming_ids: Optional[dict]
    streaming_urls: Optional[dict]
    name: str
    roles: Optional[list[str]]
    # Either a string url or a local image.
    picture: Optional[str]
    bio: Optional[str]
    user_tags: Optional[set]
    user_attributes: Optional[dict]

    def __init__(self, name):
        self.name = name