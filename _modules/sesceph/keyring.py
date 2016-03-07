import os
import shutil
import tempfile
import os.path

import model
import mdl_updater
import utils
import mdl_query
import constants

class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])

def _get_path_keyring_admin(cluster_name):
    return '/etc/ceph/%s.client.admin.keyring' % (cluster_name)

def _get_path_keyring_mon(cluster_name, host_name):
    return os.path.join(constants._path_ceph_lib_mon, '%s-%s/keyring' % (cluster_name, host_name))

def _get_path_keyring_mon_bootstrap(cluster_name, host_name):
    return os.path.join(constants._path_ceph_lib, 'bootstrap-mon/%s-%s.keyring' % (cluster_name, host_name))


def _get_path_keyring_osd(cluster_name):
    return os.path.join(constants._path_ceph_lib, 'bootstrap-osd/%s.keyring' % (cluster_name))

def _get_path_keyring_mds(cluster_name):
    return os.path.join(constants._path_ceph_lib, 'bootstrap-mds/%s.keyring' % (cluster_name))


def _get_path_keyring_rgw(cluster_name):
    return os.path.join(constants._path_ceph_lib, 'bootstrap-rgw/%s.keyring' % (cluster_name))


def _keying_read(key_path):
    output = ""
    with open(key_path, 'r') as infile:
        output = infile.read()
    return output

def _keying_write(key_path,content):
    dirname = os.path.dirname(key_path)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    with open(key_path, 'w') as infile:
        for line in content.split('\n'):
            stripped = line.strip()
            if len(stripped) == 0:
                continue
            if stripped[0] == '[':
                infile.write('%s\n' % (stripped))
                continue
            infile.write('\t%s\n' % (stripped))
    return


def Property(func):
    return property(**func())




