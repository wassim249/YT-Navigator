"""Schemas for the agent."""

from typing import (
    Annotated,
    Literal,
    Optional,
    Sequence,
    Union,
)

from django.utils.functional import SimpleLazyObject
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from markdown2 import markdown
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from app.models import Channel


class AgentRouterOutput(BaseModel):
    """The output of the agent router."""

    answer: Literal["Yes", "No", "Not relevant"]


class OutputAgentState(BaseModel):
    """The output state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]

    class Config:
        """Config for the output agent state."""

        arbitrary_types_allowed = True


class InputAgentState(OutputAgentState):
    """The input state of the agent."""

    channel: Union[Channel, dict]
    user: Union[SimpleLazyObject, object]


class AgentState(InputAgentState):
    """The state of the agent."""

    router_results: Optional[AgentRouterOutput] = Field(default=None)

    class Config:
        """Config for the agent state."""

        arbitrary_types_allowed = True


class AgentOutputTimestamp(BaseModel):
    """The timestamp of the agent output."""

    start: Optional[str] = Field(..., description="Start time of the segment")
    end: Optional[str] = Field(..., description="End time of the segment")
    description: Optional[str] = Field(..., description="Description of the segment (why it's relevant)")


class AgentOutputVideos(BaseModel):
    """The output videos of the agent."""

    title: Optional[str] = Field(..., description="Title of the video")
    id: Optional[str] = Field(..., description="Id of the video example: vxKimq_y0N5")
    timestamps: Optional[list[AgentOutputTimestamp]] = Field(
        ..., description="List of timestamps where you found the related information"
    )
    description: Optional[str] = Field(..., description="Description of the video related to the conversation")
    thumbnail_url: str = Field(
        description="Real Youtube Thumbnail url of the video from the tool results",
    )

    @field_validator("thumbnail_url", mode="before")
    @classmethod
    def fix_thumbnail_url(cls, thumbnail_url):
        """Fix the thumbnail url."""
        if thumbnail_url is None:
            return "https://i.ytimg.com/vi/vXKimq_y0N5/hqdefault.jpg"
        return thumbnail_url


class AgentOutput(BaseModel):
    """The output of the agent."""

    placeholder: Optional[str] = Field(
        ...,
        description="A user-friendly message that answers the user's request based on the results found.",
    )
    videos: Optional[list[AgentOutputVideos]] = Field(
        ...,
        description="Choose up to 5 videos that are relevant to the user's request and coherent with your answer.",
    )

    @field_validator("videos", mode="before")
    @classmethod
    def limit_videos_length(cls, videos):
        """Limit the number of videos to a maximum of 5."""
        if videos is None:
            return []
        return videos[:5]  # Limit the number of videos to a maximum of 5

    @field_validator("placeholder", mode="before")
    @classmethod
    def render_placeholder_to_html(cls, raw: str):
        """Render the placeholder to html."""
        return markdown(raw)

    @field_validator("videos", mode="before")
    @classmethod
    def fix_null_videos(cls, videos):
        """Fix null videos."""
        if videos is None:
            return []
        return videos


class ChatMessage(AgentOutput):
    """The chat message."""

    type: Literal["ai", "human"]
