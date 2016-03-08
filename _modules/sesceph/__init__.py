import logging
import shlex
import tempfile
import stat
import ConfigParser
import os.path
import os
import platform
import json
import shutil
import constants

# local modules
import utils
import model
import mdl_updater
import presenter
import mdl_query
import utils
import keyring
import osd
import mon
import rgw
import mds

log = logging.getLogger(__name__)

__virtualname__ = 'sesceph'

__has_salt = True

try:
    import salt.client
    import salt.config
except :
    __has_salt = False

try:
    from salt.utils import which as _find_executable
except:
    from distutils.spawn import _find_executable



class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])


def __virtual__():
    if not constants._path_lsblk:
        log.info("Error 'lsblk' command not find.")
        return False
    return __virtualname__


def partition_list():
    '''
    List partitions by disk

    CLI Example:

        salt '*' sesceph.partitions_all
    '''
    m = model.model()
    u = mdl_updater.model_updater(m)
    u.symlinks_refresh()
    u.partitions_all_refresh()
    u.partition_table_refresh()
    p = presenter.mdl_presentor(m)
    return p.partitions_all()

def partition_list_osd():
    '''
    List all OSD data partitions by partition

    CLI Example:

        salt '*' sesceph.partitions_osd
    '''
    m = model.model()
    u = mdl_updater.model_updater(m)
    u.symlinks_refresh()
    u.partitions_all_refresh()
    u.discover_partitions_refresh()
    p = presenter.mdl_presentor(m)
    return p.discover_osd_partitions()


def partition_list_journal():
    '''
    List all OSD journal partitions by partition

    CLI Example:

        salt '*' sesceph.partitions_journal
    '''
    m = model.model()
    u = mdl_updater.model_updater(m)
    u.symlinks_refresh()
    u.partitions_all_refresh()
    u.discover_partitions_refresh()
    p = presenter.mdl_presentor(m)
    return p.discover_journal_partitions()

def osd_discover():
    """
    List all OSD by cluster

    CLI Example:

        salt '*' sesceph.osd_discover

    """
    m = model.model()
    u = mdl_updater.model_updater(m)

    u.symlinks_refresh()
    u.partitions_all_refresh()
    u.discover_partitions_refresh()
    p = presenter.mdl_presentor(m)
    return p.discover_osd()


def partition_is(dev):
    """
    Check whether a given device path is a partition or a full disk.

    CLI Example:

    .. code-block:: bash
    salt '*' sesceph.partition_is /dev/sdc1

    """
    osdc = osd.osd_ctrl()
    return osdc.is_partition(dev)


def _update_partition(action, dev, description):
    # try to make sure the kernel refreshes the table.  note
    # that if this gets ebusy, we are probably racing with
    # udev because it already updated it.. ignore failure here.

    # On RHEL and CentOS distros, calling partprobe forces a reboot of the
    # server. Since we are not resizing partitons so we rely on calling
    # partx

    utils.execute_local_command(
        [
             constants._path_partprobe,
             dev,
        ],
    )



def zap(dev):
    """
    Destroy the partition table and content of a given disk.
    """
    if not os.path.exists(dev):
        raise Error('Cannot find', dev)
    dmode = os.stat(dev).st_mode
    osdc = osd.osd_ctrl()
    if not stat.S_ISBLK(dmode) or osdc.is_partition(dev):
        raise Error('not full block device; cannot zap', dev)
    try:
        log.debug('Zapping partition table on %s', dev)

        # try to wipe out any GPT partition table backups.  sgdisk
        # isn't too thorough.
        lba_size = 4096
        size = 33 * lba_size
        with file(dev, 'wb') as dev_file:
            dev_file.seek(-size, os.SEEK_END)
            dev_file.write(size*'\0')

        utils.execute_local_command(
            [
                constants._path_sgdisk,
                '--zap-all',
                '--',
                dev,
            ],
        )
        utils.execute_local_command(
            [
                constants._path_sgdisk,
                '--clear',
                '--mbrtogpt',
                '--',
                dev,
            ],
        )


        _update_partition('-d', dev, 'zapped')
    except subprocess.CalledProcessError as e:
        raise Error(e)
    return True


