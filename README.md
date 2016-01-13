This is a basic salt api for ceph configuration management.

This API is very early stages, and I still think all the function names need to
possibly be changed. Please do not expect production stability yet.

To support text based API's "sesceph.osd_prepare" can be run many times, and
will not error if the command has already been run once before. This is intended
to be done for all state applying commands.

So far I have mainly developed it as a CLI. For example:

    salt 'ceph-node*' sesceph.discover_osd

Will query all nodes who's name starts with 'ceph-node*' and return all OSD's
by  cluster for example:


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

This allowed me to easily identify orphaned OSD's :)

Instalation
-----------

copy the content of "sesceph" to 

    /srv/salt/_modules/sesceph

and run:

    salt '*' saltutil.sync_modules

This will distribute the runner to all salt minions.

Docuemntation
-------------

All API methods shoudl provide documentation, to list all runners methods 
available in your salt system please run:

    salt-run doc.execution

Exectution
----------

All functions in this application are under the sesceph namespace.

Code layout
-----------

The code is structured with basic methods calling 3 main classes types.

1. Models

This stores all the gathered configuration on the node to apply the function.

2. Loaders

These objects are used to update the Model.

3. Presenters

These objects are used to present the data in the model to the API users.