class keyring_implementation_base(object):
    def __init__(self,**kwargs):
        self.model = model.model(**kwargs)
        u = mdl_updater.model_updater(self.model)
        u.hostname_refresh()
        u.defaults_refresh()
        u.load_confg(self.model.cluster_name)
        u.mon_members_refresh()

    def invoke_ceph_authtool(self, keyring_name, keyring_path, caps, secret=None, extra_args=[]):
        """create arguments for invoking the ceph authtool, this simplifies most of
        the ways that ceph authtool could be invoked.

        Args:
            keyring_name: The name of keyring to be created
            keyring_path: path where keyring is to be created
            caps: A dictionary containing various k-v pairs of components and their respective auth
                  permission eg:
                  {'mon':'allow *'}
            secret: The base64 secret to create keyring from, if this is set we will use this secret
                    instead to create the keyring, otherwise authtool itself will generate one
            extra_args: any other extra arguments to be passed to ceph authtool"""
        args=[constants._path_ceph_authtool, "-n", keyring_name, "--create-keyring", keyring_path]

        if secret:
            args += ["--add-key", secret]
        else:
            args.append("--gen-key")

        args += extra_args

        for component,permission in caps.items():
            args += ["--cap", component, permission]
        return args


    def create(self, **kwargs):
        """
        Create keyring
        """
        self.model.kargs_apply(**kwargs)
        u = mdl_updater.model_updater(self.model)
        u.hostname_refresh()
        if self.model.cluster_name is None:
            u.defaults_refresh()
        keyring_path = self.get_path_keyring()
        if os.path.isfile(keyring_path):
            return _keying_read(keyring_path)
        try:
            tmpd = tempfile.mkdtemp()
            key_path = os.path.join(tmpd,"keyring")
            cmd_out = utils.execute_local_command(self.get_arguments_create(key_path,self.model.secret))
            output = _keying_read(key_path)
        finally:
            shutil.rmtree(tmpd)
        return output



    def write(self, key_content=None, **kwargs):
        """
        Persist keyring
        """
        self.model.kargs_apply(**kwargs)
        u = mdl_updater.model_updater(self.model)
        u.hostname_refresh()
        if self.model.cluster_name is None:
            u.defaults_refresh()
        keyring_path = self.get_path_keyring()
        if os.path.isfile(keyring_path):
            return True

        # We only check for secret, as init itself catches the case if
        # key_content is already set
        if secret:
            key_content=self.create(**kwargs)

        _keying_write(keyring_path, key_content)
        return True


    def auth_add(self, **kwargs):
        """
        Authorise keyring
        """
        self.model.kargs_apply(**kwargs)
        u = mdl_updater.model_updater(self.model)
        u.hostname_refresh()
        if self.model.cluster_name is None:
            u.defaults_refresh()
        keyring_path = self.get_path_keyring()
        if not os.path.isfile(keyring_path):
            raise Error("rgw keyring not found")
        u.load_confg(self.model.cluster_name)
        u.mon_members_refresh()
        q = mdl_query.mdl_query(self.model)
        if not q.mon_is():
            raise Error("Not ruining a mon daemon")
        u.mon_status()
        if not q.mon_quorum():
            raise Error("mon daemon is not in quorum")
        arguments = [
                "ceph",
                "auth",
                "import",
                "-i",
                keyring_path
                ]
        cmd_out = utils.execute_local_command(arguments)
        return True


    def auth_del(self, **kwargs):
        """
        Remove Authorised keyring
        """
        self.model.kargs_apply(**kwargs)
        u = mdl_updater.model_updater(self.model)
        u.hostname_refresh()
        if self.model.cluster_name is None:
            u.defaults_refresh()
        u.load_confg(self.model.cluster_name)
        u.mon_members_refresh()
        q = mdl_query.mdl_query(self.model)
        if not q.mon_is():
            raise Error("Not ruining a mon daemon")
        u.mon_status()
        if not q.mon_quorum():
            raise Error("mon daemon is not in quorum")
        arguments = [
                "ceph",
                "auth",
                "del",
                self.keyring_name
                ]
        cmd_out = utils.execute_local_command(arguments)
        return True


    def remove(self, **kwargs):
        """
        Delete keyring
        """
        self.model.kargs_apply(**kwargs)
        u = mdl_updater.model_updater(self.model)
        if self.model.cluster_name is None:
            u.defaults_refresh()
        keyring_path = self.get_path_keyring()
        if os.path.isfile(keyring_path):
            try:
                os.remove(keyring_path)
            except:
                raise Error("Keyring could not be deleted")
        return True


class keyring_implementation_admin(keyring_implementation_base):
    def __init__(self):
        keyring_implementation_base.__init__(self)
        self.keyring_name = "client.admin"
        self.caps = {"mon":"allow *", "osd":"allow *", "mds":"allow *"}

    def get_path_keyring(self):
        return _get_path_keyring_admin(self.model.cluster_name)

    def get_arguments_create(self, path, secret=None):
        return self.invoke_ceph_authtool(self.keyring_name, path, self.caps, secret=secret)

class keyring_implementation_mon(keyring_implementation_base):
    def __init__(self):
        keyring_implementation_base.__init__(self)
        self.keyring_name = "mon."
        self.caps = {"mon": "allow *"}

    def get_path_keyring(self):
        if self.model.cluster_name is None:
            raise  Error("Cluster name not found")
        if self.model.hostname is None:
            raise  Error("Cluster name not found")
        return _get_path_keyring_mon_bootstrap(self.model.cluster_name,
                self.model.hostname)

    def get_arguments_create(self, path, secret=None):
        extra_args=["--set-uid=0"]
        return self.invoke_ceph_authtool(self.keyring_name, path, self.caps, secret=secret, extra_args=extra_args)


class keyring_implementation_osd(keyring_implementation_base):
    def __init__(self):
        keyring_implementation_base.__init__(self)
        self.keyring_name = "client.bootstrap-osd"
        self.caps = {"mon": "allow profile bootstrap-osd"}

    def get_path_keyring(self):
        if self.model.cluster_name is None:
            raise  Error("Cluster name not found")
        return _get_path_keyring_osd(self.model.cluster_name)

    def get_arguments_create(self, path, secret=None):
        return self.invoke_ceph_authtool(self.keyring_name, path, self.caps, secret=secret)

