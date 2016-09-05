A simple example salt state files to use with

https://github.com/oms4suse/python-ceph-cfg

You should have a working salt setup for this.

Copy the files from this repo into your respective salt and pillar directories
(default is /srv/{salt,pillar}).
Edit the configuration data in the pillar files in the pillar directory. For now edit
the various secret keys and which device should become be used on osd nodes.
Then run salt '*' state.apply.
This will install ceph and python-ceph-cfg on all your nodes and start mon's,
osd's and mds' on all nodes that have osd, mon or mds in their salt minion names.

E.g. 3 node names mon-osd-node0, mon-osd-node1 and mon-osd-mds-node2 will give
you a cluster with three mon's, three osd's and one mds.

Missing Features to be added soon:
* teardown states
