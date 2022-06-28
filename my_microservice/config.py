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

"""Config Parameter Modeling and Parsing"""

from ghga_service_chassis_lib.api import ApiConfigBase
from ghga_service_chassis_lib.config import config_from_yaml
from ghga_service_chassis_lib.postgresql import PostgresqlConfigBase
from ghga_service_chassis_lib.pubsub import PubSubConfigBase
from ghga_service_chassis_lib.s3 import S3ConfigBase

from .models import SupportedLanguages


# Please adapt config prefix and remove unnecessary config bases:
@config_from_yaml(prefix="my_microservice")
class Config(ApiConfigBase, PubSubConfigBase, PostgresqlConfigBase, S3ConfigBase):
    """Config parameters and their defaults."""

    service_name: str = "my_microservice"  # Please adapt
    language: SupportedLanguages = "Croatian"


CONFIG = Config()