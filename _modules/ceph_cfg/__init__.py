# -*- coding: utf-8 -*-
'''
Module to provide ceph control with salt.

:depends:   - ceph_cfg Python module

.. versionadded:: Carbon
'''
# Import Python Libs
from __future__ import absolute_import
import logging


log = logging.getLogger(__name__)

__virtualname__ = 'ceph_cfg'

try:
    import ceph_cfg
    # Due to a bug in salt
    # https://github.com/saltstack/salt/issues/35444
    # we cant rely on previous import to
    # detect that the library ceph_cfg is present.
    # Hence we import the version of the library.
    from ceph_cfg.__version__ import version as ceph_cfg_version
    HAS_CEPH_CFG = True
except ImportError:
    HAS_CEPH_CFG = False


def __virtual__():
    if HAS_CEPH_CFG is False:
        msg = 'ceph_cfg unavailable: {0} execution module cant be loaded '.format(__virtualname__)
        return False, msg
    return __virtualname__


def partition_list():
    '''
    List partitions by disk

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.partition_list
    '''
    return ceph_cfg.partition_list()


def partition_list_osd():
    '''
    List all OSD data partitions by partition

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.partition_list_osd
    '''
    return ceph_cfg.partition_list_osd()


def partition_list_journal():
    '''
    List all OSD journal partitions by partition

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.partition_list_journal
    '''
    return ceph_cfg.partition_list_journal()


def osd_discover():
    '''
    List all OSD by cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.osd_discover

    '''
    return ceph_cfg.osd_discover()


def partition_is(dev):
    '''
    Check whether a given device path is a partition or a full disk.

    CLI Example:

    .. code-block:: bash

    salt '*' ceph_cfg.partition_is /dev/sdc1

    '''
    return ceph_cfg.partition_is(dev)


def zap(target=None, **kwargs):
    '''
    Destroy the partition table and content of a given disk.

    .. code-block:: bash

        salt '*' ceph_cfg.osd_prepare 'dev'='/dev/vdc' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'

    Notes:

    dev
        The block device to format.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster date will be added too. Defaults to the value found in
        local config.
    '''
    if target is not None:
        log.warning("Depricated use of function, use kwargs")
    target = kwargs.get("dev", target)
    kwargs["dev"] = target
    return ceph_cfg.zap(**kwargs)


def osd_prepare(**kwargs):
    '''
    prepare an OSD

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.osd_prepare 'osd_dev'='/dev/vdc' \\
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
    '''
    return ceph_cfg.osd_prepare(**kwargs)


def osd_activate(**kwargs):
    '''
    Activate an OSD

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.osd_activate 'osd_dev'='/dev/vdc'
    '''
    return ceph_cfg.osd_activate(**kwargs)


def osd_reweight(**kwargs):
    """
    Reweight an OSD

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.osd_reweight \\
                'cluster_name'='admin' \\
                'cluster_name'='ceph' \\
                'osd_number'='23' \\
                'weight'='0'
    Notes:


    osd_number
        OSD number to reweight.

    weight
        The new weight for the osd. Weight is a float, and must be
        in the range 0 to 1. Setting the weight to 0 will drain an OSD.

    cluster_uuid
        Set the deivce to store the osd data on.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    """
    return ceph_cfg.osd_reweight(**kwargs)


def keyring_create(**kwargs):
    '''
    Create keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_create \\
                'keyring_type'='admin' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    keyring_type
        Required paramter
        Can be set to:
            admin, mon, osd, rgw, mds

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.keyring_create(**kwargs)


def keyring_save(**kwargs):
    '''
    Create save keyring locally

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_save \\
                'keyring_type'='admin' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid' \\
                ''
    Notes:

    keyring_type
        Required paramter
        Can be set to:
            admin, mon, osd, rgw, mds

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.keyring_save(**kwargs)


def keyring_purge(**kwargs):
    '''
    Delete keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_purge \\
                'keyring_type'='admin' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    keyring_type
        Required paramter
        Can be set to:
            admin, mon, osd, rgw, mds

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If no ceph config file is found, this command will fail.
    '''
    return ceph_cfg.keyring_purge(**kwargs)


