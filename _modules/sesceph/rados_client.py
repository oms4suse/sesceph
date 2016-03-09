import os
import logging


import utils
import constants
import keyring
import model
import mdl_updater
import service

log = logging.getLogger(__name__)

class Error(Exception):
    """
    Error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])


class ctrl_rados_client(object):
    """
    Super class.
    """
    def __init__(self, **kwargs):
        # what we are starting
        self.ceph_client_id = kwargs.get("name")
        self.service_name = None
        self.model = model.model(**kwargs)
        self.model.init = "systemd"


    def update(self):
        self.updater = mdl_updater.model_updater(self.model)
        self.updater.hostname_refresh()
        try:
            self.updater.defaults_refresh()
        except utils.Error, e:
            log.error(e)
        if self.model.cluster_name == None:
            log.error("Cluster name not found")
        log.debug("Cluster name %s" % (self.model.cluster_name))
        try:
            self.updater.load_confg(self.model.cluster_name)
        except mdl_updater.Error, e:
            log.error(e)
        try:
            self.updater.mon_members_refresh()
        except mdl_updater.Error, e:
            log.error(e)
        self.init_system = service.init_system(init_type=self.model.init)


    def activate(self):
        if self.ceph_client_id == None:
            raise Error("self.ceph_client_id not specified")
        if self.service_name == None:
            raise Error("self.service_name not specified")
        arguments = {
            'identifier' : self.ceph_client_id,
            'service' : self.service_name,
        }
        isrunning = self.init_system.is_running(**arguments)
        if not isrunning:
            self.init_system.start(**arguments)
        self.init_system.on_boot_enable(**arguments)



    def deactivate(self):
        if self.ceph_client_id == None:
            raise Error("self.ceph_client_id not specified")
        if self.service_name == None:
            raise Error("self.service_name not specified")
        arguments = {
            'identifier' : self.ceph_client_id,
            'service' : self.service_name,
        }
        isrunning = self.init_system.is_running(**arguments)
        if isrunning:
            self.init_system.stop(**arguments)
        self.init_system.on_boot_disable(**arguments)


    def create(self):
        self.prepare()
        self.activate()


    def destroy(self):
        self.deactivate()
        self.remove()
