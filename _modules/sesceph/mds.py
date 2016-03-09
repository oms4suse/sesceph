# Python imports
import os
import logging
import json
import shutil

# Local imports
import utils
import constants
import keyring
import model
import mdl_updater
import rados_client


log = logging.getLogger(__name__)

class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])


class mds_ctrl(rados_client.ctrl_rados_client):
    def __init__(self, **kwargs):
        super(mds_ctrl, self).__init__(**kwargs)
        self.service_name = "ceph-mds"
        self.mds_name = kwargs.get("name")
        self.port = kwargs.get("port")
        self.addr = kwargs.get("addr")


    def _set_mds_path_lib(self):
        if self.mds_name == None:
            raise Error("mds name not specified")
        self.mds_path_lib = '{path}/{cluster}-{name}'.format(
            path=constants._path_ceph_lib_mds,
            cluster=self.model.cluster_name,
            name=self.mds_name
            )

    def _set_path_systemd_env(self):
        self.model.path_systemd_env = "{lib_dir}/systemd/".format(
            lib_dir=constants._path_ceph_lib_mds,
            )

    def _set_mds_path_env(self):
        if self.mds_name == None:
            raise Error("mds name not specified")
        if self.model.cluster_name == None:
            raise Error("cluster_name not specified")
        if self.model.path_systemd_env == None:
            raise Error("self.model.path_systemd_env not specified")
        self.model.mds_path_env = "{path_systemd_env}/{name}".format(
            name=self.mds_name,
            path_systemd_env=self.model.path_systemd_env
            )



    def prepare(self):
        self._set_mds_path_lib()
        self._set_path_systemd_env()
        self._set_mds_path_env()
        path_bootstrap_keyring = keyring._get_path_keyring_mds(self.model.cluster_name)
        if not os.path.isfile(path_bootstrap_keyring):
            raise Error("Keyring not found at %s" % (path_bootstrap_keyring))
        if not os.path.isdir(self.model.path_systemd_env):
            log.info("mkdir %s" % (self.model.path_systemd_env))
            os.makedirs(self.model.path_systemd_env)
        if not os.path.isdir(self.mds_path_lib):
            log.info("mkdir %s" % (self.mds_path_lib))
            os.makedirs(self.mds_path_lib)

        mds_path_keyring = os.path.join(self.mds_path_lib, 'keyring')
        if not os.path.isfile(mds_path_keyring):
            log.info("creating %s" % (mds_path_keyring))
            arguments = [
                'ceph',
                '--connect-timeout',
                '5',
                '--cluster', self.model.cluster_name,
                '--name', 'client.bootstrap-mds',
                '--keyring', path_bootstrap_keyring,
                'auth', 'get-or-create', 'client.{name}'.format(name=self.mds_name),
                'osd', 'allow rwx',
                'mon', 'allow rw',
                '-o',
                mds_path_keyring
            ]

            output = utils.execute_local_command(arguments)
            if output["retcode"] != 0:
                if os.path.isfile(mds_path_keyring):
                    log.info("Cleaning up new key:%s" % (mds_path_keyring))
                    os.remove(mds_path_keyring)
                raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                        " ".join(arguments),
                        output["retcode"],
                        output["stdout"],
                        output["stderr"])
                        )


    def _remove_mds_keyring(self):
        self._set_mds_path_lib()
        if not os.path.isdir(self.mds_path_lib):
            return
        mds_path_keyring = os.path.join(self.mds_path_lib, 'keyring')

        path_bootstrap_keyring = keyring._get_path_keyring_mds(self.model.cluster_name)
        arguments = [
            'ceph',
            '--connect-timeout',
            '5',
            '--cluster', self.model.cluster_name,
            '--name', 'client.bootstrap-mds',
            '--keyring', path_bootstrap_keyring,
            'auth', 'del', 'client.{name}'.format(name=self.mds_name),
        ]

        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                    " ".join(arguments),
                    output["retcode"],
                    output["stdout"],
                    output["stderr"])
                    )


    def remove(self):
        self._set_mds_path_lib()
        self._set_path_systemd_env()
        self._set_mds_path_env()
        if os.path.isfile(self.model.mds_path_env):
            log.info("removing:%s" % (self.model.mds_path_env))
            os.remove(self.model.mds_path_env)
        if not os.path.isdir(self.mds_path_lib):
            return
        mds_path_keyring = os.path.join(self.mds_path_lib, 'keyring')
        if os.path.isfile(mds_path_keyring):
            self._remove_mds_keyring()
        shutil.rmtree(self.mds_path_lib)




    def make_env(self):
        if os.path.isfile(self.model.mds_path_env):
            return
        data_list = []
        data_list.append('BIND_IPV4="{ipv4}"\n'.format(ipv4=self.addr))
        data_list.append('BIND_PORT="{port}"\n'.format(port=self.port))
        data_list.append('CLUSTER="{cluster}"\n'.format(cluster=self.model.cluster_name))
        with open(self.model.mds_path_env, 'w+') as f:
            for data in data_list:
                f.write(data)


    def activate(self):
        self._set_path_systemd_env()
        self._set_mds_path_env()
        if self.mds_name == None:
            raise Error("name not specified")
        if self.port == None:
            raise Error("port not specified")
        if self.addr == None:
            raise Error("addr not specified")
        if self.model.path_systemd_env == None:
            raise Error("self.model.path_systemd_env not specified")
        if self.model.mds_path_env == None:
            raise Error("self.model.mds_path_env not specified")
        if not os.path.isdir(self.model.path_systemd_env):
            raise Error("self.model.path_systemd_env not specified")

        if not os.path.isfile(self.model.mds_path_env):
            log.info("Making file:%s" % (self.model.mds_path_env))
            self.make_env()
        super(mds_ctrl, self).activate()


    def create(self):
        self._set_path_systemd_env()
        self._set_mds_path_env()
        self.prepare()
        self.activate()


    def destroy(self):
        self.deactivate()
        self.remove()
