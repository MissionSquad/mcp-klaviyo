from collections import defaultdict
from typing import Literal, Union, List
from datetime import date, datetime

from pydantic import Field, create_model
import requests

from klaviyo_api import KlaviyoAPI


class ModelGenerator:
    """Utility for generating a type from an OAS schema."""

    def __init__(self, full_oas: dict):
        self.full_oas = full_oas
        self.model_count = defaultdict(
            lambda: 0
        )  # model name -> number of times it's been used

    def generate_from_schema_name(self, *schema_path: str) -> type:
        """Generate a type from the OAS schema with the given path."""
        schema = self.full_oas["components"]["schemas"]
        for path_segment in schema_path:
            schema = schema[path_segment]
        return self._generate_from_schema(schema, list(schema_path))

    def _generate_from_schema(self, schema: dict, schema_path: list[str]) -> type:
        """Generate a type from the given OAS schema, and a list of model/property names representing the
        path to the schema."""
        if "$ref" in schema:
            schema_name = schema["$ref"].split("/")[-1]

            # Gemini doesn't support schemas being used in more than one place
            # This workaround re-defines such schema models, but appending an incremental number to their name
            schema = self.full_oas["components"]["schemas"][schema_name]
            self.model_count[schema_name] += 1
            if self.model_count[schema_name] > 1:
                schema_name += str(self.model_count[schema_name])

            return self._generate_from_schema(schema, [schema_name])

        if "enum" in schema:
            # Gemini doesn't support int enums
            if schema.get("type") == "integer":
                return int
            return Literal[*schema["enum"]]

        if "oneOf" in schema:
            sub_schemas = [
                self._generate_from_schema(m, [*schema_path, str(index)])
                for index, m in enumerate(schema["oneOf"])
            ]
            return Union[*sub_schemas]

        if schema["type"] == "array":
            item_type = self._generate_from_schema(
                schema["items"], [*schema_path, "items"]
            )
            return List[item_type]

        if schema["type"] == "object" and "properties" in schema:
            return self._generate_object_schema(schema, schema_path)

        return self._generate_simple_type_schema(schema)

    def _generate_object_schema(self, schema: dict, schema_path: list[str]) -> type:
        """Generate a Pydantic model from the given object schema."""
        model_attributes = {}
        required_props = schema.get("required", [])
        for prop_name, prop_schema in schema["properties"].items():
            prop_type = self._generate_from_schema(
                prop_schema, [*schema_path, prop_name]
            )
            field_kwargs = {}
            if prop_name not in required_props:
                field_kwargs["default"] = None
                prop_type = prop_type | None
            if "description" in prop_schema:
                field_kwargs["description"] = prop_schema["description"]
            model_attributes[prop_name] = prop_type, Field(**field_kwargs)
        return create_model("__".join(schema_path), **model_attributes)

    @staticmethod
    def _generate_simple_type_schema(schema: dict) -> type:
        """Generate a type from the given simple (i.e. primitive) schema.
        Raises a ValueError if the schema type is not recognized."""
        format_to_python_type = {"date-time": datetime, "date": date}
        if "format" in schema and schema["format"] in format_to_python_type:
            return format_to_python_type[schema["format"]]

        type_to_python_type = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "object": dict,
        }
        if schema["type"] in type_to_python_type:
            return type_to_python_type[schema["type"]]

        raise ValueError(f"Type not supported: {schema.get('type')}")


response = requests.get(
    f"https://raw.githubusercontent.com/klaviyo/openapi/refs/heads/{KlaviyoAPI._REVISION}/openapi/stable.json"
)
response.raise_for_status()
model_generator = ModelGenerator(response.json())
