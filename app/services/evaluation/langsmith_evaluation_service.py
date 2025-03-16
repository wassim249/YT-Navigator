"""This class is used to evaluate the performance of the YT Navigator model.

It uses LangSmith to create a dataset and add examples to it.
"""

import traceback
import uuid
from typing import Optional

import structlog
from asgiref.sync import sync_to_async
from langsmith.client import Client

from app.schemas import InputAgentState

logger = structlog.get_logger(__name__)


class LangsmithEvaluationService:
    """This class is used to evaluate the performance of the YT Navigator model.

    It uses LangSmith to create a dataset and add examples to it.
    """

    DEFAULT_DATASET_NAME = "YT Navigator dataset"
    input_schema = {
        "type": "object",
        "properties": {
            "messages": {"type": "string"},
            "user_information": {"type": "string"},
            "channel_information": {"type": "string"},
        },
        "required": ["messages", "user_information", "channel_information"],
    }

    output_schema = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "router_response": {"type": "string"},
            "tool_calls": {"type": "array", "items": {"type": "string"}, "nullable": True},
        },
        "required": ["answer", "router_response"],
    }

    def __init__(self, dataset_name: str = DEFAULT_DATASET_NAME):
        """Initialize the LangsmithEvaluationService."""
        self.client = Client()
        self.dataset_name = dataset_name
        self.dataset_id = self.dataset_exists(dataset_name)
        if not self.dataset_id:
            self.dataset_id = self.create_dataset(dataset_name)

    def dataset_exists(self, dataset_name: str) -> Optional[uuid.UUID]:
        """Check if a dataset with the given name exists.

        Args:
            dataset_name: The name of the dataset to check

        Returns:
            The dataset ID if it exists, None otherwise
        """
        # List all datasets and filter by name
        datasets = self.client.list_datasets()
        for dataset in datasets:
            if dataset.name == dataset_name:
                return dataset.id
        return None

    def create_dataset(
        self,
    ) -> uuid.UUID:
        """Create a new dataset in LangSmith.

        Returns:
            The ID of the created dataset
        """
        dataset = self.client.create_dataset(
            dataset_name=self.dataset_name,
            description="YT Navigator dataset",
            inputs_schema=self.input_schema,
            outputs_schema=self.output_schema,
        )
        return dataset.id

    def _parse_graph_output_to_example(self, graph_output: InputAgentState):
        """Parse the graph output to an example."""
        return {
            "messages": graph_output.get("messages"),
            "user_information": graph_output.get("user"),
            "channel_information": graph_output.get("channel"),
            "answer": graph_output.get("messages")[-1].content,
            "router_response": graph_output.get("router_results").answer,
        }

    async def add_example(
        self,
        graph_output: InputAgentState,
    ):
        """Add an example to the dataset."""
        try:
            parsed_output = self._parse_graph_output_to_example(graph_output)

            # Get channel info first
            channel_info = await parsed_output["channel_information"].pretty_str()

            input_example = {
                "messages": parsed_output["messages"],
                "user_information": str(parsed_output["user_information"]),
                "channel_information": channel_info,
            }
            output_example = {
                "answer": parsed_output["answer"],
                "router_response": parsed_output["router_response"],
            }
            logger.info("Adding example to dataset")

            # Create a thread-sensitive sync_to_async function for the client operation
            create_example = sync_to_async(
                lambda: self.client.create_example(
                    inputs=input_example, outputs=output_example, dataset_name=self.dataset_name
                ),
                thread_sensitive=True,
            )

            # Execute the async operation
            await create_example()
            logger.info("Successfully added example to dataset")
        except Exception as e:
            logger.error("Error adding example to dataset", error=e, traceback=traceback.format_exc())

    def add_example_sync(self, graph_output: InputAgentState):
        """Add an example to the dataset synchronously.

        This method is used for background tasks where async operations might be problematic.

        Args:
            graph_output: The result from the agent graph execution
        """
        try:
            parsed_output = self._parse_graph_output_to_example(graph_output)

            # Get channel info using the synchronous method
            channel_info = parsed_output["channel_information"].pretty_str_sync()

            input_example = {
                "messages": parsed_output["messages"],
                "user_information": str(parsed_output["user_information"]),
                "channel_information": channel_info,
            }
            output_example = {
                "answer": parsed_output["answer"],
                "router_response": parsed_output["router_response"],
            }
            logger.info("Adding example to dataset (sync)")

            # Execute the operation synchronously
            self.client.create_example(inputs=input_example, outputs=output_example, dataset_name=self.dataset_name)
            logger.info("Successfully added example to dataset (sync)")
        except Exception as e:
            logger.error("Error adding example to dataset (sync)", error=e, traceback=traceback.format_exc())
