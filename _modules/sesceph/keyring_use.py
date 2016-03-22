# Python imports
import logging

# local modules
import model
import mdl_updater
import keyring
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

def keyring_create_type(**kwargs):
    keyring_type = kwargs.get("keyring_type")
    if (keyring_type is None):
        raise Error("keyring_type is None")
    m = model.model(**kwargs)
    u = mdl_updater.model_updater(m)
    u.hostname_refresh()
    u.defaults_refresh()
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    keyobj = keyring.keyring_facard(m)
    keyobj.key_type = keyring_type
    return keyobj.create(**kwargs)


def keyring_present_type(**kwargs):
    """
    Check if keyring exists on disk

    CLI Example:

        salt '*' sesceph.keyring_admin_save \\
                '[mon.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mon = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    keyring_type
        Set the keyring type
    """
    keyring_type = kwargs.get("keyring_type")
    if (keyring_type is None):
        raise Error("keyring_type is None")
    m = model.model(**kwargs)
    u = mdl_updater.model_updater(m)
    u.hostname_refresh()
    try:
        u.defaults_refresh()
    except:
        pass
    keyobj = keyring.keyring_facard(m)
    keyobj.key_type = keyring_type
    return keyobj.present(**kwargs)


def keyring_purge_type(**kwargs):
    keyring_type = kwargs.get("keyring_type", None)
    if (keyring_type is None):
        raise Error("keyring_type is not set")
    m = model.model(**kwargs)
    u = mdl_updater.model_updater(m)
    u.hostname_refresh()
    u.defaults_refresh()
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    keyobj = keyring.keyring_facard(m)
    keyobj.key_type = keyring_type
    return keyobj.remove(**kwargs)


def keyring_save_type(**kwargs):
    keyring_type = kwargs.get("keyring_type")
    if (keyring_type is None):
        raise Error("keyring_type is None")
    key_content = kwargs.get("key_content")
    secret = kwargs.get("secret")
    if (key_content is None) and (secret is None):
        raise Error("Set either the key_content or the key `secret`")
    if 'secret' in kwargs:
        utils.is_valid_base64(kwargs['secret'])
    m = model.model(**kwargs)
    u = mdl_updater.model_updater(m)
    u.hostname_refresh()
    u.defaults_refresh()
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    keyobj = keyring.keyring_facard(m)
    keyobj.key_type = keyring_type
    return keyobj.write(key_content, **kwargs)


def keyring_auth_add_type(key_content=None, **kwargs):
    keyring_type = kwargs.get("keyring_type")
    if (keyring_type is None):
        raise Error("keyring_type is None")
    if (keyring_type in set(["mon","admin"])):
        raise Error("keyring_type is %s" % (keyring_type))
    m = model.model(**kwargs)
    u = mdl_updater.model_updater(m)
    u.hostname_refresh()
    u.defaults_refresh()
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    q = mdl_query.mdl_query(m)
    if not q.mon_is():
        raise Error("Not ruining a mon daemon")
    u.mon_status()
    keyobj = keyring.keyring_facard(m)
    keyobj.key_type = keyring_type
    return keyobj.auth_add(**kwargs)



def keyring_auth_del_type(**kwargs):
    """
    Write rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mds_auth_del \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyring_type = kwargs.get("keyring_type")
    if (keyring_type is None):
        raise Error("keyring_type is None")
    if (keyring_type in set(["mon","admin"])):
        raise Error("keyring_type is %s" % (keyring_type))
    m = model.model(**kwargs)
    u = mdl_updater.model_updater(m)
    u.hostname_refresh()
    u.defaults_refresh()
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    q = mdl_query.mdl_query(m)
    if not q.mon_is():
        raise Error("Not ruining a mon daemon")
    u.mon_status()
    keyobj = keyring.keyring_facard(m)
    keyobj.key_type = keyring_type
    return keyobj.auth_del(**kwargs)



