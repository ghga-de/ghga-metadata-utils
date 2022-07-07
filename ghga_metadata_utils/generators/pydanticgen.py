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
"""Custom GHGA-specific Pydantic Generators"""

from copy import deepcopy
from typing import Dict, Set, TextIO, Union

from jinja2 import Template
from linkml.generators.pydanticgen import PydanticGenerator, _get_pyrange
from linkml_runtime.linkml_model.meta import (
    Annotation,
    ClassDefinition,
    SchemaDefinition,
)
from linkml_runtime.utils.formatutils import camelcase, underscore
from linkml_runtime.utils.schemaview import SchemaView

# pylint: disable=no-value-for-parameter,too-many-arguments,too-many-branches,too-many-nested-blocks,too-many-locals,too-many-statements,redefined-builtin


NON_REFERENCE_SLOTS = {"has attribute", "has parameter", "has data use condition"}
DEFAULT_TEMPLATE = """
{#-

  Jinja2 Template for a pydantic classes
-#}
from __future__ import annotations
from enum import Enum
from typing import List, Optional, Union, Literal
from typing_extensions import Annotated
from pydantic import BaseModel, Field

metamodel_version = "{{metamodel_version}}"
version = "{{version if version else None}}"

{% for e in enums.values() %}
class {{ e.name }}(str, Enum):
    {% if e.description -%}
    \"\"\"
    {{ e.description }}
    \"\"\"
    {%- endif %}
    {% for label, value in e['values'].items() -%}
    {{label}} = "{{value}}"
    {% endfor %}
    {% if not e['values'] -%}
    dummy = "dummy"
    {% endif %}
{% endfor %}

{%- for c in schema.classes.values() %}
class {{ c.name }}
                   {%- if c.is_a %}({{c.is_a}}){%- else %}(BaseModel){% endif -%}
                   {#- {%- for p in c.mixins %}, "{{p}}" {% endfor -%} -#}
                  :
    {% if c.description -%}
    \"\"\"
    {{ c.description }}
    \"\"\"
    {%- endif %}
    {% for attr in c.attributes.values() if c.attributes -%}
    {%- if attr.name == "schema_type" -%}
    {{attr.name}}: {{ attr.annotations['python_range'].value }}
    {% else -%}
    {{attr.name}}: {{ attr.annotations['python_range'].value }} = Field(None
    {%- if attr.title != None %}, title="{{attr.title}}"{% endif -%}
    {%- if attr.description %}, description=\"\"\"{{attr.description}}\"\"\"{% endif -%}
    {%- if attr.minimum_value != None %}, ge={{attr.minimum_value}}{% endif -%}
    {%- if attr.maximum_value != None %}, le={{attr.maximum_value}}{% endif -%}
    )
    {% endif -%}
    {% else -%}
    None
    {% endfor %}

{% endfor %}


{% for au in annotated_unions.values() -%}
{{ au.name }} = Annotated[Union[{{ ','.join(au.members) }}],
Field(discriminator="{{au.discriminator_field}}")]
{% endfor %}

# Update forward refs
# see https://pydantic-docs.helpmanual.io/usage/postponed_annotations/
{% for c in schema.classes.values() -%}
{{ c.name }}.update_forward_refs()
{% endfor %}

"""