def keyring_present(**kwargs):
    '''
    Is keyring on disk

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_present \\
                'keyring_type'='admin' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    keyring_type
        Required paramter
        Can be set to:
            admin, mon, osd, rgw, mds

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.keyring_present(**kwargs)


def keyring_auth_add(**kwargs):
    '''
    Add keyring to authorised list

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_auth_add \\
                'keyring_type'='admin' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    keyring_type
        Required paramter
        Can be set to:
            admin, mon, osd, rgw, mds

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.keyring_auth_add(**kwargs)


def keyring_auth_del(**kwargs):
    '''
    Remove keyring from authorised list

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_osd_auth_del \\
                'keyring_type'='admin' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    keyring_type
        Required paramter
        Can be set to:
            admin, mon, osd, rgw, mds

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.keyring_auth_del(**kwargs)


def keyring_admin_create(**kwargs):
    '''
    Create admin keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_admin_create \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "admin"
    return keyring_create(**params)


def keyring_admin_save(key_content=None, **kwargs):
    '''
    Write admin keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_admin_save \\
                '[mon.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mon = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "admin"
    if key_content is None:
        return keyring_save(**params)
    log.warning("keyring_admin_save using legacy argument call")
    params["key_content"] = str(key_content)
    return keyring_save(**params)


def keyring_admin_purge(**kwargs):
    '''
    Delete Mon keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_admin_purge \\
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If no ceph config file is found, this command will fail.
    '''
    params = dict(kwargs)
    params["keyring_type"] = "admin"
    return keyring_purge(**params)


def keyring_mon_create(**kwargs):
    '''
    Create mon keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_mon_create \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "mon"
    return keyring_create(**params)


def keyring_mon_save(key_content=None, **kwargs):
    '''
    Write admin keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_mon_save \\
                '[mon.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mon = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "mon"
    if key_content is None:
        return keyring_save(**params)
    log.warning("keyring_admin_save using legacy argument call")
    params["key_content"] = str(key_content)
    return keyring_save(**params)


def keyring_mon_purge(**kwargs):
    '''
    Delete Mon keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_mon_purge \\
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If no ceph config file is found, this command will fail.
    '''
    params = dict(kwargs)
    params["keyring_type"] = "mon"
    return keyring_purge(**params)


def keyring_osd_create(**kwargs):
    '''
    Create osd keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_osd_create \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "osd"
    return keyring_create(**params)


def keyring_osd_save(key_content=None, **kwargs):
    '''
    Write admin keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_osd_save \\
                '[osd.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps osd = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "osd"
    if key_content is None:
        return keyring_save(**params)
    log.warning("keyring_admin_save using legacy argument call")
    params["key_content"] = str(key_content)
    return keyring_save(**params)


def keyring_osd_auth_add(**kwargs):
    '''
    Write admin keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_osd_auth_add \\
                '[osd.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps osd = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "osd"
    return keyring_auth_add(**params)


def keyring_osd_auth_del(**kwargs):
    '''
    Write rgw keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_osd_auth_del \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "osd"
    return keyring_auth_del(**params)


def keyring_osd_purge(**kwargs):
    '''
    Write admin keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_osd_purge \\
                '[osd.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps osd = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "osd"
    return keyring_purge(**params)


def keyring_mds_create(**kwargs):
    '''
    Create mds keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_mds_create \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "mds"
    return keyring_create(**params)


def keyring_mds_save(key_content=None, **kwargs):
    '''
    Write mds keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_mds_save \\
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If the value is set, it will not be changed untill the keyring is deleted.
    '''
    params = dict(kwargs)
    params["keyring_type"] = "mds"
    if key_content is None:
        return keyring_save(**params)
    log.warning("keyring_admin_save using legacy argument call")
    params["key_content"] = str(key_content)
    return keyring_save(**params)


def keyring_mds_auth_add(**kwargs):
    '''
    Write mds keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_mds_auth_add \\
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "mds"
    return keyring_auth_add(**params)


