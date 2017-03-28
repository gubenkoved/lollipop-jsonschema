import lollipop.types as lt
import lollipop.validators as lv

EMAIL_REGEXP = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

USER = lt.Object({
    'name': lt.String(validate=lv.Length(min=1)),
    'email': lt.String(validate=lv.Regexp(EMAIL_REGEXP)),
    'age': lt.Optional(lt.Integer(validate=lv.Range(min=18))),
}, name='User', description='User information')


from lollipop_jsonschema import json_schema
import json

print json.dumps(json_schema(USER), indent=2)
