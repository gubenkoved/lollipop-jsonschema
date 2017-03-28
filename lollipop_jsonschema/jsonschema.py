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
    elif hasattr(schema, 'inner_type'):
        return json_schema(schema.inner_type)

    return js
