0.1.4
-----
* Work around salt bug when kwargs and args have same name.
* Add cephfs methods.

0.1.3
-----
* Merge changes from up streaming this code to salt.
* Remove potential infante loop when python-ceph-cfg
  is not installed.

0.1.2
-----
* Fix docstrings
* Change execution module namespace to ceph_cfg from ceph.

  * Avoiding namespace clash with calamari.

0.1.1
-----
* Removed typos from documentation.

0.1.0
-----
* Change code base to use a library.
* Add state quorum.
* Update example file examples/cluster_buildup.sls

0.0.9
-----
* Bugfix Create bootstrapmon dir if missing.
* Documentation fixes

0.0.8
-----
* Rename module as ceph

0.0.7
------
* rgw keyring now more locked using profiles.
* mds keyring now more locked using profiles.
* improve logging of commands with spaces in attributes.

  * supporting cut and paste into bash.

0.0.6
------
* Update documentation to use new keyring functions.
* zap method to use kwargs.

0.0.5
------
* Allow "*auth_add" and "*auth_del" run not just on mon nodes.
* Add new public methods:

  * keyring_create
  * keyring_save
  * keyring_purge
  * keyring_present
  * keyring_auth_add
  * keyring_auth_del

0.0.4
------
* Add public methods cluster_quorum and cluster_status.
* Add to example file with cluster_status
* Add require into example file.
* Restructure cluster operations to make better time out handling.

