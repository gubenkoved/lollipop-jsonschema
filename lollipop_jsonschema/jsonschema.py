__all__ = [
    'json_schema',
]


import lollipop.types as lt
import lollipop.validators as lv
from lollipop.utils import identity

from collections import OrderedDict
from .compat import iteritems


def find_validators(schema, validator_type):
    return [validator
            for validator in schema.validators
            if isinstance(validator, validator_type)]


def json_schema(schema):
    """Convert Lollipop schema to JSON schema"""
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
        js['items'] = json_schema(schema.item_type)

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
        js['items'] = [json_schema(item_type) for item_type in schema.item_types]
    elif isinstance(schema, lt.Object):
        js['type'] = 'object'
        js['properties'] = OrderedDict(
            (k, json_schema(v.field_type))
            for k, v in iteritems(schema.fields)
        )
        required = [
            k
            for k, v in iteritems(schema.fields)
            if not isinstance(v.field_type, lt.Optional)
        ]
        if required:
            js['required'] = required
        if schema.allow_extra_fields is not None:
            js['additionalProperties'] = schema.allow_extra_fields
    elif isinstance(schema, lt.Dict):
        js['type'] = 'object'
        fixed_properties = schema.value_types \
            if hasattr(schema.value_types, 'keys') else {}
        properties = OrderedDict(
            (k, json_schema(v))
            for k, v in iteritems(fixed_properties)
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
            js['additionalProperties'] = json_schema(schema.value_types.default)
    elif isinstance(schema, lt.Constant):
        js['const'] = schema.value
    elif isinstance(schema, lt.Optional):
        js.update(json_schema(schema.inner_type))
        default = schema.load_default()
        if default:
            js['default'] = schema.inner_type.dump(default)
    elif hasattr(schema, 'inner_type'):
        js.update(json_schema(schema.inner_type))

    return js
