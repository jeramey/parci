"""
Parameter storage for parci.
"""

from parci import config


class ParameterStoreException(Exception):
    """
    Some kind of parameter store error.
    """


class ParameterStoreInterceptor:
    """
    Presents the interface for all parameter store types
    and dynamically loads the appropriate implementation at
    first use.
    """

    def __init__(self):
        self._ps = None

    def _load_store(self):
        # pylint: disable=import-outside-toplevel
        if config.PARAMETER_DRIVER == "local":
            from .local import open_parameter_store

            self._ps = open_parameter_store()
        elif config.PARAMETER_DRIVER == "aws-ssm":
            from .aws import SSMParameterStore

            self._ps = SSMParameterStore()
        else:
            raise ValueError("config.PARAMETER_DRIVER is not a valid driver type")

    def __contains__(self, item):
        if self._ps is None:
            self._load_store()
        return self._ps.__contains__(item)

    def __getitem__(self, item):
        if self._ps is None:
            self._load_store()
        return self._ps.__getitem__(item)

    def __setitem__(self, key, value):
        if config.PARAMETER_READ_ONLY:
            raise ParameterStoreException("config.PARAMETER_READ_ONLY is set to true")
        if self._ps is None:
            self._load_store()
        self._ps.__setitem__(key, value)

    def __delitem__(self, key):
        if config.PARAMETER_READ_ONLY:
            raise ParameterStoreException("config.PARAMETER_READ_ONLY is set to true")
        if self._ps is None:
            self._load_store()
        self._ps.__delitem__(key)

    def keys(self):
        """
        Return a list of keys in the parameter store.
        """
        if self._ps is None:
            self._load_store()
        return self._ps.keys()

    def items(self):
        """
        Return a list of items in the parameter store.
        """
        if self._ps is None:
            self._load_store()
        return self._ps.items()

    def values(self):
        """
        Return a list of values in the parameter store.
        """
        if self._ps is None:
            self._load_store()
        return self._ps.values()


params = ParameterStoreInterceptor()
