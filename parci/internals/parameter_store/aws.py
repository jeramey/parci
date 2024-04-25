"""
AWS parameter storage interfaces.
"""

import json
import os


import boto3

from parci import config


class SSMParameterStoreException(Exception):
    """An SSM parameter store exception"""


class SSMParameterStore:
    """
    An AWS SSM Parameter Store backed params implementation for parci.
    """

    def __init__(
        self,
        parameter_prefix: str = os.environ.get(
            "PARCI_PARAMETER_STORE_SSM_PREFIX", "/parci"
        ),
    ):
        self.prefix = parameter_prefix

        while self.prefix.endswith("/"):
            self.prefix = self.prefix[:-1]
        if not self.prefix.startswith("/"):
            self.prefix = "/" + self.prefix

        self.client = boto3.client("ssm")

    def __getitem__(self, name):
        response = self.client.get_parameter(
            Name=f"{self.prefix}/{name}", WithDecryption=True
        )["Parameter"]
        if response["Type"] == "StringList":
            return response["Value"].split(",")
        try:
            return json.loads(response["Value"])
        except json.JSONDecodeError:
            return response["Value"]

    def __setitem__(self, name, value):
        if config.PARAMETER_READ_ONLY:
            raise SSMParameterStoreException("Cannot write to AWS SSM parameter store")

        if not name.startswith("/"):
            name = self.prefix + "/" + name

        self.client.put_parameter(
            Name=name,
            Value=json.dumps(value),
            Type="SecureString",
            Overwrite=True,
            Tier="Intelligent-Tiering",
        )

    def keys(self):
        """
        Return a list of all keys in the SSM parameter store.
        """
        prefix = self.prefix + "/"
        paginator = self.client.get_paginator("describe_parameters")
        for page in paginator.paginate(
            ParameterFilters=[
                {"Key": "Name", "Option": "BeginsWith", "Values": [prefix]},
            ]
        ):
            for parameter in page["Parameters"]:
                name = parameter["Name"]
                if name.startswith(prefix):
                    name = name[len(prefix) :]
                yield name
