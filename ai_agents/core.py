from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI


# Load the project's .env file.
load_dotenv()


@dataclass
class Tool:
    """
    Deterministic Python function exposed to the LLM
    through OpenAI function calling.
    """

    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any]

    def schema(self) -> Dict[str, Any]:
        """
        Build a strict OpenAI function-calling schema.
        """

        parameters = dict(self.parameters)

        parameters["type"] = "object"
        parameters.setdefault("properties", {})

        properties = parameters["properties"]

        # OpenAI strict function calling requires all
        # declared properties to be required.
        parameters["required"] = list(properties.keys())

        # Critical requirement for strict schemas.
        parameters["additionalProperties"] = False

        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": parameters,
            "strict": True,
        }


class AutonomousAgent:
    """
    LLM-driven autonomous ESG agent.

    The LLM decides which available tool to use and
    what action to take next.

    Deterministic Python tools perform the actual:
        - PDF inspection
        - BRSR extraction
        - validation
        - ESG calculations
        - analysis

    This keeps the autonomous decision layer separate
    from the trusted computation layer.
    """

    def __init__(
        self,
        name: str,
        goal: str,
        instructions: str,
        tools: Optional[List[Tool]] = None,
        model: Optional[str] = None,
    ):
        self.name = name
        self.goal = goal
        self.instructions = instructions

        self.tools_list = tools or []

        self.tools = {
            tool.name: tool
            for tool in self.tools_list
        }

        self.model = model or os.getenv("OPENAI_MODEL")
        if not self.model:
            raise RuntimeError(
                "OPENAI_MODEL is not set. "
                "Add the OpenAI model name to your .env file."
            )

        self.max_steps = 12

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file."
            )

        self.client = OpenAI(
            api_key=api_key
        )

        self._last_trace: List[Dict[str, Any]] = []

    def tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Return all tools in OpenAI function-calling format.
        """

        return [
            tool.schema()
            for tool in self.tools_list
        ]

    def _serialize_context(
        self,
        context: Any,
    ) -> str:
        """
        Convert the pipeline context to plain text.

        The pipeline passes a Python dictionary.
        The initial Responses API input is deliberately
        sent as a plain string to avoid object-content
        validation errors.
        """

        if isinstance(context, str):
            return context

        try:
            return json.dumps(
                context,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        except Exception:
            return str(context)

    def _execute_tool(
        self,
        tool_name: str,
        arguments_json: str,
    ) -> Any:
        """
        Execute the deterministic Python tool selected
        by the LLM.
        """

        if tool_name not in self.tools:
            raise ValueError(
                f"Unknown tool requested by model: "
                f"{tool_name}"
            )

        tool = self.tools[tool_name]

        try:
            arguments = json.loads(
                arguments_json or "{}"
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON arguments for tool "
                f"'{tool_name}': {arguments_json}"
            ) from exc

        if not isinstance(arguments, dict):
            raise ValueError(
                f"Arguments for tool '{tool_name}' "
                f"must be a JSON object."
            )

        return tool.handler(**arguments)

    def run(
        self,
        context: Any = None,
        max_steps: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run the autonomous tool-selection loop.

        The model:
            1. receives the project context,
            2. decides which tool is useful,
            3. calls the deterministic tool,
            4. receives its result,
            5. decides whether another action is required,
            6. produces a final response.
        """

        if max_steps is not None:
            self.max_steps = max_steps

        effective_context = (
            context
            if context is not None
            else self.goal
        )

        initial_input = self._serialize_context(
            effective_context
        )

        # IMPORTANT:
        # The first Responses API input is a plain string.
        # This avoids the previous:
        # input[0].content expected string/array
        # but got object error.
        conversation_input: Any = initial_input

        trace: List[Dict[str, Any]] = []

        final_text = ""

        for step in range(
            1,
            self.max_steps + 1,
        ):

            response = self.client.responses.create(
                model=self.model,
                instructions=(
                    f"Your specialist role is: {self.name}\n\n"
                    f"Your goal is: {self.goal}\n\n"
                    f"{self.instructions}"
                ),
                input=conversation_input,
                tools=self.tool_schemas(),
                tool_choice="auto",
            )

            output_items = response.output

            trace.append(
                {
                    "step": step,
                    "response_id": getattr(
                        response,
                        "id",
                        None,
                    ),
                    "output_types": [
                        getattr(
                            item,
                            "type",
                            None,
                        )
                        for item in output_items
                    ],
                }
            )

            function_calls = [
                item
                for item in output_items
                if getattr(
                    item,
                    "type",
                    None,
                ) == "function_call"
            ]

            # No function call means the model has
            # completed its autonomous task.
            if not function_calls:

                final_text = getattr(
                    response,
                    "output_text",
                    "",
                )

                result = {
                    "agent": self.name,
                    "goal": self.goal,
                    "model": self.model,
                    "status": "completed",
                    "steps": step,
                    "final": final_text,
                    "answer": final_text,
                    "trace": trace,
                }

                self._last_trace = trace

                return result

            # Build the next Responses API input.
            #
            # The model's function-call items are preserved,
            # followed by the outputs of the deterministic
            # Python tools.
            next_input: List[Any] = list(
                output_items
            )

            for call in function_calls:

                tool_name = getattr(
                    call,
                    "name",
                    None,
                )

                arguments = getattr(
                    call,
                    "arguments",
                    "{}",
                )

                call_id = getattr(
                    call,
                    "call_id",
                    None,
                )

                try:

                    tool_result = self._execute_tool(
                        tool_name,
                        arguments,
                    )

                    if isinstance(
                        tool_result,
                        str,
                    ):
                        result_text = tool_result
                    else:
                        result_text = json.dumps(
                            tool_result,
                            ensure_ascii=False,
                            default=str,
                        )

                    tool_status = "success"

                except Exception as exc:

                    result_text = json.dumps(
                        {
                            "error": type(exc).__name__,
                            "message": str(exc),
                        },
                        ensure_ascii=False,
                    )

                    tool_status = "error"

                trace.append(
                    {
                        "step": step,
                        "tool": tool_name,
                        "arguments": arguments,
                        "tool_status": tool_status,
                    }
                )

                next_input.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": result_text,
                    }
                )

            conversation_input = next_input

        self._last_trace = trace

        final_text = (
            "The autonomous agent reached the maximum "
            f"number of {self.max_steps} steps."
        )

        return {
            "agent": self.name,
            "goal": self.goal,
            "model": self.model,
            "status": "max_steps_reached",
            "steps": self.max_steps,
            "final": final_text,
            "answer": final_text,
            "trace": trace,
        }

    def save_trace(
        self,
        path: str | Path,
    ) -> None:
        """
        Save the autonomous decision/tool trace
        for project auditability.
        """

        output_path = Path(path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            json.dumps(
                {
                    "agent": self.name,
                    "goal": self.goal,
                    "model": self.model,
                    "max_steps": self.max_steps,
                    "trace": self._last_trace,
                },
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )


# Backward-compatible alias.
Agent = AutonomousAgent