# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Custom GHGA-specific Validation Plugins"""

from typing import Dict

from linkml.utils.generator import Generator
from linkml_validator.plugins.jsonschema_validation import JsonSchemaValidationPlugin

from ghga_metadata_utils.generators.jsonschemagen import GhgaJsonSchemaGenerator


class GhgaJsonSchemaValidationPlugin(JsonSchemaValidationPlugin):
    """
    Plugin to perform JSONSchema validation for GHGA metadata records.

    This Plugin uses the GhgaJsonSchemaGenerator instead of the default.

    Args:
        schema: Path or URL to GHGA metadata schema YAML
        jsonschema_generator: A generator to use for generating the JSONSchema
        generator_args: Arguments to instantiate the generator specified in `jsonschema_generator`
        kwargs: Additional arguments that are used to instantiate the plugin

    """

    NAME = "GhgaJsonSchemaValidationPlugin"

    def __init__(
        self,
        schema: str,
        jsonschema_generator: Generator = GhgaJsonSchemaGenerator,
        generator_args: Dict = None,
        **kwargs
    ) -> None:
        super().__init__(
            schema=schema,
            jsonschema_generator=jsonschema_generator,
            generator_args=generator_args,
            **kwargs
        )
