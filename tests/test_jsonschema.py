import lollipop.type_registry as lr
import lollipop.types as lt
import lollipop.validators as lv
from lollipop.utils import is_mapping
from lollipop_jsonschema import json_schema
from lollipop_jsonschema.compat import iteritems
import pytest
from collections import namedtuple


def sorted_dicts(items):
    def normalize(v):
        return [(k, normalize(v)) for k, v in v.items()] if is_mapping(v) else v
    return sorted(items, key=normalize)


class TestJsonSchema:
    def test_string_schema(self):
        assert json_schema(lt.String()) == {'type': 'string'}

    def test_string_minLength(self):
        assert json_schema(lt.String(validate=lv.Length(min=1))) == \
            {'type': 'string', 'minLength': 1}

    def test_string_maxLength(self):
        assert json_schema(lt.String(validate=lv.Length(max=10))) == \
            {'type': 'string', 'maxLength': 10}

    def test_string_min_and_maxLength(self):
        assert json_schema(lt.String(validate=lv.Length(min=1, max=10))) == \
            {'type': 'string', 'minLength': 1, 'maxLength': 10}

    def test_string_exact_length(self):
        assert json_schema(lt.String(validate=lv.Length(exact=5))) == \
            {'type': 'string', 'minLength': 5, 'maxLength': 5}

    def test_string_pattern(self):
        assert json_schema(lt.String(validate=lv.Regexp('[a-z0-9]+'))) == \
            {'type': 'string', 'pattern': '[a-z0-9]+'}

    def test_number_schema(self):
        assert json_schema(lt.Float()) == {'type': 'number'}

    def test_number_minimum(self):
        assert json_schema(lt.Float(validate=lv.Range(min=2))) == \
            {'type': 'number', 'minimum': 2}

    def test_number_maximum(self):
        assert json_schema(lt.Float(validate=lv.Range(max=10))) == \
            {'type': 'number', 'maximum': 10}

    def test_number_minimum_and_maximum(self):
        assert json_schema(lt.Float(validate=lv.Range(min=1, max=10))) == \
            {'type': 'number', 'minimum': 1, 'maximum': 10}

    def test_integer_schema(self):
        assert json_schema(lt.Integer()) == {'type': 'integer'}

    def test_integer_minimum(self):
        assert json_schema(lt.Integer(validate=lv.Range(min=2))) == \
            {'type': 'integer', 'minimum': 2}

    def test_integer_maximum(self):
        assert json_schema(lt.Integer(validate=lv.Range(max=10))) == \
            {'type': 'integer', 'maximum': 10}

    def test_integer_minimum_and_maximum(self):
        assert json_schema(lt.Integer(validate=lv.Range(min=1, max=10))) == \
            {'type': 'integer', 'minimum': 1, 'maximum': 10}

    def test_boolean_schema(self):
        assert json_schema(lt.Boolean()) == {'type': 'boolean'}

    def test_list_schema(self):
        assert json_schema(lt.List(lt.String())) == \
            {'type': 'array', 'items': {'type': 'string'}}

    def test_list_minItems(self):
        assert json_schema(lt.List(lt.String(), validate=lv.Length(min=1))) == \
            {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1}

    def test_list_maxItems(self):
        assert json_schema(lt.List(lt.String(), validate=lv.Length(max=10))) == \
            {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 10}

    def test_list_min_and_maxItems(self):
        assert json_schema(lt.List(lt.String(),
                                   validate=lv.Length(min=1, max=10))) == \
            {'type': 'array', 'items': {'type': 'string'},
             'minItems': 1, 'maxItems': 10}

    def test_list_uniqueItems(self):
        assert json_schema(lt.List(lt.String(), validate=lv.Unique())) == \
            {'type': 'array', 'items': {'type': 'string'}, 'uniqueItems': True}

    def test_tuple_schema(self):
        assert json_schema(lt.Tuple([lt.String(), lt.Integer(), lt.Boolean()])) == \
            {'type': 'array', 'items': [
                {'type': 'string'},
                {'type': 'integer'},
                {'type': 'boolean'},
            ]}

    def test_object_schema(self):
        result = json_schema(lt.Object({'foo': lt.String(), 'bar': lt.Integer()}))

        assert len(result) == 3
        assert result['type'] == 'object'
        assert result['properties'] == {
            'foo': {'type': 'string'},
            'bar': {'type': 'integer'},
        }
        assert sorted(result['required']) == sorted(['foo', 'bar'])

    def test_object_optional_fields(self):
        result = json_schema(lt.Object({'foo': lt.String(),
                                        'bar': lt.Optional(lt.Integer())}))
        assert 'bar' not in result['required']

    def test_object_optional_fields_wrapped_in_other_modifiers(self):
        result = json_schema(lt.Object({
            'foo': lt.String(),
            'bar': lt.DumpOnly(lt.Optional(lt.Integer())),
        }))
        assert 'bar' not in result['required']

    def test_object_all_optional_fields(self):
        result = json_schema(lt.Object({'foo': lt.Optional(lt.String()),
                                        'bar': lt.Optional(lt.Integer())}))
        assert 'required' not in result

    def test_object_no_allow_extra_fields(self):
        result = json_schema(lt.Object({
            'foo': lt.String(), 'bar': lt.Integer(),
        }))

        assert 'additionalProperties' not in result

    def test_object_allow_extra_fields_true(self):
        result = json_schema(lt.Object({
            'foo': lt.String(), 'bar': lt.Integer(),
        }, allow_extra_fields=True))

        assert result['additionalProperties'] == True

    def test_object_allow_extra_fields_any(self):
        result = json_schema(lt.Object({
            'foo': lt.String(), 'bar': lt.Integer(),
        }, allow_extra_fields=lt.Any()))

        assert result['additionalProperties'] == True

    def test_object_allow_extra_fields_false(self):
        result = json_schema(lt.Object({
            'foo': lt.String(), 'bar': lt.Integer(),
        }, allow_extra_fields=False))

        assert result['additionalProperties'] == False

    def test_object_allow_extra_fields_type(self):
        result = json_schema(lt.Object({
            'foo': lt.String(), 'bar': lt.Integer(),
        }, allow_extra_fields=lt.Object({
            'bar': lt.String(), 'foo': lt.Integer(),
        })))

        additional = result['additionalProperties']
        assert additional['type'] == 'object'
        assert additional['properties'] == {
            'foo': {'type': 'integer'},
            'bar': {'type': 'string'},
        }

    def test_fixed_fields_dict_schema(self):
        result = json_schema(lt.Dict({'foo': lt.String(), 'bar': lt.Integer()}))

        assert len(result) == 3
        assert result['type'] == 'object'
        assert result['properties'] == {
            'foo': {'type': 'string'},
            'bar': {'type': 'integer'},
        }
        assert sorted(result['required']) == sorted(['foo', 'bar'])

    def test_variadic_fields_dict_schema(self):
        result = json_schema(lt.Dict(lt.Integer()))

        assert len(result) == 2
        assert result['type'] == 'object'
        assert result['additionalProperties'] == {'type': 'integer'}

    def test_fixed_fields_dict_optional_fields(self):
        result = json_schema(lt.Dict({'foo': lt.String(),
                                      'bar': lt.Optional(lt.Integer())}))
        assert 'bar' not in result['required']

    def test_fixed_fields_dict_all_optional_fields(self):
        result = json_schema(lt.Dict({'foo': lt.Optional(lt.String()),
                                      'bar': lt.Optional(lt.Integer())}))
        assert 'required' not in result

    def test_schema_title(self):
        assert json_schema(lt.String(name='My string'))['title'] == 'My string'
        assert json_schema(lt.Integer(name='My integer'))['title'] == 'My integer'
        assert json_schema(lt.Float(name='My float'))['title'] == 'My float'
        assert json_schema(lt.Boolean(name='My boolean'))['title'] == 'My boolean'

    def test_schema_description(self):
        assert json_schema(lt.String(description='My description'))['description'] \
            == 'My description'
        assert json_schema(lt.Integer(description='My description'))['description'] \
            == 'My description'
        assert json_schema(lt.Float(description='My description'))['description'] \
            == 'My description'
        assert json_schema(lt.Boolean(description='My description'))['description'] \
            == 'My description'

    def test_type_with_any_of_validator_is_dumped_as_enum(self):
        jschema = json_schema(lt.String(validate=lv.AnyOf(['foo', 'bar', 'baz'])))
        assert len(jschema) == 1
        assert sorted(jschema['enum']) == sorted(['foo', 'bar', 'baz'])

        jschema = json_schema(lt.Integer(validate=lv.AnyOf([1, 2, 3])))
        assert len(jschema) == 1
        assert sorted(jschema['enum']) == sorted([1, 2, 3])

    def test_type_with_any_of_validator_values_are_serialized(self):
        MyType = namedtuple('MyType', ['foo', 'bar'])

        MY_TYPE = lt.Object(
            {'foo': lt.String(), 'bar': lt.Integer()},
            validate=lv.AnyOf([MyType('hello', 1), MyType('goodbye', 2)]),
        )
        jschema = json_schema(MY_TYPE)

        assert sorted(jschema['enum'], key=lambda d: sorted(d.items())) == \
            [{'foo': 'hello', 'bar': 1}, {'foo': 'goodbye', 'bar': 2}]

    def test_type_with_multiple_any_of_validators(self):
        jschema = json_schema(
            lt.String(validate=[
                lv.AnyOf(['foo', 'bar', 'baz']),
                lv.AnyOf(['bar', 'baz', 'bam']),
            ])
        )

        assert len(jschema) == 1
        assert sorted(jschema['enum']) == sorted(['bar', 'baz'])

    def test_type_with_none_of_validator_is_dumped_as_not_enum(self):
        jschema = json_schema(lt.String(validate=lv.NoneOf(['foo', 'bar', 'baz'])))
        assert 'not' in jschema
        assert len(jschema['not']) == 1
        assert sorted(jschema['not']['enum']) == sorted(['foo', 'bar', 'baz'])

        jschema = json_schema(lt.Integer(validate=lv.NoneOf([1, 2, 3])))
        assert 'not' in jschema
        assert len(jschema['not']) == 1
        assert sorted(jschema['not']['enum']) == sorted([1, 2, 3])

    def test_type_with_none_of_validator_values_are_serialized(self):
        MyType = namedtuple('MyType', ['foo', 'bar'])

        MY_TYPE = lt.Object(
            {'foo': lt.String(), 'bar': lt.Integer()},
            validate=lv.NoneOf([MyType('hello', 1), MyType('goodbye', 2)]),
        )
        jschema = json_schema(MY_TYPE)

        assert sorted(jschema['not']['enum'], key=lambda d: sorted(d.items())) == \
            [{'foo': 'hello', 'bar': 1}, {'foo': 'goodbye', 'bar': 2}]

    def test_type_with_multiple_none_of_validators(self):
        jschema = json_schema(
            lt.String(validate=[
                lv.NoneOf(['foo', 'bar', 'baz']),
                lv.NoneOf(['bar', 'baz', 'bam']),
            ])
        )

        assert sorted(jschema['not']['enum']) == sorted(['foo', 'bar', 'baz', 'bam'])

    def test_constant(self):
        assert json_schema(lt.Constant('foo')) == {'const': 'foo'}
        assert json_schema(lt.Constant(123)) == {'const': 123}

    def test_optional_schema_is_its_inner_type_schema(self):
        assert json_schema(lt.Optional(lt.String())) == json_schema(lt.String())
        assert json_schema(lt.Optional(lt.Integer())) == json_schema(lt.Integer())

    def test_optional_load_default_is_used_as_default(self):
        assert json_schema(lt.Optional(lt.String(), load_default='foo')) \
            == {'type': 'string', 'default': 'foo'}

    def test_optional_load_default_value_is_serialized(self):
        MyType = namedtuple('MyType', ['foo', 'bar'])

        result = json_schema(lt.Optional(lt.Object({
            'foo': lt.String(), 'bar': lt.Integer(),
        }), load_default=MyType('hello', 123)))

        assert result['default'] == {'foo': 'hello', 'bar': 123}

    def test_one_of_schema_with_sequence(self):
        t1 = lt.String()
        t2 = lt.Integer()
        t3 = lt.Boolean()
        result = json_schema(lt.OneOf([t1, t2, t3]))

        assert sorted(['anyOf']) == sorted(result.keys())
        assert sorted_dicts([json_schema(t) for t in [t1, t2, t3]]) == \
            sorted_dicts(result['anyOf'])

    def test_one_of_schema_with_mapping(self):
        Foo = namedtuple('Foo', ['foo'])
        Bar = namedtuple('Bar', ['bar'])

        FOO_SCHEMA = lt.Object({'type': 'Foo', 'foo': lt.String()})
        BAR_SCHEMA = lt.Object({'type': 'Bar', 'bar': lt.Integer()})

        result = json_schema(lt.OneOf({'Foo': FOO_SCHEMA, 'Bar': BAR_SCHEMA},
                                      load_hint=lt.dict_value_hint('type'),
                                      dump_hint=lt.type_name_hint))

        assert sorted(['anyOf']) == sorted(result.keys())
        assert sorted_dicts([json_schema(FOO_SCHEMA), json_schema(BAR_SCHEMA)]) == \
            sorted_dicts(result['anyOf'])

    def test_no_definitions_if_no_duplicate_types(self):
        result = json_schema(lt.Object({'foo': lt.String(), 'bar': lt.String()}))

        assert 'definitions' not in result

    def test_duplicate_types_in_objects_are_extracted_to_definitions(self):
        type1 = lt.String(name='MyString')
        result = json_schema(lt.Object({'foo': type1, 'bar': type1}))

        assert 'definitions' in result
        assert result['definitions'] == {'MyString': json_schema(type1)}
        assert result['properties']['foo'] == {'$ref': '#/definitions/MyString'}
        assert result['properties']['bar'] == {'$ref': '#/definitions/MyString'}

    def test_duplicate_types_in_objects_extra_fields_are_extracted_to_definitions(self):
        type1 = lt.String(name='MyString')
        result = json_schema(lt.Object({'foo': type1}, allow_extra_fields=type1))

        assert 'definitions' in result
        assert result['definitions'] == {'MyString': json_schema(type1)}
        assert result['properties']['foo'] == {'$ref': '#/definitions/MyString'}
        assert result['additionalProperties'] == {'$ref': '#/definitions/MyString'}

    def test_duplicate_types_in_lists_are_extracted_to_definitions(self):
        type1 = lt.String(name='MyString')
        result = json_schema(lt.Object({'foo': type1,
                                        'bar': lt.List(type1)}))

        assert 'definitions' in result
        assert result['definitions'] == {'MyString': json_schema(type1)}
        assert result['properties']['foo'] == {'$ref': '#/definitions/MyString'}
        assert result['properties']['bar']['items'] == \
            {'$ref': '#/definitions/MyString'}

    def test_duplicate_types_in_dicts_are_extracted_to_definitions(self):
        type1 = lt.String(name='MyString')
        result = json_schema(lt.Object({'foo': type1,
                                        'bar': lt.Dict({'baz': type1})}))

        assert 'definitions' in result
        assert result['definitions'] == {'MyString': json_schema(type1)}
        assert result['properties']['foo'] == {'$ref': '#/definitions/MyString'}
        assert result['properties']['bar']['properties']['baz'] == \
            {'$ref': '#/definitions/MyString'}

    def test_duplicate_types_in_dicts_default_are_extracted_to_definitions(self):
        type1 = lt.String(name='MyString')
        result = json_schema(lt.Object({'foo': type1,
                                        'bar': lt.Dict(type1)}))

        assert 'definitions' in result
        assert result['definitions'] == {'MyString': json_schema(type1)}
        assert result['properties']['foo'] == {'$ref': '#/definitions/MyString'}
        assert result['properties']['bar']['additionalProperties'] == \
            {'$ref': '#/definitions/MyString'}

    def test_duplicate_types_in_one_of_are_extracted_to_definitions(self):
        type1 = lt.String(name='MyString')
        result = json_schema(lt.Object({'foo': type1,
                                        'bar': lt.OneOf([type1, lt.Integer()])}))

        assert 'definitions' in result
        assert result['definitions'] == {'MyString': json_schema(type1)}
        assert result['properties']['foo'] == {'$ref': '#/definitions/MyString'}
        assert result['properties']['bar']['anyOf'][0] == \
            {'$ref': '#/definitions/MyString'}

    def test_duplicate_types_in_optional_are_extracted_to_definitions(self):
        type1 = lt.String(name='MyString')
        result = json_schema(lt.Object({'foo': type1,
                                        'bar': lt.Optional(type1)}))

        assert 'definitions' in result
        assert result['definitions'] == {'MyString': json_schema(type1)}
        assert result['properties']['foo'] == {'$ref': '#/definitions/MyString'}
        assert result['properties']['bar'] == {'$ref': '#/definitions/MyString'}
        assert 'bar' not in result['required']

    def test_type_references(self):
        registry = lr.TypeRegistry()

        type1 = lt.String(name='MyString')
        type1_ref = registry.add('AString', type1)

        assert json_schema(type1_ref) == json_schema(type1)

    def test_duplicate_type_references_are_extracted_to_definitions(self):
        registry = lr.TypeRegistry()

        type1 = lt.String(name='MyString')
        type1_ref = registry.add('AString', type1)

        result = json_schema(lt.Object({'foo': type1_ref, 'bar': type1_ref}))
        assert 'definitions' in result
        assert result['definitions'] == {'MyString': json_schema(type1)}
        assert result['properties']['foo'] == {'$ref': '#/definitions/MyString'}
        assert result['properties']['bar'] == {'$ref': '#/definitions/MyString'}

    def test_duplicate_type_and_type_references_are_extracted_to_definitions(self):
        registry = lr.TypeRegistry()

        type1 = lt.String(name='MyString')
        type1_ref = registry.add('AString', type1)

        result = json_schema(lt.Object({'foo': type1, 'bar': type1_ref}))
        assert 'definitions' in result
        assert result['definitions'] == {'MyString': json_schema(type1)}
        assert result['properties']['foo'] == {'$ref': '#/definitions/MyString'}
        assert result['properties']['bar'] == {'$ref': '#/definitions/MyString'}

    def test_self_referencing_types(self):
        registry = lr.TypeRegistry()
        errors_type = registry.add('Errors', lt.Dict(
            lt.OneOf([lt.String(), lt.List(lt.String()), registry['Errors']]),
            name='Errors',
        ))

        result = json_schema(errors_type)

        assert sorted(result.keys()) == sorted(['definitions', '$ref'])

        assert 'Errors' in result['definitions']
        errorsDef = result['definitions']['Errors']
        assert errorsDef['title'] == 'Errors'
        assert errorsDef['type'] == 'object'
        assert errorsDef['additionalProperties'] == {
            'anyOf': [
                json_schema(lt.String()),
                json_schema(lt.List(lt.String())),
                {'$ref': '#/definitions/Errors'},
            ]
        }

        assert result['$ref'] == '#/definitions/Errors'

    def test_definition_name_sanitization(self):
        type1 = lt.String(name='My string!')

        result = json_schema(lt.Object({'foo': type1, 'bar': type1}))
        assert result['definitions'] == {'MyString': json_schema(type1)}

    def test_definition_name_conflict_resolving(self):
        type1 = lt.String(name='MyType')
        type2 = lt.Integer(name='MyType')
        type3 = lt.Boolean(name='MyType')

        result = json_schema(lt.Object({
            'field1': type1, 'field2': type2, 'field3': type3,
            'field4': type1, 'field5': type2, 'field6': type3,
        }))
        refs = [
            '#/definitions/MyType',
            '#/definitions/MyType1',
            '#/definitions/MyType2',
        ]
        assert result['properties']['field1']['$ref'] in refs
        assert result['properties']['field2']['$ref'] in refs
        assert result['properties']['field3']['$ref'] in refs
        assert len(set(result['properties'][field]['$ref']
                       for field in ['field1', 'field2', 'field3'])) == 3

    def test_unnamed_types_definition_name_conflict_resolving(self):
        type1 = lt.String()
        type2 = lt.Integer()
        type3 = lt.Integer()

        result = json_schema(lt.Object({
            'field1': type1, 'field2': type2, 'field3': type3,
            'field4': type1, 'field5': type2, 'field6': type3,
        }))
        refs = [
            '#/definitions/Type',
            '#/definitions/Type1',
            '#/definitions/Type2',
        ]
        assert result['properties']['field1']['$ref'] in refs
        assert result['properties']['field2']['$ref'] in refs
        assert result['properties']['field3']['$ref'] in refs
        assert len(set(result['properties'][field]['$ref']
                       for field in ['field1', 'field2', 'field3'])) == 3
