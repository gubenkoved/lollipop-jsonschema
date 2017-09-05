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


class JsonSchemaContext(object):
    def __init__(self, definitions=None, mode=None):
        if mode is not None and mode not in ['load', 'dump']:
            raise ValueError('Invlaid mode: %s' % mode)

        self.definitions = definitions if definitions is not None else {}
        self.mode = mode


def json_schema(schema, definitions=None, mode=None):
    """Convert Lollipop schema to JSON schema."""
    is_top_level_schema = definitions is None
    context = JsonSchemaContext(definitions=definitions, mode=mode)

    definition_names = {definition.name
                        for definition in itervalues(context.definitions)}

    counts = {}
    _count_schema_usages(schema, counts)

    for schema1, count in iteritems(counts):
        if count == 1:
            continue

        if schema1 not in context.definitions:
            def_name = _sanitize_name(schema1.name) if schema1.name else 'Type'

            if def_name in definition_names:
                i = 1
                while def_name + str(i) in definition_names:
                    i += 1
                def_name += str(i)

            context.definitions[schema1] = Definition(def_name)
            definition_names.add(def_name)

    for schema1, definition in iteritems(context.definitions):
        if definition.jsonschema is not None:
            continue

        context.definitions[schema1].jsonschema = _json_schema(
            schema1, context, force_render=True,
        )

    js = _json_schema(schema, context=context)
    if is_top_level_schema and context.definitions:
        js['definitions'] = {definition.name: definition.jsonschema
                             for definition in itervalues(context.definitions)}
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


def has_modifier(schema, modifier):
    while isinstance(schema, (lt.Modifier, lr.TypeRef)):
        if isinstance(schema, modifier):
            return True
        schema = schema.inner_type
    return False


def is_optional(schema):
    return has_modifier(schema, lt.Optional)


def is_dump_schema(schema):
    return not has_modifier(schema, lt.LoadOnly)


def is_load_schema(schema):
    return not has_modifier(schema, lt.DumpOnly)


def is_type(schema, schema_type):
    while isinstance(schema, (lt.Modifier, lr.TypeRef)):
        schema = schema.inner_type
    return isinstance(schema, schema_type)


def _json_schema(schema, context, force_render=False):
    if schema in context.definitions and not force_render:
        return {'$ref': '#/definitions/' + context.definitions[schema].name}

    if isinstance(schema, lt.Modifier):
        js = _json_schema(schema.inner_type, context=context)
        if js is None:
            return None

        if isinstance(schema, lt.Optional):
            default = schema.load_default()
            if default is None:
                js['default'] = None
            elif default is not lt.MISSING:
                js['default'] = schema.inner_type.dump(default)
        elif context.mode and (
                (context.mode == 'dump' and not is_dump_schema(schema)) or
                (context.mode == 'load' and not is_load_schema(schema))
        ):
            return None

        return js

    if isinstance(schema, lr.TypeRef):
        return _json_schema(schema.inner_type, context=context,
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
        item_schema = _json_schema(schema.item_type, context=context)
        if item_schema is None:
            js['maxItems'] = 0
        else:
            js['items'] = item_schema
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
        items_schema = [
            item_schema
            for item_type in schema.item_types
            for item_schema in [_json_schema(item_type, context=context)]
            if item_schema is not None
        ]
        if not items_schema:
            js['maxItems'] = 0
        else:
            js['items'] = items_schema
    elif isinstance(schema, lt.Object):
        js['type'] = 'object'
        properties = OrderedDict(
            (field_name, field_schema)
            for field_name, field in iteritems(schema.fields)
            for field_schema in [_json_schema(field.field_type, context=context)]
            if field_schema is not None
        )
        if properties:
            js['properties'] = properties

            required = [
                field_name
                for field_name, field in iteritems(schema.fields)
                if not is_optional(field.field_type) and field_name in js['properties']
            ]
            if required:
                js['required'] = required

        if schema.allow_extra_fields in [True, False]:
            js['additionalProperties'] = schema.allow_extra_fields
        elif isinstance(schema.allow_extra_fields, lt.Field):
            field_type = schema.allow_extra_fields.field_type
            field_schema = _json_schema(field_type, context=context)
            if field_schema is not None:
                if is_type(field_type, lt.Any):
                    js['additionalProperties'] = True
                else:
                    js['additionalProperties'] = field_schema

        if not js.get('properties') and not js.get('additionalProperties'):
            js['maxProperties'] = 0
    elif isinstance(schema, lt.Dict):
        js['type'] = 'object'
        properties = OrderedDict(
            (k, value_schema)
            for k, v in iteritems(schema.value_types)
            for value_schema in [_json_schema(v, context=context)]
            if value_schema is not None
        )
        if properties:
            js['properties'] = properties
        required = [
            k
            for k, v in iteritems(schema.value_types)
            if not is_optional(v) and k in properties
        ]
        if required:
            js['required'] = required
        if hasattr(schema.value_types, 'default'):
            additional_schema = _json_schema(
                schema.value_types.default, context=context,
            )
            if additional_schema is not None:
                js['additionalProperties'] = additional_schema

        if not js.get('properties') and not js.get('additionalProperties'):
            js['maxProperties'] = 0
    elif isinstance(schema, lt.OneOf):
        types = itervalues(schema.types) \
            if is_mapping(schema.types) else schema.types
        js['anyOf'] = [
            variant_schema
            for variant in types
            for variant_schema in [_json_schema(variant, context=context)]
            if variant_schema is not None
        ]
        if not js['anyOf']:
            return None
    elif isinstance(schema, lt.Constant):
        js['const'] = schema.value

    return js