def keyring_mds_auth_del(**kwargs):
    '''
    Write rgw keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_mds_auth_del \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "mds"
    return keyring_auth_del(**params)


def keyring_mds_purge(**kwargs):
    '''
    Delete MDS keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_mds_purge \\
                '[mds.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps mds = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If no ceph config file is found, this command will fail.
    '''
    params = dict(kwargs)
    params["keyring_type"] = "mds"
    return keyring_purge(**params)


def keyring_rgw_create(**kwargs):
    '''
    Create rgw keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_rgw_create \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "rgw"
    return keyring_create(**params)


def keyring_rgw_save(key_content=None, **kwargs):
    '''
    Write rgw keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_rgw_save \\
                '[rgw.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps rgw = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If the value is set, it will not be changed untill the keyring is deleted.
    '''
    params = dict(kwargs)
    params["keyring_type"] = "rgw"
    if key_content is None:
        return keyring_save(**params)
    log.warning("keyring_admin_save using legacy argument call")
    params["key_content"] = str(key_content)
    return keyring_save(**params)


def keyring_rgw_auth_add(**kwargs):
    '''
    Write rgw keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_rgw_auth_add \\
                '[rgw.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps rgw = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "rgw"
    return keyring_auth_add(**params)


def keyring_rgw_auth_del(**kwargs):
    '''
    Write rgw keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_rgw_auth_del \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    params = dict(kwargs)
    params["keyring_type"] = "rgw"
    return keyring_auth_del(**params)


def keyring_rgw_purge(**kwargs):
    '''
    Delete rgw keyring for cluster

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_rgw_purge \\
                '[rgw.]\n\tkey = AQA/vZ9WyDwsKRAAxQ6wjGJH6WV8fDJeyzxHrg==\n\tcaps rgw = \"allow *\"\n' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".

    If no ceph config file is found, this command will fail.
    '''
    params = dict(kwargs)
    params["keyring_type"] = "rgw"
    return keyring_purge(**params)


def mon_is(**kwargs):
    '''
    Is this a mon node

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.mon_is \\
                'mon_name'='mon_01' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    mon_name
        Set the mon service name. Required

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.
    '''
    return ceph_cfg.mon_is(**kwargs)


def mon_status(**kwargs):
    '''
    Get status from mon deamon

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.mon_status \\
                'mon_name'='mon_01' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    mon_name
        Set the mon service name. Required

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.mon_status(**kwargs)


def mon_quorum(**kwargs):
    '''
    Is mon deamon in quorum

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.mon_quorum \\
                'mon_name'='mon_01' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    mon_name
        Set the mon service name. Required

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.mon_quorum(**kwargs)


def mon_active(**kwargs):
    '''
    Is mon deamon running

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.mon_active \\
                'mon_name'='mon_01' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    mon_name
        Set the mon serrvice name. Required

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.mon_active(**kwargs)


def mon_create(**kwargs):
    '''
    Create a mon service on node

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.mon_create \\
                'mon_name'='new_mon' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    mon_name
        Set the mon service name. Required

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.mon_create(**kwargs)


def mon_destroy(**kwargs):
    '''
    Destroy a mon service

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.mon_destroy \\
                'mon_name'='wrong_node' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    mon_name
        Set the mon service name. Required

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.mon_destroy(**kwargs)


def mon_list(**kwargs):
    '''
    List mon services on node

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.mon_create \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.mon_list(**kwargs)


def rgw_pools_create(**kwargs):
    '''
    Create pools for rgw

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.rgw_pools_create

    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.rgw_pools_create(**kwargs)


def rgw_pools_missing(**kwargs):
    '''
    Show pools missing for rgw

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.rgw_pools_missing

    Notes:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.rgw_pools_missing(**kwargs)


def rgw_create(**kwargs):
    '''
    Create a rgw

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.rgw_create \\
                'name' = 'rgw.name' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'

    Notes:

    name:
        Required paramter
        Set the rgw client name. Must start with 'rgw.'

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.rgw_create(**kwargs)


def rgw_destroy(**kwargs):
    '''
    Remove a rgw

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.rgw_destroy \\
                'name' = 'rgw.name' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'

    Notes:

    name:
        Required paramter
        Set the rgw client name. Must start with 'rgw.'

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.rgw_destroy(**kwargs)


