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

from linkml.utils.generator import Generator
from linkml_validator.plugins.jsonschema_validation import JsonschemaValidationPlugin

from ghga_metadata_utils.generators.jsonschemagen import GhgaJsonSchemaGenerator


class GhgaJsonschemaValidationPlugin(JsonschemaValidationPlugin):
    """
    Plugin to perform JSONSchema validation for GHGA metadata records.

    This Plugin uses the GhgaJsonSchemaGenerator instead of the Default

    Args:
        schema: Path or URL to GHGA metadata schema YAML
        kwargs: Additional arguments

    """

    NAME = "GhgaJsonschemaValidationPlugin"

    def __init__(
        self,
        schema: str,
        jsonschema_generator: Generator = GhgaJsonSchemaGenerator,
        **kwargs
    ) -> None:
        super().__init__(schema=schema, jsonschema_generator=jsonschema_generator)
