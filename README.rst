*******************
lollipop-jsonschema
*******************

.. image:: https://img.shields.io/pypi/l/lollipop-jsonschema.svg
    :target: https://github.com/maximkulkin/lollipop-jsonschema/blob/master/LICENSE
    :alt: License: MIT

.. image:: https://img.shields.io/travis/maximkulkin/lollipop-jsonschema.svg
    :target: https://travis-ci.org/maximkulkin/lollipop-jsonschema
    :alt: Build Status

.. image:: https://img.shields.io/pypi/v/lollipop-jsonschema.svg
    :target: https://pypi.python.org/pypi/lollipop-jsonschema
    :alt: PyPI

Library to convert `Lollipop schema <https://github.com/maximkulkin/lollipop>`_
to `JSON schema <http://json-schema.org>`_.

Example
=======
.. code:: python

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
    # {
    #   "title": "User",
    #   "description": "User information",
    #   "type": "object",
    #   "properties": {
    #     "age": {
    #       "type": "integer",
    #       "minimum": 18
    #     },
    #     "name": {
    #       "type": "string",
    #       "minLength": 1
    #     },
    #     "email": {
    #       "type": "string",
    #       "pattern": "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"
    #     }
    #   },
    #   "required": [
    #     "name",
    #     "email"
    #   ]
    # }

Installation
============
::

    $ pip install lollipop-jsonschema

Requirements
============

- Python >= 2.7 and <= 3.6
- `lollipop <https://pypi.python.org/pypi/lollipop>`_ >= 1.1.2

Project Links
=============

- PyPI: https://pypi.python.org/pypi/lollipop-jsonschema
- Issues: https://github.com/maximkulkin/lollipop-jsonschema/issues

License
=======

MIT licensed. See the bundled `LICENSE <https://github.com/maximkulkin/lollipop-jsconschema/blob/master/LICENSE>`_ file for more details.
