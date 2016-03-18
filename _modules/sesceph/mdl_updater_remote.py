# This module is to update the model with remote commands.

# Python imports
import logging
import os
import json

# Local imports
import keyring
import constants
import utils


log = logging.getLogger(__name__)


class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])


class model_updater_remote():
    """
    Basic model updator retrives data and adds to model
    """
    def __init__(self, model):
        self.model = model
        self.keyring_type = None
        self.keyring_path = None
        self.keyring_identity = None


    def connection_arguments_get(self):
        if self.keyring_type != None:
            return [
                    '--connect-timeout',
                    '5',
                    "--keyring",
                    self.keyring_path,
                    "--name",
                    self.keyring_identity,
                ]
        raise Error("No keytype selected")


    def connect(self):
        keyring_obj = keyring.keyring_facard()
        for keytype in ["admin", "osd", "mds", "rgw", "mon"]:
            log.debug("Trying keyring:%s" % (keytype))
            keyring_obj.key_type = keytype
            keyring_path = keyring_obj.keyring_path_get()
            if not os.path.isfile(keyring_path):
                log.debug("Skipping keyring %s" % (keyring_path))
                continue
            keyring_identity = keyring_obj.keyring_identity_get()
            arguments = [
                constants._path_ceph,
                '--connect-timeout',
                '5',
                "--keyring",
                keyring_path,
                "--name",
                keyring_identity,
                "-f",
                "json-pretty",
                "status"
            ]
            output = utils.execute_local_command(arguments)
            if output["retcode"] != 0:
                continue
            self.model.cluster_status = json.loads(output["stdout"].strip())
            self.keyring_type = keytype
            self.keyring_path = keyring_path
            self.keyring_identity = keyring_identity
            return True
        return False


    def status_refresh(self):
        """
        Get the cluster status

        This is not normally needed as connect method has updated this information
        """
        prefix_arguments = [
            constants._path_ceph
        ]
        postfix_arguments = [
            "-f",
            "json-pretty",
            "status"
        ]
        connection_arguments = self.connection_arguments_get()
        arguments = prefix_arguments + connection_arguments + postfix_arguments
        output = utils.execute_local_command(arguments)

        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                        " ".join(arguments),
                        output["retcode"],
                        output["stdout"],
                        output["stderr"])
                        )
        self.model.cluster_status = json.loads(output["stdout"].strip())
