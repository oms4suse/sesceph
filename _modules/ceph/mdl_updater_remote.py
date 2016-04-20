# This module is to update the model with remote commands.

# Python imports
import logging
import os
import json
import shlex

# Local imports
import keyring
import constants
import utils
import mdl_query


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
        keyring_obj = keyring.keyring_facard(self.model)
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


    def auth_list(self):
        prefix_arguments = [
            constants._path_ceph
        ]
        postfix_arguments = [
            "auth",
            "list"
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
        auth_list_out = {}
        section = {}
        for line in output["stdout"].split('\n'):
            if len(line) == 0:
                continue
            if line[0] != '\t':
                prev_sec_name = section.get("name")
                if prev_sec_name is not None:
                    auth_list_out[prev_sec_name] = section
                section = { "name" : line }
                continue
            tokenised_line = shlex.split(line)
            if len(tokenised_line) == 0:
                continue
            if tokenised_line[0] == 'key:':
                section['key'] = tokenised_line[1]
            if tokenised_line[0] == 'caps:':
                if not 'caps' in section:
                    section['caps'] = []
                cap_details = tokenised_line[1:]
                section["caps"].append(cap_details)


        prev_sec_name = section.get("name")
        if prev_sec_name is not None:
            auth_list_out[prev_sec_name] = section
        self.model.auth_list = auth_list_out


    def auth_add(self, keyring_type):
        """
        Authorise keyring
        """
        keyringobj = keyring.keyring_facard(self.model)
        keyringobj.key_type = keyring_type


        if not keyringobj.present():
            raise Error("rgw keyring not found")
        q = mdl_query.mdl_query(self.model)
        if q.mon_is() and q.mon_quorum() is False:
            raise Error("mon daemon is not in quorum")
        arguments = [
                "ceph",
                "auth",
                "import",
                "-i",
                keyringobj.keyring_path_get()
                ]
        cmd_out = utils.execute_local_command(arguments)
        return True


    def auth_del(self, **kwargs):
        """
        Remove Authorised keyring
        """
        keyringobj = keyring.keyring_facard(self.model)
        keyringobj.key_type = keyring_type
        q = mdl_query.mdl_query(self.model)
        if q.mon_is() and q.mon_quorum() is False:
            raise Error("mon daemon is not in quorum")
        arguments = [
                "ceph",
                "auth",
                "del",
                keyringobj.keyring_path_get()
                ]
        cmd_out = utils.execute_local_command(arguments)
        return True


    def pool_list(self):
        prefix_arguments = [
            constants._path_ceph
        ]
        postfix_arguments = [
            "-f",
            "json",
            "osd",
            "lspools"
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
        details = {}
        for item in json.loads(output["stdout"].strip()):
            pool_num = item.get("poolnum")
            pool_name = item.get("poolname")
            details[pool_name] = {"poolnum" : pool_num }
        self.model.pool_list = details

    def _pool_adder(self, name, **kwargs):
        pg_num = kwargs.get("pg_num", 8)
        pgp_num = kwargs.get("pgp_num", pg_num)
        pool_type = kwargs.get("pool_type")
        er_profile = kwargs.get("erasure_code_profile")
        crush_ruleset_name = kwargs.get("crush_ruleset")
        prefix_arguments = [
            constants._path_ceph
        ]
        postfix_arguments = [
            'osd',
            'pool',
            'create',
            name,
            str(pg_num)
            ]
        connection_arguments = self.connection_arguments_get()
        arguments = prefix_arguments + connection_arguments + postfix_arguments
        if pgp_num is not None:
            arguments.append(str(pgp_num))
        if pool_type == "replicated":
            arguments.append("replicated")
        if pool_type == "erasure":
            arguments.append("erasure")
            arguments.append("erasure-code-profile=%s" % (er_profile))
        if crush_ruleset_name is not None:
            arguments.append(crush_ruleset_name)
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                        " ".join(arguments),
                        output["retcode"],
                        output["stdout"],
                        output["stderr"]))

    def pool_add(self, name, **kwargs):
        if not name in self.model.pool_list.keys():
            return self._pool_adder(name, **kwargs)

    def pool_del(self, name):
        if not name in self.model.pool_list.keys():
            return True
        prefix_arguments = [
            constants._path_ceph
        ]
        postfix_arguments = [
            'osd',
            'pool',
            'delete',
            name,
            name,
            '--yes-i-really-really-mean-it'
            ]
        connection_arguments = self.connection_arguments_get()
        arguments = prefix_arguments + connection_arguments + postfix_arguments
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                        " ".join(arguments),
                        output["retcode"],
                        output["stdout"],
                        output["stderr"]))
        return True



