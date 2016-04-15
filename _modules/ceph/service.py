import logging


import utils
import constants


log = logging.getLogger(__name__)


init_types_available = set([ "systemd" , "sysV"])


def Property(func):
    return property(**func())

class init_exception(Exception):
    """Base class for exceptions in this module."""
    pass

class init_exception_init_type(init_exception):
    """Exception raised for errors in the init_type
    Attributes:
        msg  -- explanation of the error
    """
    def __init__(self, msg):
        self.msg = msg

class init_exception_service(init_exception):
    """Exception raised for errors in the init implementation
    Attributes:
        msg  -- explanation of the error
    """
    def __init__(self, msg):
        self.msg = msg


class init_system(object):
    def __init__(self, **kwargs):
        self.log = logging.getLogger("init_system_facade")
        init_type = kwargs.get('init_type', None)
        if init_type != None:
            self.init_type = init_type

    @Property
    def init_type():
        doc = "Ouput init_type"
        def fget(self):
            if hasattr(self, '_init_type_name'):
                return self._init_type_name
            else:
                return None
        def fset(self, name):
            if not name in init_types_available:
                del(self._init_type_implementation)
                del(self._init_type_name)
                raise init_exception_init_type("Invalid Value:%s" % (name))
            self._init_type_name = name
            init_implementation = {'systemd' : init_system_systemd,
                'message' : init_system_sysV,
            }
            new_implementation = init_implementation[name]()
            self._init_type_implementation = new_implementation
            return self._init_type_name
        def fdel(self):
            del (self._init_type_implementation)
            del (self._init_type_name)
        return locals()


    def _check_properties(self):
        if not hasattr(self, '_init_type_implementation'):
            raise init_exception_init_type("Property 'init_type' has invalid value.")


    def is_running(self, **kwargs):
        """Get the service is_running
        return:
        True for running
        False for not running
        """
        self._check_properties()
        return self._init_type_implementation.is_running(**kwargs)

    def start(self, **kwargs):
        """Start service
        throws exception on failure:
        """
        self._check_properties()
        return self._init_type_implementation.start(**kwargs)

    def stop(self, **kwargs):
        self._check_properties()
        return self._init_type_implementation.stop(**kwargs)

    def restart(self, **kwargs):
        self._check_properties()
        return self._init_type_implementation.restart(**kwargs)

    def on_boot_enable(self, **kwargs):
        self._check_properties()
        return self._init_type_implementation.on_boot_enable(**kwargs)

    def on_boot_disable(self, **kwargs):
        self._check_properties()
        return self._init_type_implementation.on_boot_disable(**kwargs)

class init_system_systemd():

    def _get_systemctl_name(self, **kwargs):
        service = kwargs.get("service")
        if service == None:
            raise
        identifier = kwargs.get("identifier")
        if identifier != None:
            return str(service + "@" + identifier)
        return service_name


    def is_running(self, **kwargs):

        systemctl_name = self._get_systemctl_name(**kwargs)
        arguments = [
                constants._path_systemctl,
                'show',
                '--property',
                'ActiveState',
                systemctl_name,
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise init_exception_service("failed to query state from '%s' Error rc=%s, stdout=%s stderr=%s" % (
                    systemctl_name,
                    output["retcode"],
                    output["stdout"],
                    output["stderr"])
                    )
        running = None
        for item in output["stdout"].split('\n'):
            split_item = item.split('=')
            key = split_item[0]
            value = "=".join(split_item[1:])
            if key == "ActiveState":
                if value == "active":
                    running = True
                else:
                    running = False
        if running == None:
            raise init_exception_service("failed to get ActiveState from '%s'" % (
                    systemctl_name))
        return running

    def start(self, **kwargs):
        systemctl_name = self._get_systemctl_name(**kwargs)
        arguments = [
                constants._path_systemctl,
                'start',
                systemctl_name
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise init_exception_service("failed to start '%s' Error rc=%s, stdout=%s stderr=%s" % (
                    systemctl_name,
                    output["retcode"],
                    output["stdout"],
                    output["stderr"])
                    )
        return True

    def stop(self, **kwargs):
        systemctl_name = self._get_systemctl_name(**kwargs)
        arguments = [
                constants._path_systemctl,
                'stop',
                systemctl_name
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise init_exception_service("failed to stop '%s' Error rc=%s, stdout=%s stderr=%s" % (
                    systemctl_name,
                    output["retcode"],
                    output["stdout"],
                    output["stderr"])
                    )
        return True

    def restart(self, **kwargs):
        systemctl_name = self._get_systemctl_name(**kwargs)
        arguments = [
                constants._path_systemctl,
                'restart',
                systemctl_name
            ]
        output = utils.execute_local_command(arguments)
        if output["retcode"] != 0:
            raise init_exception_service("failed to restart '%s' Error rc=%s, stdout=%s stderr=%s" % (
                    systemctl_name,
                    output["retcode"],
                    output["stdout"],
                    output["stderr"])
                    )
        return True


    def on_boot_enable(self, **kwargs):

        systemctl_name = self._get_systemctl_name(**kwargs)
        arguments = [
                constants._path_systemctl,
                'enable',
                systemctl_name
            ]
        utils.execute_local_command(arguments)

    def on_boot_disable(self, **kwargs):
        systemctl_name = self._get_systemctl_name(**kwargs)
        arguments = [
                constants._path_systemctl,
                'disable',
                systemctl_name
            ]
        utils.execute_local_command(arguments)

class init_system_sysV():
    # TODO: this is largely untested



    def _get_sysvinit_name(self, **kwargs):
        service = kwargs.get("service")
        if service == None:
            raise init_exception("service is None")
        return service


    def start(self, **kwargs):
        service_name = self._get_sysvinit_name(**kwargs)
        arguments = [
                'service',
                service_name,
                'start'
            ]
        utils.execute_local_command(arguments)


    def stop(self, **kwargs):
        service_name = self._get_sysvinit_name(**kwargs)
        arguments = [
                'service',
                service_name,
                'stop'
            ]
        utils.execute_local_command(arguments)


    def restart(self, **kwargs):
        service_name = self._get_sysvinit_name(**kwargs)
        arguments = [
                'service',
                service_name,
                'restart'
            ]
        utils.execute_local_command(arguments)


    def on_boot_enable(self, **kwargs):
        service_name = self._get_sysvinit_name(**kwargs)
        arguments = [
                    'chkconfig',
                    service_name,
                    'on'
            ]
        utils.execute_local_command(arguments)


    def on_boot_disable(self, **kwargs):
        service_name = self._get_sysvinit_name(**kwargs)
        arguments = [
                    'chkconfig',
                    service_name,
                    'off'
            ]
        utils.execute_local_command(arguments)

    def is_running(self, **kwargs):
        service_name = self._get_sysvinit_name(**kwargs)
        arguments = [
                    'chkconfig',
                    service_name,
                    'status'
            ]
        utils.execute_local_command(arguments)
