import logging

log = logging.getLogger(__name__)

__virtualname__ = 'sesceph'

__outputter__ = {
                'is_ok': 'is_ok'
                }

def is_ok():
    '''
    A function to make some spam with eggs!

    CLI Example::

        salt '*' test.spam eggs
    '''
    log.error('wibble')
    return {'a' :'hkjhjk'}


def __virtual__():
    return __virtualname__
