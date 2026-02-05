"""
Stub live connector: no network; raises LiveIODisabledError on fetch.
"""


class LiveIODisabledError(Exception):
    pass


class LiveConnectorStub:
    def fetch(self, *args, **kwargs):
        raise LiveIODisabledError("Live IO disabled")
