# We need a ceph config file before we start.
#
# Note:
# - The file name is dependennt on the cluster name:
#    /etc/ceph/${CLUSTER_NAME}.conf

/etc/ceph/ceph.conf:
  file:
    - managed
    - source:
        # Where to get the source file will have to be customised to your enviroment.
        - salt://osceph/ceph.conf
    - user: root
    - group: root
    - mode: 644
    - makedirs: True

# First we need to create the keys.
#
# Note:
# - This only needs to be done once per site.

keyring_admin_create:
  module.run:
    - name: sesceph.keyring_admin_create
    - require:
      - file: /etc/ceph/ceph.conf


keyring_mon_create:
  module.run:
    - name: sesceph.keyring_mon_create
    - require:
      - file: /etc/ceph/ceph.conf


keyring_osd_create:
  module.run:
    - name: sesceph.keyring_osd_create
    - require:
      - file: /etc/ceph/ceph.conf


keyring_rgw_create:
  module.run:
    - name: sesceph.keyring_rgw_create
    - require:
      - file: /etc/ceph/ceph.conf


keyring_mds_create:
  module.run:
    - name: sesceph.keyring_mds_create
    - require:
      - file: /etc/ceph/ceph.conf

# Save the keys to the nodes so ceph can use them.
#
# Note:
# - You should customise the 'secret' values for your site using the values from
#   the previous create step

keyring_admin_save:
  module.run:
    - name: sesceph.keyring_admin_save
    - kwargs: {
       'secret' : 'AQBR8KhWgKw6FhAAoXvTT6MdBE+bV+zPKzIo6w=='
        }


keyring_mon_save:
  module.run:
    - name: sesceph.keyring_mon_save
    - kwargs: {
       'secret' : 'AQB/8KhWmIfENBAABq8EEbzCJMjEFoazMNb+oQ=='
        }


keyring_osd_save:
  module.run:
    - name: sesceph.keyring_osd_save
    - kwargs: {
       'secret' : 'AQCxU6dWKJzuEBAAjh0WSiThjl+Ruvj3QCsDDQ=='
        }


keyring_rgw_save:
  module.run:
    - name: sesceph.keyring_rgw_save
    - kwargs: {
       'secret' : 'AQDant1WGP7qJBAA1Iqr9YoNo4YExai4ieXYMg=='
        }

keyring_mds_save:
  module.run:
    - name: sesceph.keyring_mds_save
    - kwargs: {
       'secret' : 'AQADn91WzLT9OBAA+LqKkXFBzwszBX4QkCkFYw=='
        }

# Create the mon server
#
# Note:
# - This will throw and exception on non mon nodes.
# - This is depenent on having 'saved' the mon and admin keys.

mon_create:
    module.run:
    - name: sesceph.mon_create

# Add the OSD key to the clusters authorized key list

keyring_osd_auth_add:
  module.run:
    - name: sesceph.keyring_osd_auth_add

# Add the rgw key to the clusters authorized key list

keyring_auth_add_rgw:
  module.run:
    - name: sesceph.keyring_rgw_auth_add

# Add the mds key to the clusters authorized key list

keyring_auth_add_mds:
  module.run:
    - name: sesceph.keyring_mds_auth_add

# Prepare disks for OSD use

prepare_vdb:
  module.run:
    - name: sesceph.osd_prepare
    - kwargs: {
        osd_dev: /dev/vdb
        }


prepare_vdc:
  module.run:
    - name: sesceph.osd_prepare
    - kwargs: {
        osd_dev: /dev/vdc
        }

# Activate OSD's on prepared disks

activate_vdb:
  module.run:
    - name: sesceph.osd_activate
    - kwargs: {
        osd_dev: /dev/vdb
        }


activate_vdc:
  module.run:
    - name: sesceph.osd_activate
    - kwargs: {
        osd_dev: /dev/vdc
        }

# Prepare for the rgw

rgw_prep:
  module.run:
    - name: sesceph.rgw_pools_create

# Create the rgw

rgw_create:
  module.run:
    - name: sesceph.rgw_create
    - kwargs: {
        name: rgw-{{ grains['machine_id'] }}
        }

# Create the mds

mds_create:
  module.run:
    - name: sesceph.mds_create
    - kwargs: {
        name: mds-{{ grains['machine_id'] }},
        port: 1000,
        addr:{{ grains['fqdn_ip4'] }}
        }
