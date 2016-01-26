import os
import shutil
import tempfile

from model import _model
from mdl_updater import _model_updator
from utils import _excuete_local_command
from mdl_query import _mdl_query

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
    return '/var/lib/ceph/mon/%s-%s/keyring' % (cluster_name, host_name)

def _get_path_keyring_mon_bootstrap(cluster_name, host_name):
    return '/var/lib/ceph/bootstrap-mon/%s-%s.keyring' % (cluster_name, host_name)


def _get_path_keyring_osd(cluster_name):
    return '/var/lib/ceph/bootstrap-osd/%s.keyring' % (cluster_name)

def _get_path_keyring_mds(cluster_name):
    return '/var/lib/ceph/bootstrap-mds/%s.keyring' % (cluster_name)


def _get_path_keyring_rgw(cluster_name):
    return '/var/lib/ceph/bootstrap-rgw/%s.keyring' % (cluster_name)


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
    def __init__(self):
        self.model = model

    def create(self, **kwargs):
        """
        Create keyring
        """
        m = _model(**kwargs)
        u = _model_updator(m)
        if m.cluster_name == None:
            u.defaults_refresh()
        self.cluster_name = m.cluster_name
        keyring_path = self.get_path_keyring()
        if os.path.isfile(keyring_path):
            return _keying_read(keyring_path)
        try:
            tmpd = tempfile.mkdtemp()
            key_path = os.path.join(tmpd,"keyring")
            cmd_out = _excuete_local_command(self.get_arguments_create(key_path))
            output = _keying_read(key_path)
        finally:
            shutil.rmtree(tmpd)
        print output
        return output


    def write(self, key_content, **kwargs):
        """
        Persist keyring
        """
        m = _model(**kwargs)
        u = _model_updator(m)
        if m.cluster_name == None:
            u.defaults_refresh()
        self.cluster_name = m.cluster_name
        keyring_path = self.get_path_keyring()
        if os.path.isfile(keyring_path):
            return True
        _keying_write(keyring_path, key_content)
        return True

    def auth_add(self, **kwargs):
        """
        Authorise keyring
        """
        m = _model(**kwargs)
        u = _model_updator(m)
        u.hostname_refresh()
        if m.cluster_name == None:
            u.defaults_refresh()
        self.cluster_name = m.cluster_name
        keyring_path = self.get_path_keyring()
        if not os.path.isfile(keyring_path):
            raise Error("rgw keyring not found")
        u.load_confg(m.cluster_name)
        u.mon_members_refresh()
        q = _mdl_query(m)
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
        cmd_out = _excuete_local_command(arguments)
        return True



    def auth_del(self, **kwargs):
        """
        Remove Authorised keyring
        """
        m = _model(**kwargs)
        u = _model_updator(m)
        u.hostname_refresh()
        if m.cluster_name == None:
            u.defaults_refresh()
        self.cluster_name = m.cluster_name
        u.load_confg(m.cluster_name)
        u.mon_members_refresh()
        q = _mdl_query(m)
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
        cmd_out = _excuete_local_command(arguments)
        return True


    def remove(self, **kwargs):
        """
        Delete keyring
        """
        m = _model(**kwargs)
        u = _model_updator(m)
        if m.cluster_name == None:
            u.defaults_refresh()
        self.cluster_name = m.cluster_name
        keyring_path = self.get_path_keyring()
        if os.path.isfile(keyring_path):
            try:
                os.remove(keyring_path)
            except:
                raise Error("Keyring could not be deleted")
        return True



class keyring_implementation_osd(keyring_implementation_base):
    def __init__(self):
        self.cluster_name = None
        self.keyring_name = "client.bootstrap-osd"

    def get_path_keyring(self):
        return _get_path_keyring_osd(self.cluster_name)

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
        self.cluster_name = None
        self.keyring_name = "client.bootstrap-rgw"

    def get_path_keyring(self):
        return _get_path_keyring_rgw(self.cluster_name)

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
        self.cluster_name = None
        self.keyring_name = "client.bootstrap-mds"

    def get_path_keyring(self):
        return _get_path_keyring_mds(self.cluster_name)

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
        self._availableKeys = set([ "osd", "mds", "rgw"])
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
            if name == "osd":
                implementation = keyring_implementation_osd()
            if name == "mds":
                implementation = keyring_implementation_mds()
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
