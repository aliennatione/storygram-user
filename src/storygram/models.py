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


class Source(BaseModel):
    id: str = Field(pattern=r"^source:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Source"]
    title: str
    source_type: Literal["oral", "written", "archival", "registry", "photograph", "audio", "video", "website", "other"] | None = None
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "archived"]
    created_at: datetime
    updated_at: datetime
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    notes: str | None = None


class Annotation(BaseModel):
    id: str = Field(pattern=r"^annotation:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Annotation"]
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "archived"]
    created_at: datetime
    updated_at: datetime
    target_ids: list[str] | None = None
    episode_ids: list[str] | None = None
    source_ids: list[str] | None = None
    notes: str | None = None
    visibility: Literal["private", "restricted", "family", "public"] | None = None


class Person(BaseModel):
    id: str = Field(pattern=r"^person:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Person"]
    name: str | None = None
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "archived"]
    created_at: datetime
    updated_at: datetime
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    notes: str | None = None


class Organization(BaseModel):
    id: str = Field(pattern=r"^organization:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Organization"]
    name: str | None = None
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "archived"]
    created_at: datetime
    updated_at: datetime
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    notes: str | None = None


class Place(BaseModel):
    id: str = Field(pattern=r"^place:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Place"]
    name: str | None = None
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "archived"]
    created_at: datetime
    updated_at: datetime
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    notes: str | None = None


class Period(BaseModel):
    id: str = Field(pattern=r"^period:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Period"]
    name: str | None = None
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "archived"]
    created_at: datetime
    updated_at: datetime
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    notes: str | None = None


class Event(BaseModel):
    id: str = Field(pattern=r"^event:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Event"]
    name: str | None = None
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "archived"]
    created_at: datetime
    updated_at: datetime
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    notes: str | None = None


class Relationship(BaseModel):
    id: str = Field(pattern=r"^relationship:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Relationship"]
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "archived"]
    created_at: datetime
    updated_at: datetime
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    notes: str | None = None


class MediaAsset(BaseModel):
    id: str = Field(pattern=r"^media:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["MediaAsset"]
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "archived"]
    created_at: datetime
    updated_at: datetime
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    notes: str | None = None


class Narrative(BaseModel):
    id: str = Field(pattern=r"^narrative:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Narrative"]
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "archived"]
    created_at: datetime
    updated_at: datetime
    author: str | None = None
    language: str | None = None
    perspective: str | None = None
    related_ids: list[str] | None = None
    source_ids: list[str] | None = None
    content_location: str | None = None
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    notes: str | None = None


class Collection(BaseModel):
    id: str = Field(pattern=r"^collection:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Collection"]
    name: str | None = None
    status: Literal["draft", "proposed", "reported", "confirmed", "disputed", "rejected", "archived"]
    created_at: datetime
    updated_at: datetime
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    notes: str | None = None


class Proposal(BaseModel):
    id: str = Field(pattern=r"^proposal:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Proposal"]
    status: Literal["draft", "proposed", "under_review", "approved", "rejected", "merged", "archived"]
    created_at: datetime
    updated_at: datetime
    target_ids: list[str] | None = None
    evidence: list[str] | None = None
    rationale: str | None = None
    confidence: Literal["low", "medium", "high"] | None = None
    approval_state: str | None = None
    notes: str | None = None


class Conflict(BaseModel):
    id: str = Field(pattern=r"^conflict:[A-Za-z0-9][A-Za-z0-9._~-]*$")
    type: Literal["Conflict"]
    assertions: list[str] = Field(min_length=2)
    relation: Literal["contradicts", "inconsistent", "competing"] | None = None
    status: Literal["open", "under_review", "resolved", "accepted_as_plural", "rejected"]
    reason: str | None = None
    identified_at: datetime | None = None
    review: dict[str, Any] | None = None
    evidence: list[str] | None = None
    reviewer: str | None = None
    decision: str | None = None
    created_at: datetime
    updated_at: datetime
    visibility: Literal["private", "restricted", "family", "public"] | None = None
    notes: str | None = None
