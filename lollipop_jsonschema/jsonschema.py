__all__ = [
    'json_schema',
]

import lollipop.type_registry as lr
import lollipop.types as lt
import lollipop.validators as lv
from lollipop.utils import identity, is_mapping

from collections import OrderedDict, namedtuple
from .compat import itervalues, iteritems
import re


def find_validators(schema, validator_type):
    return [validator
            for validator in schema.validators
            if isinstance(validator, validator_type)]


class Definition(object):
    def __init__(self, name):
        self.name = name
        self.jsonschema = None


def _sanitize_name(name):
    valid_chars_name = re.sub('[^a-zA-Z0-9-_]+', ' ', name).strip()
    camel_cased_name = re.sub('[_ ]+([a-z])', lambda m: m.group(1).upper(),
                              valid_chars_name)
    return camel_cased_name


def json_schema(schema, definitions=None):
    """Convert Lollipop schema to JSON schema."""
    is_top_level_schema = definitions is None
    if definitions is None:
        definitions = {}

    definition_names = {definition.name for definition in itervalues(definitions)}

    counts = {}
    _count_schema_usages(schema, counts)

    for schema1, count in iteritems(counts):
        if count == 1:
            continue

        if schema1 not in definitions:
            def_name = _sanitize_name(schema1.name) if schema1.name else 'Type'

            if def_name in definition_names:
                i = 1
                while def_name + str(i) in definition_names:
                    i += 1
                def_name += str(i)

            definitions[schema1] = Definition(def_name)
            definition_names.add(def_name)

    for schema1, definition in iteritems(definitions):
        if definition.jsonschema is not None:
            continue

        definitions[schema1].jsonschema = _json_schema(
            schema1, definitions, force_render=True,
        )

    js = _json_schema(schema, definitions=definitions)
    if is_top_level_schema and definitions:
        js['definitions'] = {definition.name: definition.jsonschema
                             for definition in itervalues(definitions)}
    return js


def _count_schema_usages(schema, counts):
    if schema in counts:
        counts[schema] += 1
        return

    if isinstance(schema, lr.TypeRef):
        _count_schema_usages(schema.inner_type, counts)
        return

    counts[schema] = 1
    if isinstance(schema, lt.List):
        _count_schema_usages(schema.item_type, counts)
    elif isinstance(schema, lt.Tuple):
        for item_type in schema.item_types:
            _count_schema_usages(item_type, counts)
    elif isinstance(schema, lt.Object):
        for field in itervalues(schema.fields):
            _count_schema_usages(field.field_type, counts)

        if isinstance(schema.allow_extra_fields, lt.Field):
            _count_schema_usages(schema.allow_extra_fields.field_type, counts)
    elif isinstance(schema, lt.Dict):
        for _, value_type in iteritems(schema.value_types):
            _count_schema_usages(value_type, counts)
        if hasattr(schema.value_types, 'default'):
            _count_schema_usages(schema.value_types.default, counts)
    elif isinstance(schema, lt.OneOf):
        types = itervalues(schema.types) \
            if is_mapping(schema.types) else schema.types
        for item_type in types:
            _count_schema_usages(item_type, counts)
    elif hasattr(schema, 'inner_type'):
        _count_schema_usages(schema.inner_type, counts)


