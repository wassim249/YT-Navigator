"""MongoDB evaluation database."""

import json
import os
import traceback
from datetime import datetime

import motor.motor_asyncio
import structlog
from bs4 import BeautifulSoup
from langchain_core.messages import BaseMessage

from app.schemas.agent import InputAgentState

logger = structlog.get_logger(__name__)


class MongoDBEvalDB:
    """MongoDB evaluation database."""

    EVALUATION_COLLECTION = "evaluation"

    def __init__(self):
        """Initializes the MongoDB evaluation database."""
        logger.info("Initializing MongoDB evaluation database.")
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGO_DB_EVALUATION_URI"))
            self.db = self.client[os.getenv("MONGO_DB_EVALUATION_NAME")]
        except Exception as e:
            logger.error(
                "Error initializing MongoDB evaluation database.", error=str(e), traceback=traceback.format_exc()
            )
            raise e

    async def _evaluation_collection_created(self):
        """Checks if evaluation collection exists.

        Returns:
            bool: True if collection exists, False otherwise.
        """
        collections = await self.db.list_collection_names()
        if self.EVALUATION_COLLECTION not in collections:
            logger.info("Evaluation collection not found in the database.")
            await self.create_evaluation_collection()
            logger.info("Created evaluation collection.")
            return False
        logger.info("Evaluation collection already exists.")
        return True

    async def create_evaluation_collection(self):
        """Creates the evaluation collection."""
        logger.info("Creating evaluation collection.")
        await self.db.create_collection(self.EVALUATION_COLLECTION)

    async def add_evaluation(self, graph_output: InputAgentState):
        """Adds an evaluation to the evaluation collection.

        Args:
            graph_output (InputAgentState): The agent state containing evaluation data.

        Returns:
            dict: The evaluation object that was added to the database.
        """
        logger.info("Adding evaluation to the collection.")

        # Ensure collection exists
        await self._evaluation_collection_created()

        evaluation = await self._get_evaluation_object(graph_output)
        results = await self.db[self.EVALUATION_COLLECTION].insert_one(evaluation, bypass_document_validation=True)
        logger.info("Evaluation added successfully.", evaluation=evaluation, results=results.inserted_id)
        return evaluation

    async def _get_evaluation_object(self, graph_output: InputAgentState) -> dict:
        """Gets the evaluation object.

        Args:
            graph_output (InputAgentState): The agent state containing evaluation data.

        Returns:
            dict: A dictionary containing the formatted evaluation data.
        """
        return {
            "history": self.__parse_history(graph_output.get("messages")),
            "tool_calls": self.__get_tool_calls(graph_output.get("messages")[4]),
            "router_response": graph_output.get("router_results").answer,
            "answer": self.__parse_answer(graph_output.get("messages")[-1].content),
            "channel": await graph_output.get("channel").pretty_str(),
            "user": graph_output.get("user").dict(),
            "created_at": datetime.now(),
        }

    @staticmethod
    def __parse_history(history: list[BaseMessage]) -> list[dict]:
        """Parses the history into the correct format.

        Args:
            history (list[BaseMessage]): List of message objects from conversation history.

        Returns:
            list[dict]: List of dictionaries with role and content for each message.
        """
        logger.info("Parsing history.")
        return [
            {"role": msg.type, "content": MongoDBEvalDB.__parse_answer_to_plain_text(msg.content)}
            for msg in history
            if msg.type in ["human", "ai"] and msg.content
        ][4:-1]

    @staticmethod
    def __get_tool_calls(history: list[BaseMessage]) -> list[dict]:
        """Gets the tool calls from the history."""
        tool_calls_from_ai = []
        tool_calls = []
        for msg in history:
            if msg.type == "ai" and msg.tool_calls:
                tool_calls_from_ai.extend(msg.tool_calls)

        for tool_result in [msg for msg in history if msg.type == "tool"]:
            if tool_result.name in [tool_call.get("name") for tool_call in tool_calls_from_ai]:
                corresponding_tool_call_from_ai = next(
                    (tool_call for tool_call in tool_calls_from_ai if tool_call.get("name") == tool_result.name),
                    None,
                )
                tool_calls.append(
                    {
                        "name": tool_result.name,
                        "args": corresponding_tool_call_from_ai.get("args"),
                        "content": tool_result.content,
                        "id": tool_result.id,
                        "tool_call_id": tool_result.tool_call_id,
                        "status": tool_result.status,
                    }
                )

        return tool_calls

    @staticmethod
    def __parse_answer(answer: str) -> str:
        """Parses the answer into the correct format.

        Args:
            answer (str): The raw answer string.

        Returns:
            str: The parsed answer, either as JSON or the original string if parsing fails.
        """
        logger.info("Parsing answer.")
        try:
            return json.loads(MongoDBEvalDB.__parse_answer_to_plain_text(answer))
        except json.JSONDecodeError as e:
            logger.error("Error parsing answer.", error=str(e), traceback=traceback.format_exc())
            return answer

    @staticmethod
    def __parse_answer_to_plain_text(answer: str) -> str:
        """Parses the answer into plain text.

        Args:
            answer (str): The raw answer string, potentially containing HTML.

        Returns:
            str: The plain text version of the answer with HTML stripped.
        """
        logger.info("Parsing answer to plain text.")
        try:
            soup = BeautifulSoup(answer, "html.parser")
            return soup.get_text().strip()
        except Exception as e:
            logger.error("Error parsing answer to plain text.", error=str(e), traceback=traceback.format_exc())
            return answer