def osd_prepare(**kwargs):
    """
    prepare an OSD

    CLI Example:

        salt '*' sesceph.osd_prepare 'osd_dev'='/dev/vdc' \\
                'journal_dev'='device' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid' \\
                'osd_fs_type'='xfs' \\
                'osd_uuid'='2a143b73-6d85-4389-a9e9-b8a78d9e1e07' \\
                'journal_uuid'='4562a5db-ff6f-4268-811d-12fd4a09ae98'
    Notes:

    cluster_uuid
        Set the deivce to store the osd data on.

    journal_dev
        Set the journal device. defaults to osd_dev.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster date will be added too. Defaults to the value found in local config.

    osd_fs_type
        set the file system to store OSD data with. Defaults to "xfs".

    osd_uuid
        set the OSD data UUID. If set will return if OSD with data UUID already exists.

    journal_uuid
        set the OSD journal UUID. If set will return if OSD with journal UUID already exists.
    """
    return osd.osd_prepare(**kwargs)


def osd_activate(**kwargs):
    """
    Activate an OSD

    CLI Example:

        salt '*' sesceph.osd_activate 'osd_dev'='/dev/vdc'
    """
    return osd.osd_activate(**kwargs)



def keyring_admin_create(**kwargs):
    """
    Create admin keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_admin_create \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "admin"
    return keyobj.create(**kwargs)


def keyring_admin_save(key_content=None, **kwargs):
    """
    Write admin keyring for cluster

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
    """
    if (key_content is None) != ('secret' in kwargs):
        raise Error("Set either the key_content or the key `secret`")
    if 'secret' in kwargs:
        utils.is_valid_base64(kwargs['secret'])

    keyobj = keyring.keyring_facard()
    keyobj.key_type = "admin"
    return keyobj.write(key_content, **kwargs)


def keyring_admin_purge(**kwargs):
    """
    Delete Mon keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_admin_purge \\
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If no ceph config file is found, this command will fail.
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "admin"
    return keyobj.remove(**kwargs)


def keyring_mon_create(**kwargs):
    """
    Create mon keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mon_create \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mon"
    return keyobj.create(**kwargs)


def keyring_mon_save(key_content=None, **kwargs):
    """
    Write admin keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mon_save \\
                '[mon.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mon = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    if (key_content is None) != ('secret' in kwargs):
        raise Error("Set either the key_content or the key `secret`")
    if 'secret' in kwargs:
        utils.is_valid_base64(kwargs['secret'])

    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mon"
    return keyobj.write(key_content, **kwargs)


def keyring_mon_purge(**kwargs):
    """
    Delete Mon keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mon_purge \\
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If no ceph config file is found, this command will fail.
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mon"
    return keyobj.remove(**kwargs)


def keyring_osd_create(**kwargs):
    """
    Create osd keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_osd_create \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "osd"
    return keyobj.create(**kwargs)


def keyring_osd_save(key_content=None, **kwargs):
    """
    Write admin keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_osd_save \\
                '[osd.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps osd = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    if (key_content is None) != ('secret' in kwargs):
        raise Error("Set either the key_content or the key `secret`")
    if 'secret' in kwargs:
        utils.is_valid_base64(kwargs['secret'])

    keyobj = keyring.keyring_facard()
    keyobj.key_type = "osd"
    return keyobj.write(key_content, **kwargs)


def keyring_osd_auth_add(**kwargs):
    """
    Write admin keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_osd_auth_add \\
                '[osd.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps osd = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "osd"
    return keyobj.auth_add(**kwargs)


def keyring_osd_auth_del(**kwargs):
    """
    Write rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_osd_auth_del \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "osd"
    return keyobj.auth_del(**kwargs)


def keyring_osd_purge(**kwargs):
    """
    Write admin keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_osd_purge \\
                '[osd.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps osd = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "osd"
    return keyobj.remove(**kwargs)