def mds_create(**kwargs):
    '''
    Create a mds

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.mds_create \\
                'name' = 'mds.name' \\
                'port' = 1000, \\
                'addr' = 'fqdn.example.org' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'

    Notes:

    name:
        Required paramter
        Set the rgw client name. Must start with 'mds.'

    port:
        Required paramter
        Port for the mds to listen to.

    addr:
        Required paramter
        Address or IP address for the mds to listen to.

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.mds_create(**kwargs)


def mds_destroy(**kwargs):
    '''
    Remove a mds

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.mds_destroy \\
                'name' = 'mds.name' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'

    Notes:

    name:
        Required paramter
        Set the rgw client name. Must start with 'mds.'

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.mds_destroy(**kwargs)


def keyring_auth_list(**kwargs):
    '''
    List all cephx authorization keys

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.keyring_auth_list \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.
    '''
    return ceph_cfg.keyring_auth_list(**kwargs)


def pool_list(**kwargs):
    '''
    List all pools

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.pool_list \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.
    '''
    return ceph_cfg.pool_list(**kwargs)


def pool_add(pool_name, **kwargs):
    '''
    Create a pool

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.pool_add pool_name \\
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
    '''
    return ceph_cfg.pool_add(pool_name, **kwargs)


def pool_del(pool_name, **kwargs):
    '''
    Delete a pool

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.pool_del pool_name \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.
    '''
    return ceph_cfg.pool_del(pool_name, **kwargs)


def purge(**kwargs):
    '''
    purge ceph configuration on the node

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.purge \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'

    Notes:

    cluster_name
        Set the cluster name. Defaults to "ceph".

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.
    '''
    return ceph_cfg.purge(**kwargs)


def ceph_version():
    '''
    Get the version of ceph installed
    '''
    return ceph_cfg.ceph_version()


def cluster_quorum(**kwargs):
    '''
    Get the cluster's quorum status

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.cluster_quorum \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:
    Get the cluster quorum status.

    Scope:
    Cluster wide

    Arguments:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.cluster_quorum(**kwargs)


def cluster_status(**kwargs):
    '''
    Get the cluster status

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.cluster_status \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:
    Get the cluster status including health if in quorum.

    Scope:
    Cluster wide

    Arguments:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.cluster_status(**kwargs)


def cephfs_list(**kwargs):
    '''
    list the cephfs filesystems

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.cephfs_ls \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:
    List the cephfs instances.

    Scope:
    Cluster wide

    Arguments:

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.cephfs_ls(**kwargs)


def cephfs_add(fs_name, **kwargs):
    '''
    Add a cephfs filesystems

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.cephfs_add \\
                new_cephfs \\
                'pool_data'='pool_data_new_cephfs' \\
                'pool_metadata'='pool_metadata_new_cephfs' \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:
    More than one cephfs is an experimental feature in ceph.

    Scope:
    Cluster wide

    Arguments:

    fs_name:
        file system name to create.

    pool_data:
        ceph pool to store the data for filesystem.

    pool_metadata:
        ceph pool to store the mata data for filesystem.

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.cephfs_add(fs_name, **kwargs)


def cephfs_del(fs_name, **kwargs):
    '''
    Delete a cephfs filesystem

    CLI Example:

    .. code-block:: bash

        salt '*' ceph_cfg.cephfs_del \\
                del_cephfs \\
                'cluster_name'='ceph' \\
                'cluster_uuid'='cluster_uuid'
    Notes:
    All mon nodes should be stopped to allow this operation to success.

    Scope:
    Cluster wide

    Arguments:

    fs_name:
        file system name to create.

    cluster_uuid
        Set the cluster UUID. Defaults to value found in ceph config file.

    cluster_name
        Set the cluster name. Defaults to "ceph".
    '''
    return ceph_cfg.cephfs_del(fs_name, **kwargs)
