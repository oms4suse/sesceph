# Remove the ceph cluster from node
run_purge:
  module.run:
    - name: sesceph.purge

# Wipe data on drives

zap_vdb:
   module.run:
    - name: sesceph.zap
    - dev: /dev/vdb


zap_vdc:
   module.run:
    - name: sesceph.zap
    - dev: /dev/vdc

