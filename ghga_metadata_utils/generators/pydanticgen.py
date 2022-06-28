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
from typing import TextIO, Union

import click
from jinja2 import Template
from linkml.generators.pydanticgen import (
    PydanticGenerator,
    _get_pyrange,
    default_template,
)
from linkml.utils.generator import shared_arguments
from linkml_runtime.linkml_model.meta import (
    Annotation,
    ClassDefinition,
    SchemaDefinition,
)
from linkml_runtime.utils.formatutils import camelcase, underscore
from linkml_runtime.utils.schemaview import SchemaView

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
{{ au.name }} = Annotated[Union[{{ ','.join(au.members) }}], Field(discriminator="{{au.discriminator_field}}")]
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
        self.reference_slots = set()
        self.annotated_unions = {}
        for slot in self.schema.slots:
            slot_alias_name = self.aliased_slot_name(slot)
            if (
                slot_alias_name.startswith("has ") or slot_alias_name == "main contact"
            ) and (slot_alias_name not in NON_REFERENCE_SLOTS):
                self.reference_slots.add(underscore(slot_alias_name))
        self.default_template = DEFAULT_TEMPLATE

    def serialize(self) -> str:
        """
        Serialize the schema to Pydantic models.

        The serialization is near identical to `PydanticGenerator.serialize`
        except for the following:
            - slots that are reference slots are made more permissible

        """
        sv = self.schemaview
        if self.template_file is not None:
            with open(self.template_file) as template_file:
                template_obj = Template(template_file.read())
        else:
            template_obj = Template(self.default_template)
        sv: SchemaView
        sv = self.schemaview
        schema = sv.schema
        pyschema = SchemaDefinition(
            id=schema.id,
            name=schema.name,
            description=schema.description.replace('"', '\\"'),
        )
        enums = self.generate_enums(sv.all_enums())
        sorted_classes = self.sort_classes(list(sv.all_classes().values()))
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
            for sn in sv.class_slots(class_name):
                s = deepcopy(sv.induced_slot(sn, class_name))
                s.name = underscore(s.name)
                if s.description:
                    s.description = s.description.replace('"', '\\"')
                class_def.attributes[s.name] = s
                collection_key = None
                if s.name == "schema_type":
                    # Treat schema_type as a specialized Literal field
                    pyrange = f'Literal["{class_def.name}"]'
                elif s.range in sv.all_classes():
                    range_cls = sv.get_class(s.range)
                    if range_cls.class_uri == "linkml:Any":
                        pyrange = "Any"
                    elif s.inlined or sv.get_identifier_slot(range_cls.name) is None:
                        pyrange_list = []
                        descendants = sv.class_descendants(s.range)
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
                            sv.get_identifier_slot(range_cls.name) is not None
                            and not s.inlined_as_list
                        ):
                            collection_type = "str"
                    else:
                        pyrange = "str"
                elif s.range in sv.all_enums():
                    pyrange = f"{camelcase(s.range)}"
                elif s.range in sv.all_types():
                    t = sv.get_type(s.range)
                    pyrange = _get_pyrange(t, sv)
                elif s.range is None:
                    pyrange = "str"
                else:
                    raise Exception(f"range: {s.range}")
                if s.multivalued:
                    if collection_key is None:
                        pyrange = f"List[{pyrange}]"
                    else:
                        pyrange = f"Dict[{collection_key}, {pyrange}]"

                # Making reference slots more permissible
                if s.name in self.reference_slots:
                    if ("[str]" not in pyrange) and (pyrange != "str"):
                        if s.multivalued:
                            pyrange = f"Union[{pyrange}, List[str]]"
                        else:
                            pyrange = f"Union[{pyrange}, str]"

                if not s.required and s.name != "schema_type":
                    pyrange = f"Optional[{pyrange}]"
                ann = Annotation("python_range", pyrange)
                s.annotations[ann.tag] = ann
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


@shared_arguments(GhgaPydanticGenerator)
@click.option(
    "--template_file", help="Optional jinja2 template to use for class generation"
)
@click.command()
def cli(
    yamlfile,
    template_file=None,
    head=True,
    emit_metadata=False,
    genmeta=False,
    classvars=True,
    slots=True,
    **args,
):
    """Generate pydantic classes to represent a LinkML model"""
    gen = GhgaPydanticGenerator(
        yamlfile,
        template_file=template_file,
        head=head,
        emit_metadata=emit_metadata,
        genmeta=genmeta,
        gen_classvars=classvars,
        gen_slots=slots,
        **args,
    )
    print(gen.serialize())


if __name__ == "__main__":
    cli()