def keyring_mds_create(**kwargs):
    """
    Create mds keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mds_create \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mds"
    return keyobj.create(**kwargs)

def keyring_mds_save(key_content=None, **kwargs):
    """
    Write mds keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mds_save \\
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If the value is set, it will not be changed untill the keyring is deleted.
    """
    if (key_content is None) != ('secret' in kwargs):
        raise Error("Set either the key_content or the key `secret`")
    if 'secret' in kwargs:
        utils.is_valid_base64(kwargs['secret'])

    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mds"
    return keyobj.write(key_content, **kwargs)

def keyring_mds_auth_add(**kwargs):
    """
    Write mds keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mds_auth_add \\
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mds"
    return keyobj.auth_add(**kwargs)


def keyring_mds_auth_del(**kwargs):
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
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mds"
    return keyobj.auth_del(**kwargs)


def keyring_mds_purge(**kwargs):
    """
    Delete MDS keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_mds_purge \\
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If no ceph config file is found, this command will fail.
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "mds"
    return keyobj.remove(**kwargs)


def keyring_rgw_create(**kwargs):
    """
    Create rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_rgw_create \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "rgw"
    return keyobj.create(**kwargs)


def keyring_rgw_save(key_content=None, **kwargs):
    """
    Write rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_rgw_save \\
                '[rgw.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps rgw = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If the value is set, it will not be changed untill the keyring is deleted.
    """
    if (key_content is None) != ('secret' in kwargs):
        raise Error("Set either the key_content or the key `secret`")
    if 'secret' in kwargs:
        utils.is_valid_base64(kwargs['secret'])
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "rgw"
    return keyobj.write(key_content, **kwargs)

def keyring_rgw_auth_add(**kwargs):
    """
    Write rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_rgw_auth_add \\
                '[rgw.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps rgw = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "rgw"
    return keyobj.auth_add(**kwargs)


def keyring_rgw_auth_del(**kwargs):
    """
    Write rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_rgw_auth_del \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "rgw"
    return keyobj.auth_del(**kwargs)


def keyring_rgw_purge(**kwargs):
    """
    Delete rgw keyring for cluster

    CLI Example:

        salt '*' sesceph.keyring_rgw_purge \\
                '[rgw.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps rgw = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If no ceph config file is found, this command will fail.
    """
    keyobj = keyring.keyring_facard()
    keyobj.key_type = "rgw"
    return keyobj.remove(**kwargs)



def mon_is(**kwargs):
    """
    Is this a mon node

    CLI Example:

        salt '*' sesceph.mon_is \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.
    """
    ctrl_mon = mon.mon_facard(**kwargs)
    return ctrl_mon.is_mon()


def mon_status(**kwargs):
    """
    Get status from mon deamon

    CLI Example:

        salt '*' sesceph.mon_status \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    ctrl_mon = mon.mon_facard(**kwargs)
    return ctrl_mon.status()

def mon_quorum(**kwargs):
    """
    Is mon deamon in quorum

    CLI Example:

        salt '*' sesceph.mon_quorum \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    ctrl_mon = mon.mon_facard(**kwargs)
    return ctrl_mon.quorum()



def mon_active(**kwargs):
    """
    Is mon deamon running

    CLI Example:

        salt '*' sesceph.mon_active \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    ctrl_mon = mon.mon_facard(**kwargs)
    return ctrl_mon.active()


def mon_create(**kwargs):
    """
    Create a mon node

    CLI Example:

        salt '*' sesceph.mon_create \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    ctrl_mon = mon.mon_facard(**kwargs)
    return ctrl_mon.create()


def rgw_pools_create(**kwargs):
    """
    Create pools for rgw
    """
    ctrl_rgw = rgw.rgw_ctrl(**kwargs)
    return ctrl_rgw.rgw_pools_create()

def rgw_pools_missing(**kwargs):
    """
    Show pools missing for rgw
    """
    ctrl_rgw = rgw.rgw_ctrl(**kwargs)
    return ctrl_rgw.rgw_pools_missing()


def rgw_create(**kwargs):
    """
    Create a rgw
    """
    ctrl_rgw = rgw.rgw_ctrl(**kwargs)
    return ctrl_rgw.create(**kwargs)


def rgw_destroy(**kwargs):
    """
    Remove a rgw
    """
    ctrl_rgw = rgw.rgw_ctrl(**kwargs)
    return ctrl_rgw.destroy(**kwargs)



