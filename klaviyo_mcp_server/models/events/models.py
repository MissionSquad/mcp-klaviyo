from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from klaviyo_mcp_server.models.profiles import Profile


class EventMetricAttributes(BaseModel):
    name: str = Field(
        description="Name of the event.",
        max_length=128,
    )


class EventMetric(BaseModel):
    type: Literal["metric"]
    attributes: EventMetricAttributes = Field(
        description="Attributes of the metric the event is associated with."
    )


class EventProfile(BaseModel):
    type: Literal["profile"]
    id: str | None = Field(
        None, description="Primary key that uniquely identifies this profile."
    )
    attributes: Profile = Field(
        description="Attributes of the profile the event is associated with."
    )


class Event(BaseModel):
    properties: dict[str, Any] = Field(
        description="Properties of this event. Any top level property (that are not objects) can be used to create segments. The $extra property is a special property. This records any non-segmentable values that can be referenced later. For example, HTML templates are useful on a segment but are not used to create a segment.",
    )
    time: datetime | None = Field(
        None,
        description="When this event occurred. By default, the time the request was received will be used. The time is truncated to the second. The time must be after the year 2000 and can only be up to 1 year in the future.",
    )
    value: float | None = Field(
        None,
        description="A numeric, monetary value to associate with this event. For example, the dollar amount of a purchase.",
    )
    value_currency: str | None = Field(
        None,
        description="The ISO 4217 currency code of the value associated with the event.",
    )
    unique_id: str | None = Field(
        None,
        description="A unique identifier for an event. If the unique_id is repeated for the same profile and metric, only the first processed event will be recorded. If this is not present, this will use the time to the second. Using the default, this limits only one event per profile per second.",
    )
