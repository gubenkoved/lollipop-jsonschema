import sys

PY2 = int(sys.version_info[0]) == 2

if PY2:
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()
else:
    itervalues = lambda d: d.values()
    iteritems = lambda d: d.items()
