from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AlertSeverity = Literal["info", "warning", "critical"]


class SystemAnnouncementPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    body: str
    severity: AlertSeverity
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    dismissible: bool
    created_at: datetime


class OrgAlertPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    title: str
    body: str
    severity: AlertSeverity
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    dismissible: bool
    created_at: datetime


class SystemAnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)
    severity: AlertSeverity = "info"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    dismissible: bool = True


class OrgAlertCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)
    severity: AlertSeverity = "info"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    dismissible: bool = True


class AlertAcknowledgementRequest(BaseModel):
    """Empty body — the target alert is identified by the URL path."""