def mds_create(**kwargs):
    """
    Create a mds
    """
    ctrl_mds = mds.mds_ctrl(**kwargs)
    return ctrl_mds.create(**kwargs)


def mds_destroy(**kwargs):
    """
    Remove a mds
    """
    ctrl_mds = mds.mds_ctrl(**kwargs)
    return ctrl_mds.destroy(**kwargs)


def keyring_auth_list(**kwargs):
    """
    List all cephx authorization keys

    CLI Example:

        salt '*' sesceph.auth_list \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.
    """
    m = model.model(**kwargs)
    u = mdl_updater.model_updater(m)
    u.hostname_refresh()
    try:
        u.defaults_refresh()
    except:
        return {}
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    u.auth_list()
    p = presenter.mdl_presentor(m)
    return p.auth_list()


def pool_list(**kwargs):
    """
    List all cephx authorization keys

    CLI Example:

        salt '*' sesceph.pool_list \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.
    """
    m = model.model(**kwargs)
    u = mdl_updater.model_updater(m)
    u.hostname_refresh()
    try:
        u.defaults_refresh()
    except:
        return {}
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    u.pool_list()
    p = presenter.mdl_presentor(m)
    return p.pool_list()


def pool_add(pool_name, **kwargs):
    """
    List all cephx authorization keys

    CLI Example:

        salt '*' sesceph.pool_add pool_name \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    pg_num
        Default to 8

    pgp_num
        Default to pg_num

    pool_type
        can take values "replicated" or "erasure"

    erasure_code_profile
        Set the "erasure_code_profile"

    crush_ruleset
        Set the crush map rule set
    """
    m = model.model(**kwargs)
    u = mdl_updater.model_updater(m)
    u.hostname_refresh()
    try:
        u.defaults_refresh()
    except:
        return {}
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    u.pool_list()
    u.pool_add(pool_name, **kwargs)
    return True


def pool_del(pool_name, **kwargs):
    """
    List all cephx authorization keys

    CLI Example:

        salt '*' sesceph.pool_del pool_name \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.
    """
    m = model.model(**kwargs)
    u = mdl_updater.model_updater(m)
    u.hostname_refresh()
    try:
        u.defaults_refresh()
    except:
        return {}
    u.load_confg(m.cluster_name)
    u.mon_members_refresh()
    u.pool_list()
    u.pool_del(pool_name)
    return True


def purge():
    """
    purge ceph configuration on the node

    CLI Example:

        salt '*' sesceph.purge
    """
    arguments = [
            constants._path_systemctl,
            "stop",
            "ceph*",
            ]
    output = utils.execute_local_command(arguments)
    if output["retcode"] != 0:
        raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
            " ".join(arguments),
            output["retcode"],
            output["stdout"],
            output["stderr"]
            ))
    m = model.model()
    u = mdl_updater.model_updater(m)
    u.symlinks_refresh()
    u.partitions_all_refresh()
    u.discover_partitions_refresh()

    for part in m.partitions_osd:
        disk = m.part_pairent.get(part)
        if disk is None:
            continue
        disk_details = m.lsblk.get(disk)
        if disk_details is None:
            continue
        all_parts = disk_details.get('PARTITION')
        if all_parts is None:
            continue
        part_details = all_parts.get(part)
        if part_details is None:
            continue
        mountpoint =  part_details.get("MOUNTPOINT")
        if mountpoint is None:
            continue
        arguments = [
            "umount",
            mountpoint
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
                " ".join(arguments),
                output["retcode"],
                output["stdout"],
                output["stderr"]
                ))

    arguments = [
            "rm",
            "-rf",
            "--one-file-system",
            "/var/lib/ceph",
            ]
    output = utils.execute_local_command(arguments)
    if output["retcode"] != 0:
        raise Error("Failed executing '%s' Error rc=%s, stdout=%s stderr=%s" % (
            " ".join(arguments),
            output["retcode"],
            output["stdout"],
            output["stderr"]
            ))


def ceph_version():
    """
    Get the version of ceph installed
    """
    m = model.model()
    u = mdl_updater.model_updater(m)
    u.ceph_version_refresh()
    p = presenter.mdl_presentor(m)
    return p.ceph_version()
