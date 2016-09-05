keyring_admin_save:
  module.run:
    - name: ceph.keyring_save
    - kwargs: {
        'keyring_type' : 'admin',
        'secret' : {{ salt['pillar.get']('admin.secret', 'AQBR8KhWgKw6FhAA__DEFAULT_KEY__PKzIo6def') }}
        }
    - require:
      - sls: ses.ceph
