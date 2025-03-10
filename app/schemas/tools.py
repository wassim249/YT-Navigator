"""Schemas for the tools."""

from pydantic import (
    BaseModel,
    Field,
)


class VectorDatabaseToolInput(BaseModel):
    """Input for the vector database tool."""

    query: str = Field(description="The textual query to search for videos, optimized for similarity search")
    channel_id: str = Field(description="The ID of the YouTube channel associated with the query")


class SQLQueryToolInput(BaseModel):
    """Input for the SQL query tool."""

    query: str = Field(description="The SQL query to execute that respects the database schema")