class GhgaPydanticGenerator(PydanticGenerator):
    """
    GhgaPydanticGenerator extends PydanticGenerator and adds the ability
    to make references slots more permissible.

    This generator was written to get across the limitation of not
    being able to express a slot to be both inlined and not inlined.

    Note: This is a temporary solution until https://github.com/linkml/linkml/issues/664
    is resolved.
    """

    valid_formats = PydanticGenerator.valid_formats

    def __init__(
        self,
        schema: Union[str, TextIO, SchemaDefinition],
        template_file: str = None,
        allow_extra=False,
        format: str = valid_formats[0],
        genmeta: bool = False,
        gen_classvars: bool = True,
        gen_slots: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(
            schema=schema,
            template_file=template_file,
            allow_extra=allow_extra,
            format=format,
            genmeta=genmeta,
            gen_classvars=gen_classvars,
            gen_slots=gen_slots,
            **kwargs,
        )
        self.reference_slots: Set = set()
        self.annotated_unions: Dict[str, Dict] = {}
        for slot in self.schema.slots:
            slot_alias_name = self.aliased_slot_name(slot)
            if (
                slot_alias_name.startswith("has ") or slot_alias_name == "main contact"
            ) and (slot_alias_name not in NON_REFERENCE_SLOTS):
                self.reference_slots.add(underscore(slot_alias_name))
        self.default_template = DEFAULT_TEMPLATE

    def serialize(self) -> str:  # noqa: C901
        """
        Serialize the schema to Pydantic models.

        The serialization is near identical to `PydanticGenerator.serialize`
        except for the following:
            - slots that are reference slots are made more permissible

        """
        schema_view: SchemaView = self.schemaview
        if self.template_file is not None:
            with open(self.template_file, encoding="utf-8") as template_file:
                template_obj = Template(template_file.read())
        else:
            template_obj = Template(self.default_template)
        schema = schema_view.schema
        pyschema = SchemaDefinition(
            id=schema.id,
            name=schema.name,
            description=schema.description.replace('"', '\\"'),
        )
        enums = self.generate_enums(schema_view.all_enums())
        sorted_classes = self.sort_classes(list(schema_view.all_classes().values()))
        sorted_classes = [c for c in sorted_classes if c.class_uri != "linkml:Any"]
        for class_original in sorted_classes:
            class_def: ClassDefinition
            class_def = deepcopy(class_original)
            class_name = class_original.name
            class_def.name = camelcase(class_original.name)
            if class_def.is_a:
                class_def.is_a = camelcase(class_def.is_a)
            class_def.mixins = [camelcase(p) for p in class_def.mixins]
            if class_def.description:
                class_def.description = class_def.description.replace('"', '\\"')
            pyschema.classes[class_def.name] = class_def
            for attribute in list(class_def.attributes.keys()):
                del class_def.attributes[attribute]
            for slot_name in schema_view.class_slots(class_name):
                slot = deepcopy(schema_view.induced_slot(slot_name, class_name))
                slot.name = underscore(slot.name)
                if slot.description:
                    slot.description = slot.description.replace('"', '\\"')
                class_def.attributes[slot.name] = slot
                collection_key = None
                if slot.name == "schema_type":
                    # Treat schema_type as a specialized Literal field
                    pyrange = f'Literal["{class_def.name}"]'
                elif slot.range in schema_view.all_classes():
                    range_cls = schema_view.get_class(slot.range)
                    if range_cls.class_uri == "linkml:Any":
                        pyrange = "Any"
                    elif (
                        slot.inlined
                        or schema_view.get_identifier_slot(range_cls.name) is None
                    ):
                        pyrange_list = []
                        descendants = schema_view.class_descendants(slot.range)
                        for descendant in reversed(descendants):
                            pyrange_list.append(f"{camelcase(descendant)}")
                        pyrange = ",".join(pyrange_list)
                        if len(pyrange_list) > 1:
                            annotated_union_name = camelcase(
                                f"annotated {descendants[0]}"
                            )
                            if annotated_union_name not in self.annotated_unions:
                                annotated_union = {
                                    "name": annotated_union_name,
                                    "discriminator_field": "schema_type",
                                }
                                annotated_union_members = [
                                    f"{camelcase(x)}" for x in pyrange_list
                                ]
                                annotated_union["members"] = annotated_union_members
                                self.annotated_unions[
                                    annotated_union_name
                                ] = annotated_union
                            pyrange = f"{annotated_union_name}"
                        if (
                            schema_view.get_identifier_slot(range_cls.name) is not None
                            and not slot.inlined_as_list
                        ):
                            pyrange = "str"
                    else:
                        pyrange = "str"
                elif slot.range in schema_view.all_enums():
                    pyrange = f"{camelcase(slot.range)}"
                elif slot.range in schema_view.all_types():
                    range_type = schema_view.get_type(slot.range)
                    pyrange = _get_pyrange(range_type, schema_view)
                elif slot.range is None:
                    pyrange = "str"
                else:
                    raise Exception(f"range: {slot.range}")
                if slot.multivalued:
                    if collection_key is None:
                        pyrange = f"List[{pyrange}]"
                    else:
                        pyrange = f"Dict[{collection_key}, {pyrange}]"

                # Making reference slots more permissible
                if slot.name in self.reference_slots:
                    if ("[str]" not in pyrange) and (pyrange != "str"):
                        if slot.multivalued:
                            pyrange = f"Union[{pyrange}, List[str]]"
                        else:
                            pyrange = f"Union[{pyrange}, str]"

                if not slot.required and slot.name != "schema_type":
                    pyrange = f"Optional[{pyrange}]"
                ann = Annotation("python_range", pyrange)
                slot.annotations[ann.tag] = ann
        code = template_obj.render(
            schema=pyschema,
            annotated_unions=self.annotated_unions,
            underscore=underscore,
            enums=enums,
            allow_extra=self.allow_extra,
            metamodel_version=self.schema.metamodel_version,
            version=self.schema.version,
        )
        return code
