# Remove the ceph cluster from node
run_purge:
  module.run:
    - name: ceph.purge

# Wipe data on drives

zap_vdb:
   module.run:
    - name: ceph.zap
    - dev: /dev/vdb


zap_vdc:
   module.run:
    - name: ceph.zap
    - dev: /dev/vdc

