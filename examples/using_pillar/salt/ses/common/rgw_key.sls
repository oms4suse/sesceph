keyring_rgw_save:
  module.run:
    - name: ceph.keyring_save
    - kwargs: {
        'keyring_type' : 'rgw',
        'secret' : {{ salt['pillar.get']('rgw.secret', 'AQBR8KhWgKw6FhAA__DEFAULT_KEY__PKzIo6def') }}
        }
    - require:
      - sls: ses.ceph
