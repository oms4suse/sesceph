import os
import logging
import json
import shutil

import utils
import constants
import keyring
import model
import mdl_updater


log = logging.getLogger(__name__)

class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])


class rgw_ctrl(object):
    def __init__(self, **kwargs):
        self.model = model.model(**kwargs)
        self.model.init = "systemd"
        self.rgw_name = kwargs.get("name")
        u = mdl_updater.model_updater(self.model)
        u.hostname_refresh()
        u.defaults_refresh()
        u.load_confg(self.model.cluster_name)
        u.mon_members_refresh()


    def _set_rgw_path_lib(self):
        if self.rgw_name == None:
            raise Error("rgw name not specified")
        self.rgw_path_lib = '{path}/{cluster}-{name}'.format(
            path=constants._path_ceph_lib_rgw,
            cluster=self.model.cluster_name,
            name=self.rgw_name
            )


    def rgw_pools_missing(self):
        requiredPools = set([".rgw",
                ".rgw.control",
                ".rgw.gc",
                ".log",
                ".intent-log",
                ".usage",
                ".users",
                ".users.email",
                ".users.swift",
                ".users.uid"
            ])
        u = mdl_updater.model_updater(self.model)
        u.pool_list()
        if self.model.pool_list == None:
            LOG.error("Failed to list available pools")
            return False
        foundnames = set()
        for pool in self.model.pool_list:
            foundnames.add(pool)
        return list(requiredPools.difference(foundnames))


    def rgw_pools_create(self):
        rc = True
        u = mdl_updater.model_updater(self.model)
        for name in self.rgw_pools_missing():
            log.info("Adding missing pool:%s" % (name))
            try:
                tmp_rc = u.pool_add(name, pg_num=16)
            except:
                log.error("Failed to add pool '%s'" % (name))
                rc = False
        return rc


    def prepare(self, **kwargs):
        missing_pools = self.rgw_pools_missing()
        if len(missing_pools) > 0:
            raise Error("Pools missing: %s" % (", ".join(missing_pools)))
        self._set_rgw_path_lib()
        path_bootstrap_keyring = keyring._get_path_keyring_rgw(self.model.cluster_name)
        if not os.path.isfile(path_bootstrap_keyring):
            raise Error("Keyring not found at %s" % (path_bootstrap_keyring))
        if not os.path.isdir(self.rgw_path_lib):
            log.info("Make missing directory:%s" % (self.rgw_path_lib))
            os.makedirs(self.rgw_path_lib)
        rgw_path_keyring = os.path.join(self.rgw_path_lib, 'keyring')
        if not os.path.isfile(rgw_path_keyring):
            log.info("Make missing keyring:%s" % (rgw_path_keyring))
            arguments = [
                'ceph',
                '--connect-timeout',
                '5',
                '--cluster', self.model.cluster_name,
                '--name', 'client.bootstrap-rgw',
                '--keyring', path_bootstrap_keyring,
                'auth', 'get-or-create', 'client.{name}'.format(name=self.rgw_name),
                'osd', 'allow rwx',
                'mon', 'allow rw',
                '-o',
                rgw_path_keyring
            ]

            output = utils.execute_local_command(arguments)
            if output["retcode"] != 0:
                if os.path.isfile(rgw_path_keyring):
                    log.info("Cleaning up new key:%s" % (rgw_path_keyring))
                    os.remove(rgw_path_keyring)
                raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                        " ".join(arguments),
                        output["retcode"],
                        output["stdout"],
                        output["stderr"])
                        )


    def _remove_rgw_keyring(self, **kwargs):
        self._set_rgw_path_lib()
        if not os.path.isdir(self.rgw_path_lib):
            return
        rgw_path_keyring = os.path.join(self.rgw_path_lib, 'keyring')

        path_bootstrap_keyring = keyring._get_path_keyring_rgw(self.model.cluster_name)
        arguments = [
            'ceph',
            '--connect-timeout',
            '5',
            '--cluster', self.model.cluster_name,
            '--name', 'client.bootstrap-rgw',
            '--keyring', path_bootstrap_keyring,
            'auth', 'del', 'client.{name}'.format(name=self.rgw_name),
        ]

        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                    " ".join(arguments),
                    output["retcode"],
                    output["stdout"],
                    output["stderr"])
                    )


    def remove(self, **kwargs):
        self._set_rgw_path_lib()
        if not os.path.isdir(self.rgw_path_lib):
            return
        rgw_path_keyring = os.path.join(self.rgw_path_lib, 'keyring')
        if os.path.isfile(rgw_path_keyring):
            log.info("Remove from auth list keyring:%s" % (rgw_path_keyring))
            self._remove_rgw_keyring(**kwargs)
        log.info("Remove directory:%s" % (self.rgw_path_lib))
        shutil.rmtree(self.rgw_path_lib)


    def activate(self, **kwargs):
        if self.rgw_name == None:
            raise Error("Name not specified")
        arguments = [
            constants._path_systemctl,
            "start",
            "ceph-radosgw@%s" % (self.rgw_name)
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                " ".join(arguments),
                output["retcode"],
                output["stdout"],
                output["stderr"])
                )
            raise Error("Name not specified")
        arguments = [
            constants._path_systemctl,
            "enable",
            "ceph-radosgw@%s" % (self.rgw_name)
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                " ".join(arguments),
                output["retcode"],
                output["stdout"],
                output["stderr"])
                )


    def deactivate(self, **kwargs):
        if self.rgw_name == None:
            raise Error("Name not specified")
        arguments = [
            constants._path_systemctl,
            "disable",
            "ceph-radosgw@%s" % (self.rgw_name)
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                " ".join(arguments),
                output["retcode"],
                output["stdout"],
                output["stderr"])
                )
        arguments = [
            constants._path_systemctl,
            "stop",
            "ceph-radosgw@%s" % (self.rgw_name)
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                " ".join(arguments),
                output["retcode"],
                output["stdout"],
                output["stderr"])
                )


    def create(self, **kwargs):
        self.prepare(**kwargs)
        self.activate(**kwargs)


    def destroy(self, **kwargs):
        self.deactivate(**kwargs)
        self.remove(**kwargs)
