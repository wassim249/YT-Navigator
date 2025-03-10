"""This module contains the tools for the SQL database."""

import asyncio
from typing import (
    Any,
    Dict,
    List,
)

import asyncpg
import psycopg2
import psycopg2.extras
from django.conf import settings
from langchain.tools import StructuredTool

from app.models import (
    Channel,
    User,
    Video,
    VideoChunk,
)
from app.schemas import SQLQueryToolInput


class SQLTools:
    """A tool for executing SQL queries and database operations."""

    @classmethod
    def get_db_connection(cls):
        """Get a database connection."""
        return psycopg2.connect(settings.PSYCOPG2_DATABASE_URL)

    @classmethod
    def close_db_connection(cls, conn):
        """Close a database connection."""
        conn.close()

    @classmethod
    def get_tables_schema(cls):
        """Retrieve the schema information for all relevant database tables, including their names and field types."""
        project_models = [Channel, User, Video, VideoChunk]
        tables = []
        for model in project_models:
            table_info = {
                "table_name": model._meta.db_table,
                "fields": [
                    {
                        "name": field.name,
                        "type": field.get_internal_type(),
                    }
                    for field in model._meta.fields
                ],
            }
            tables.append(table_info)
        return tables

    @classmethod
    def _format_tables_schema(cls, tables: List[Dict[str, Any]]) -> str:
        """Format the schema of all tables in the database."""
        return "\n".join(
            f"{table['table_name']}: " + ", ".join(f"{f['name']}({f['type']})" for f in table["fields"])
            for table in tables
        )

    @classmethod
    async def execute_query(cls, query: str) -> str:
        """Execute a SELECT query and return the results.

        Args:
            query: The SQL query to execute (must be a SELECT query)

        Returns:
            List of result rows as strings or an error message
        """
        if not query.startswith("SELECT"):
            return "Error: Only SELECT queries are supported"

        # get Video db_name
        video_db_name = Video._meta.db_table
        chunk_db_name = VideoChunk._meta.db_table
        if video_db_name not in query and chunk_db_name not in query:
            return f"""DB SCHEMA:\n{cls.get_tables_schema()}\nError: You are allowed only to search in the {video_db_name} and {chunk_db_name} tables"""

        try:
            # Extract connection parameters from the URL
            conn_url = settings.PSYCOPG2_DATABASE_URL

            # Connect using asyncpg
            conn = await asyncpg.connect(conn_url)
            try:
                # Execute the query
                result = await conn.fetch(query)

                # Format the results - asyncpg returns Record objects that need to be converted to dicts
                formated_result = [str(dict(row.items())) for row in result]
                if len(formated_result) > 20:
                    formated_result.append(
                        f"The result is too long; truncated to 20 rows from a total of {len(formated_result)} rows."
                    )
                    return "\n".join(formated_result[:20])
                return "\n".join(formated_result)
            finally:
                # Close the connection
                await conn.close()
        except Exception as e:
            return f"""
            DB SCHEMA:
            {cls.get_tables_schema()}
        
            #Error: {e}
            """

    @classmethod
    def tool(cls) -> StructuredTool:
        """Create a structured tool for executing SQL queries."""

        def run_async_query(query: str) -> List[str] | str:
            """Run the async query in a synchronous context.

            Args:
                query: The SQL query to execute

            Returns:
                The query results or error message
            """
            try:
                return asyncio.run(cls.execute_query(query))
            except Exception as e:
                return f"Error executing query: {str(e)}"

        return StructuredTool.from_function(
            func=run_async_query,
            name="execute_query",
            description="Powerful SQL query execution tool for advanced data retrieval and analysis. Use this to perform complex database operations such as: "
            "- Joining multiple tables to extract comprehensive insights "
            "- Filtering and aggregating video metadata "
            "- Performing complex calculations or statistical analysis "
            "- Retrieving specific subsets of data not easily accessible through other methods "
            f"\n Table schema:\nPOSTGRES SYNTAX:\n{cls.get_tables_schema()}",
            args_schema=SQLQueryToolInput,
            handle_tool_error=True,
        )
