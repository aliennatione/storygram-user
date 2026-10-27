"""Pydantic models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Checksum(BaseModel):
    algorithm: Literal["sha256"]
    value: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")


class TransactionTime(BaseModel):
    recorded_at: datetime
    recorded_until: datetime | None = None


class ValidTime(BaseModel):
    start: str | None = None
    end: str | None = None
    precision: Literal["day", "month", "year", "decade", "approximate", "unknown"] | None = None
    expression: str | None = None
    calendar: str | None = None


class Episode(BaseModel):
    id: str = Field(pattern=r"^episode:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Episode"]
    episode_type: Literal[
        "interview",
        "memory",
        "letter",
        "photograph",
        "audio",
        "video",
        "document",
        "observation",
        "import",
        "narrative_revision",
        "other",
    ]
    title: str | None = None
    description: str | None = None
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "archived"]
    created_at: datetime
    updated_at: datetime
    captured_at: str | None = None  # allow date or datetime or year
    captured_until: str | None = None
    recorded_by: str | None = None
    created_by: str | None = None
    participants: list[str] | None = None
    source_ids: list[str] | None = None
    media_asset_ids: list[str] | None = None
    transcript_id: str | None = None
    content: dict[str, Any] | None = None
    checksum: Checksum | None = None
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    tags: list[str] | None = None
    supersedes: list[str] | None = None
    notes: str | None = None


class Assertion(BaseModel):
    id: str = Field(pattern=r"^assertion:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Assertion"]
    subject: str
    predicate: str = Field(pattern=r"^relation:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    object: str | None = None
    value: Any | None = None
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "superseded", "archived"]
    certainty: Literal["unknown", "possible", "probable", "reported", "confirmed", "disputed", "rejected"] | None = None
    confidence: Literal["low", "medium", "high"] | None = None
    source_quality: Literal["unknown", "low", "medium", "high"] | None = None
    valid_time: ValidTime | None = None
    transaction_time: TransactionTime
    asserted_by: list[str] | None = None
    produced_by: list[str] | None = None
    supported_by: list[str] | None = None
    annotations: list[str] | None = None
    supersedes: list[str] | None = None
    revises: list[str] | None = None
    contradicts: list[str] | None = None
    corroborates: list[str] | None = None
    review: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    tags: list[str] | None = None
    notes: str | None = None
