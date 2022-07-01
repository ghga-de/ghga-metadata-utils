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
#
"""Test jsonschema validation"""
import json

from linkml_validator.validator import Validator

from ghga_metadata_utils.validation_plugins.jsonschema_validation import (
    GhgaJsonSchemaValidationPlugin,
)
from tests.fixtures.utils import BASE_DIR

SCHEMA_VERSION = "0.7.0"
CREATE_SCHEMA_URL_TEMPLATE = "https://raw.githubusercontent.com/ghga-de/ghga-metadata-schema/<VERSION>/artifacts/derived_schema/creation/ghga_creation.yaml"


def test_jsonschema_validation1():
    """Test a create submission JSON which is valid"""

    file_path = BASE_DIR / "test_data" / "submission.json"
    with open(file_path, encoding="utf-8") as file:
        data = json.load(file)
    if "schema_version" in data and data["schema_version"]:
        schema_version = data["schema_version"]
    else:
        schema_version = SCHEMA_VERSION
    create_schema_url = CREATE_SCHEMA_URL_TEMPLATE.replace("<VERSION>", schema_version)
    plugins = [
        {
            "plugin_class": GhgaJsonSchemaValidationPlugin,
            "args": {"include_range_class_descendants": True},
        }
    ]
    validator = Validator(schema=create_schema_url, plugins=plugins)
    report = validator.validate(data, target_class=data["schema_type"])
    messages = report.validation_results[0].validation_messages
    assert report.valid
    assert len(messages) == 0


def test_jsonschema_validation2():
    """Test a create submission JSON, which is invalid"""

    file_path = BASE_DIR / "test_data" / "invalid_submission.json"
    with open(file_path, encoding="utf-8") as file:
        data = json.load(file)
    if "schema_version" in data and data["schema_version"]:
        schema_version = data["schema_version"]
    else:
        schema_version = SCHEMA_VERSION
    create_schema_url = CREATE_SCHEMA_URL_TEMPLATE.replace("<VERSION>", schema_version)
    plugins = [
        {
            "plugin_class": GhgaJsonSchemaValidationPlugin,
            "args": {"include_range_class_descendants": True},
        }
    ]
    validator = Validator(schema=create_schema_url, plugins=plugins)
    report = validator.validate(data, target_class=data["schema_type"])
    messages = report.validation_results[0].validation_messages
    assert not report.valid
    assert len(messages) > 0
    assert "'alias' is a required property" in [x.message for x in messages]
