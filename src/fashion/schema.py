"""Item schema (plan Section 5.2). Used as the Gemini response schema and for validation."""
import re
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

Kind = Literal["top", "bottom", "dress", "layer", "ethnic_wear", "jewellery"]
Pattern = Literal["solid", "micro", "stripe", "check", "floral", "print", "embroidered", "other"]
Season = Literal["summer", "monsoon", "winter", "all"]
Metal = Literal["gold", "silver", "rose_gold", "oxidised", "mixed", "none"]
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class ItemTags(BaseModel):
    kind: Kind
    subtype: str = Field(description="e.g. kurti, saree, jeans, jhumka, blazer")
    primary_color_hex: str = Field(description="dominant colour of the garment only, like #A1B2C3")
    secondary_color_hex: Optional[str] = None
    pattern: Pattern = "solid"
    fabric_guess: str = "unknown"
    neckline: Optional[str] = None
    sleeve: Optional[str] = None
    length: Optional[str] = None
    fit: Optional[str] = None
    formality: int = Field(description="1 very casual .. 5 very formal")
    seasons: list[Season] = ["all"]
    occasions: list[str] = []
    embellishment_level: int = Field(default=0, description="0 none .. 3 heavy embroidery or stones")
    metal_tone: Optional[Metal] = None
    style_tags: list[str] = []

    @field_validator("primary_color_hex", "secondary_color_hex")
    @classmethod
    def _hex(cls, v):
        if v is None:
            return v
        if not _HEX.match(v):
            raise ValueError(f"bad hex colour: {v}")
        return v.upper()

    @field_validator("formality")
    @classmethod
    def _formality(cls, v):
        return max(1, min(5, int(v)))

    @field_validator("embellishment_level")
    @classmethod
    def _emb(cls, v):
        return max(0, min(3, int(v)))
