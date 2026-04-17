from datetime import datetime

from sqlmodel import Field, SQLModel
from pydantic import field_validator
import re


class PaletteCreate(SQLModel):
    title: str = Field(max_length=50)
    description: str = Field(max_length=500)
    palette_colors: list[PaletteColorSave] = Field(default=[])

    @field_validator("title")
    @classmethod
    def validate_title_palette_create(cls, title: str) -> str:
        pattern = r"^[a-zA-Z0-9._-]+$"
        if not re.match(pattern, title):
            raise ValueError("Title is invalid.")
        return title


class PaletteCreateResponse(SQLModel):
    id: int
    title: str
    description: str
    created_at: datetime


class PaletteSave(SQLModel):
    title: str
    description: str


class PaletteColorSave(SQLModel):
    hex: str = Field(max_length=6)
    label: str | None = Field(max_length=50)


class PaletteSnapshotSave(SQLModel):
    parent_snapshot_id: int | None = Field(default=None)  # branch point
    palette_colors: list[PaletteColorSave] = Field(default=[])
    comment: str = Field(max_length=500)


class PaletteSnapshotSaveResponse(SQLModel):
    palette_id: int
    palette_snapshot_id: int
    parent_snapshot_id: int | None
    palette_colors: list[PaletteColorSave] = Field(default=[])
    comment: str = Field(max_length=500)
    created_at: datetime
    colors_added: int = Field(default=0)
    colors_deleted: int = Field(default=0)
    colors_modified: int = Field(default=0)


# A single commit in the tree
class PaletteCommitResponse(SQLModel):
    id: int
    palette_id: int
    parent_snapshot_id: int | None
    comment: str | None
    created_at: datetime
    palette_colors: list[PaletteColorSave] = Field(default=[])
    colors_added: int = Field(default=0)
    colors_deleted: int = Field(default=0)
    colors_modified: int = Field(default=0)


# The overall repository history
class PaletteHistoryGraphResponse(SQLModel):
    main: list[PaletteCommitResponse] = Field(default=[])
    branches: dict[str, list[PaletteCommitResponse]] = Field(default={})
