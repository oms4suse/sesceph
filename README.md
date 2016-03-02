This is a basic salt module for ceph configuration and deployment.

Please do not expect production stability yet. Function names may still change.

All methods in this module are intended to be atomic and idempotent. Some state
changes are in practice made up of many steps, but will verify that all stages
have succeeded before presenting the result to the caller. Most functions are 
fully idempotent in operation so can be repeated or retried as often as 
necessary without causing unintended effects. This is so clients of this module
do not need to keep track of whether the operation was already performed or not.
Some methods do depend upon the successful completion of other methods. While 
not strictly idempotent, this is considered acceptable modules having 
dependencies on other methods operation should present clear error messages.

Installation
------------

Copy the content of "_modules/sesceph" to

    /srv/salt/_modules/sesceph

and run:

    salt '*' saltutil.sync_modules

This will distribute the runner to all salt minions. To verify this process has
succeeded, on a specific node it is best to try and access the online
documentation.

Documentation
-------------

To show sesceph method:

    salt "ceph-node*" sesceph -d

All API methods should provide documentation. To list all runners methods
available in your salt system please run:

    salt-run doc.execution

Execution
---------

All functions in this application are under the sesceph namespace.

Example
~~~~~~~

Get a list of potential MON keys:

    # salt "*ceph-node*" sesceph.keyring_admin_create

This will not persist the created key, but if a persistent key already exists 
this function will return the persistent key.

Use one output to write the keyring to admin nodes:

    # salt "*ceph-node*" sesceph.keyring_admin_save '[client.admin]
    > key = AQDHYqZWkGHiEhAA5T+214L5CiIeek5o3zGZtQ==
    > auid = 0
    > caps mds = "allow *"
    > caps mon = "allow *"
    > caps osd = "allow *"
    > '

Repeat the process for the MON keyring:

    # salt "*ceph-node*" sesceph.keyring_mon_create

Use one output to write the keyring to MON nodes:

    # salt "*ceph-node*" sesceph.keyring_mon_save '[mon.]
    > key = AQCpY6ZW2KCRExAAxbJ+dljnln40wYmb7UvHcQ==
    > caps mon = "allow *"
    > '

Create the monitor daemons:

    # salt "*ceph-node*" sesceph.mon_create

The sesceph.mon_create function requires both the admin and the mon keyring to
exist before this function can be successful.

Get monitor status:

    # salt "*ceph-node*" sesceph.mon_status

The sesceph.mon_status function requires the sesceph.mon_create function to have
completed successfully.

List authorized keys:

    # salt "*ceph-node*" sesceph.keyring_auth_list

The sesceph.auth_list function will only execute successfully on nodes running 
mon daemons which are in quorum.

Get a list of potential OSD keys:

    # salt "*ceph-node*" sesceph.keyring_osd_create

Use one output to write the keyring to OSD nodes:

    # salt "*ceph-node*" sesceph.keyring_osd_save '[client.bootstrap-osd]
    > key = AQAFNKZWaByNLxAAmIx9CbAaN+9L5KvZunmo2w==
    > caps mon = "allow profile bootstrap-osd"
    > '

Authorise the OSD boot strap:

    # salt "*ceph-node*" sesceph.keyring_osd_auth_add

The sesceph.keyring_osd_auth_add function will only execute successfully on nodes
running mon daemons which are in quorum.

Create some OSDs

    # salt "*ceph-node*" sesceph.osd_prepare  osd_dev=/dev/vdb

The sesceph.osd_prepare function will only execute successfully on nodes
with OSD boot strap keys writern.

SLS example
~~~~~~~~~~~

An example SLS file. After the writing of all keys:

    mon_create:
      module.run:
        - name:  sesceph.mon_create

    keyring_osd_auth_add:
      module.run:
        - name:  sesceph.keyring_osd_auth_add

    prepare:
      module.run:
        - name: sesceph.osd_prepare
        - kwargs: {
            osd_dev: /dev/vdb
            }

Common Use cases
----------------

To discover OSD's

    salt 'ceph-node*' sesceph.osd_discover

Will query all nodes whose name starts with 'ceph-node*' and return all OSDs
by cluster for example:

    ceph-node2.example.org:
        ----------
        5abcca4c-efb3-4c8f-96eb-cb85c30af50e:
            |_
              ----------
              dev:
                  /dev/vdc1
              dev_journal:
                  /dev/vdc2
              dev_parent:
                  /dev/vdc
              fsid:
                  be2a3e75-6190-406f-ab41-435ed5257319
              journal_uuid:
                  bd760a10-d78b-491a-9569-d80d329e0489
              magic:
                  ceph osd volume v026
              whoami:
                  7
            |_
              ----------
              dev:
                  /dev/vdb1
              dev_journal:
                  /dev/vdb2
              dev_parent:
                  /dev/vdb
              fsid:
                  4deff815-0e6f-498a-aa24-8fdbe41430de
              journal_uuid:
                  aac8012a-1d5e-414a-b969-54b8e3cf1240
              magic:
                  ceph osd volume v026
              whoami:
                  0

This allowed me to easily identify orphaned OSDs :)

Code layout
-----------

The code is structured with basic methods calling 3 main class types.

1. Models

This stores all the gathered configuration on the node to apply the function.

2. Loaders

These objects are used to update the Model.

3. Presenters

These objects are used to present the data in the model to the API users.
