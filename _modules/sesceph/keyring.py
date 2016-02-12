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

    def create(self, **kwargs):
        """
        Create keyring
        """
        self.model.kargs_apply(**kwargs)
        u = mdl_updater.model_updater(self.model)
        u.hostname_refresh()
        if self.model.cluster_name == None:
            u.defaults_refresh()
        keyring_path = self.get_path_keyring()
        if os.path.isfile(keyring_path):
            return _keying_read(keyring_path)
        try:
            tmpd = tempfile.mkdtemp()
            key_path = os.path.join(tmpd,"keyring")
            # TODO: We can do better than this hack!
            if kwargs.get("key") is not None:
                cmd = self.get_arguments_create(key_path,kwargs.get("key"))
            else:
                cmd = self.get_arguments_create(key_path)
            cmd_out = utils.execute_local_command(cmd)
            output = _keying_read(key_path)
        finally:
            shutil.rmtree(tmpd)
        return output


    def write(self, key_content, **kwargs):
        """
        Persist keyring
        """
        self.model.kargs_apply(**kwargs)
        u = mdl_updater.model_updater(self.model)
        u.hostname_refresh()
        if self.model.cluster_name == None:
            u.defaults_refresh()
        keyring_path = self.get_path_keyring()
        if os.path.isfile(keyring_path):
            return True
        _keying_write(keyring_path, key_content)
        return True


    def auth_add(self, **kwargs):
        """
        Authorise keyring
        """
        self.model.kargs_apply(**kwargs)
        u = mdl_updater.model_updater(self.model)
        u.hostname_refresh()
        if self.model.cluster_name == None:
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
        if self.model.cluster_name == None:
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
        if self.model.cluster_name == None:
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

    def get_path_keyring(self):
        return _get_path_keyring_admin(self.model.cluster_name)

    def get_arguments_create(self, path):
        return [
            constants._path_ceph_authtool,
            "--create-keyring",
            path,
            "--gen-key",
            "-n",
            self.keyring_name,
            "--set-uid=0",
            "--cap",
            "mon",
            "allow *",
            "--cap",
            "mds",
            "allow *",
            "--cap",
            "osd",
            "allow *"
            ]

class keyring_implementation_mon(keyring_implementation_base):
    def __init__(self):
        keyring_implementation_base.__init__(self)
        self.keyring_name = "mon." + self.model.hostname

    def get_path_keyring(self):
        if self.model.cluster_name == None:
            raise  Error("Cluster name not found")
        if self.model.hostname == None:
            raise  Error("Cluster name not found")
        return _get_path_keyring_mon_bootstrap(self.model.cluster_name,
                self.model.hostname)

    def get_arguments_create(self, path, key=None):
        if key is None:
            key_opts="--create-keyring"
        else:
            key_opts="--add-key %s" %key
        return [
            constants._path_ceph_authtool,
            "--create-keyring",
            path,
            key_opts,
            "-n",
            self.keyring_name,
            "--cap",
            "mon",
            "allow *"
            ]

    def create_and_save(self, key, **kwargs):
        # TODO: fix the base class
        # TODO: also we don't right now check for failures
        kwargs['key'] = key
        keyring = self.create(**kwargs)
        return self.write(keyring,**kwargs)

class keyring_implementation_osd(keyring_implementation_base):
    def __init__(self):
        keyring_implementation_base.__init__(self)
        self.keyring_name = "client.bootstrap-osd"

    def get_path_keyring(self):
        if self.model.cluster_name == None:
            raise  Error("Cluster name not found")
        return _get_path_keyring_osd(self.model.cluster_name)

    def get_arguments_create(self, path):
        return [
            "ceph-authtool",
            "--create-keyring",
            path,
            "--gen-key",
            "-n",
            self.keyring_name,
            "--cap",
            "mon",
            "allow profile bootstrap-osd"
            ]

class keyring_implementation_rgw(keyring_implementation_base):
    def __init__(self):
        keyring_implementation_base.__init__(self)
        self.keyring_name = "client.bootstrap-rgw"

    def get_path_keyring(self):
        if self.model.cluster_name == None:
            raise  Error("Cluster name not found")
        return _get_path_keyring_rgw(self.model.cluster_name)

    def get_arguments_create(self, path):
        return [
            "ceph-authtool",
            "--create-keyring",
            path,
            "--gen-key",
            "-n",
            self.keyring_name,
            "--cap",
            "mon",
            "allow profile bootstrap-rgw"
            ]


class keyring_implementation_mds(keyring_implementation_base):
    def __init__(self):
        keyring_implementation_base.__init__(self)
        self.keyring_name = "client.bootstrap-mds"

    def get_path_keyring(self):
        if self.model.cluster_name == None:
            raise  Error("Cluster name not found")
        return _get_path_keyring_mds(self.model.cluster_name)

    def get_arguments_create(self, path):
        return [
            "ceph-authtool",
            "--create-keyring",
            path,
            "--gen-key",
            "-n",
            self.keyring_name,
            "--cap",
            "mon",
            "allow profile bootstrap-mds"
            ]






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
            if name == None:
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
            if implementation == None:
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
        if self._keyImp == None:
            raise Error("Programming error: key type unset")
        return self._keyImp.create(**kwargs)


    def write(self, key_content, **kwargs):
        """
        Persist keyring
        """
        if self._keyImp == None:
            raise Error("Programming error: key type unset")
        return self._keyImp.write(key_content, **kwargs)

    def create_and_save(self, key, **kwargs):
        """
        Create keyring from given secret
        """
        if self._keyImp is None:
            raise Error("Programming error: key type unset")
        return self._keyImp.create_and_save(key, **kwargs)

    def auth_add(self, **kwargs):
        """
        Authorise keyring
        """
        if self._keyImp == None:
            raise Error("Programming error: key type unset")
        return self._keyImp.auth_add(**kwargs)

    def auth_del(self, **kwargs):
        """
        Authorise keyring
        """
        if self._keyImp == None:
            raise Error("Programming error: key type unset")
        return self._keyImp.auth_del(**kwargs)

    def remove(self, **kwargs):
        """
        Remove keyring
        """
        if self._keyImp == None:
            raise Error("Programming error: key type unset")
        return self._keyImp.remove(**kwargs)