def _json_schema(schema, definitions, force_render=False):
    if schema in definitions and not force_render:
        return {'$ref': '#/definitions/' + definitions[schema].name}

    if isinstance(schema, lt.Modifier):
        js = _json_schema(schema.inner_type, definitions=definitions)
        if isinstance(schema, lt.Optional):
            default = schema.load_default()
            if default:
                js['default'] = schema.inner_type.dump(default)

        return js

    if isinstance(schema, lr.TypeRef):
        return _json_schema(schema.inner_type, definitions=definitions,
                            force_render=force_render)

    js = OrderedDict()
    if schema.name:
        js['title'] = schema.name
    if schema.description:
        js['description'] = schema.description

    any_of_validators = find_validators(schema, lv.AnyOf)
    if any_of_validators:
        choices = set(any_of_validators[0].choices)
        for validator in any_of_validators[1:]:
            choices = choices.intersection(set(validator.choices))

        if not choices:
            raise ValueError('AnyOf constraints choices does not allow any values')

        js['enum'] = list(schema.dump(choice) for choice in choices)

        return js

    none_of_validators = find_validators(schema, lv.NoneOf)
    if none_of_validators:
        choices = set(none_of_validators[0].values)
        for validator in none_of_validators[1:]:
            choices = choices.union(set(validator.values))

        if choices:
            js['not'] = {'enum': list(schema.dump(choice) for choice in choices)}

    if isinstance(schema, lt.Any):
        pass
    elif isinstance(schema, lt.String):
        js['type'] = 'string'

        length_validators = find_validators(schema, lv.Length)
        if length_validators:
            if any(v.min for v in length_validators) or \
                    any(v.exact for v in length_validators):
                js['minLength'] = max(v.exact or v.min for v in length_validators)
            if any(v.max for v in length_validators) or \
                    any(v.exact for v in length_validators):
                js['maxLength'] = min(v.exact or v.max for v in length_validators)

        regexp_validators = find_validators(schema, lv.Regexp)
        if regexp_validators:
            js['pattern'] = regexp_validators[0].regexp.pattern
    elif isinstance(schema, lt.Number):
        if isinstance(schema, lt.Integer):
            js['type'] = 'integer'
        else:
            js['type'] = 'number'

        range_validators = find_validators(schema, lv.Range)
        if range_validators:
            if any(v.min for v in range_validators):
                js['minimum'] = max(v.min for v in range_validators if v.min)
            if any(v.max for v in range_validators):
                js['maximum'] = min(v.max for v in range_validators if v.max)
    elif isinstance(schema, lt.Boolean):
        js['type'] = 'boolean'
    elif isinstance(schema, lt.List):
        js['type'] = 'array'
        js['items'] = _json_schema(schema.item_type, definitions=definitions)

        length_validators = find_validators(schema, lv.Length)
        if length_validators:
            if any(v.min for v in length_validators) or \
                    any(v.exact for v in length_validators):
                js['minItems'] = min(v.exact or v.min for v in length_validators)
            if any(v.max for v in length_validators) or \
                    any(v.exact for v in length_validators):
                js['maxItems'] = min(v.exact or v.max for v in length_validators)

        unique_validators = find_validators(schema, lv.Unique)
        if unique_validators and any(v.key is identity for v in unique_validators):
            js['uniqueItems'] = True
    elif isinstance(schema, lt.Tuple):
        js['type'] = 'array'
        js['items'] = [
            _json_schema(item_type, definitions=definitions)
            for item_type in schema.item_types
        ]
    elif isinstance(schema, lt.Object):
        js['type'] = 'object'
        js['properties'] = OrderedDict(
            (k, _json_schema(v.field_type, definitions=definitions))
            for k, v in iteritems(schema.fields)
        )
        required = [
            k
            for k, v in iteritems(schema.fields)
            if not isinstance(v.field_type, lt.Optional)
        ]
        if required:
            js['required'] = required
        if schema.allow_extra_fields in [True, False]:
            js['additionalProperties'] = schema.allow_extra_fields
        elif isinstance(schema.allow_extra_fields, lt.Field):
            field_type = schema.allow_extra_fields.field_type
            if isinstance(field_type, lt.Any):
                js['additionalProperties'] = True
            else:
                js['additionalProperties'] = _json_schema(field_type,
                                                          definitions=definitions)
    elif isinstance(schema, lt.Dict):
        js['type'] = 'object'
        properties = OrderedDict(
            (k, _json_schema(v, definitions=definitions))
            for k, v in iteritems(schema.value_types)
        )
        if properties:
            js['properties'] = properties
        required = [
            k
            for k, v in iteritems(fixed_properties)
            if not isinstance(v, lt.Optional)
        ]
        if required:
            js['required'] = required
        if hasattr(schema.value_types, 'default'):
            js['additionalProperties'] = _json_schema(
                schema.value_types.default, definitions=definitions)
    elif isinstance(schema, lt.OneOf):
        types = itervalues(schema.types) \
            if is_mapping(schema.types) else schema.types
        js['anyOf'] = [_json_schema(variant, definitions=definitions)
                       for variant in types]
    elif isinstance(schema, lt.Constant):
        js['const'] = schema.value

    return js
