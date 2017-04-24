#: our package version
__version__ = '0.0.1'

#: set of shared actors implementing various state-machines
actors = {}


class bag(dict):
    """
    Placeholder we pass across states in the fsm (e.g that *data* parameter) with some extra attributes.
    """
    pass