class keyring_implementation_rgw(keyring_implementation_base):
    def __init__(self):
        keyring_implementation_base.__init__(self)
        self.keyring_name = "client.bootstrap-rgw"
        self.caps = {"mon": "allow profile bootstrap-rgw"}

    def get_path_keyring(self):
        if self.model.cluster_name is None:
            raise  Error("Cluster name not found")
        return _get_path_keyring_rgw(self.model.cluster_name)


    def get_arguments_create(self, path, secret=None):
        # TODO ideally remove extra_args when we understand permisons better.
        extra_args=["--cap",
            "osd",
            "allow *",
            "--cap",
            "mon",
            "allow *"
            ]
        return self.invoke_ceph_authtool(self.keyring_name, path, self.caps, extra_args=extra_args, secret=secret)


class keyring_implementation_mds(keyring_implementation_base):
    def __init__(self):
        keyring_implementation_base.__init__(self)
        self.keyring_name = "client.bootstrap-mds"
        self.caps = {"mon": "allow profile bootstrap-mds"}

    def get_path_keyring(self):
        if self.model.cluster_name is None:
            raise  Error("Cluster name not found")
        return _get_path_keyring_mds(self.model.cluster_name)

    def get_arguments_create(self, path, secret=None):
        # TODO ideally remove extra_args when we understand permisons better.
        extra_args=[
            "--cap", "osd", "allow *",
            "--cap", "mon", "allow *"
            ]
        return self.invoke_ceph_authtool(self.keyring_name, path, self.caps, extra_args=extra_args, secret=secret)


class keyring_facard(object):
    def __init__(self):
        self._availableKeys = set(["admin", "mds", "mon", "osd", "rgw"])
        self._clear_implementation()


    def _clear_implementation(self):
        self._keyType = None
        self._keyImp = None


    @Property
    def key_type():
        doc = "key_type"

        def fget(self):
            return self._keyType


        def fset(self, name):
            if name is None:
                self._clear_implementation()
            if not name in self._availableKeys:
                self._clear_implementation()
                raise Error("Invalid Value")
            implementation = None
            if name == "admin":
                implementation = keyring_implementation_admin()
            if name == "mds":
                implementation = keyring_implementation_mds()
            if name == "mon":
                implementation = keyring_implementation_mon()
            if name == "osd":
                implementation = keyring_implementation_osd()
            if name == "rgw":
                implementation = keyring_implementation_rgw()
            if implementation is None:
                self._clear_implementation()
                raise Error("Invalid Value")
            self._keyImp = implementation
            self._keyType = name
            return self._keyType


        def fdel(self):
            self._clear_implementation()


        return locals()

    def create(self, **kwargs):
        """
        Create keyring
        """
        self.key_type == 'osd'
        if self._keyImp is None:
            raise Error("Programming error: key type unset")
        return self._keyImp.create(**kwargs)


    def write(self, key_content=None, **kwargs):
        """
        Persist keyring
        """
        if self._keyImp is None:
            raise Error("Programming error: key type unset")
        return self._keyImp.write(key_content,**kwargs)


    def auth_add(self, **kwargs):
        """
        Authorise keyring
        """
        if self._keyImp is None:
            raise Error("Programming error: key type unset")
        return self._keyImp.auth_add(**kwargs)

    def auth_del(self, **kwargs):
        """
        Authorise keyring
        """
        if self._keyImp is None:
            raise Error("Programming error: key type unset")
        return self._keyImp.auth_del(**kwargs)

    def remove(self, **kwargs):
        """
        Remove keyring
        """
        if self._keyImp is None:
            raise Error("Programming error: key type unset")
        return self._keyImp.remove(**kwargs)
