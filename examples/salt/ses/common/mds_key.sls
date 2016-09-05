keyring_mds_save:
  module.run:
    - name: ceph.keyring_save
    - kwargs: {
        'keyring_type' : 'mds',
        'secret' : {{ salt['pillar.get']('mds.secret', 'AQBR8KhWgKw6FhAA__DEFAULT_KEY__PKzIo6def') }}
        }
    - require:
      - sls: ses.ceph
