import logging
from odoo import http, tools

_logger = logging.getLogger(__name__)


old_session_gc = http.session_gc


def session_gc(session_store):
    """
    Allow to disable sessions garbage collector
    """
    if tools.config.get('disable_session_gc'):
        return _logger.debug("Global cleaning of sessions disabled")
    return old_session_gc


# #Monkey patch of standard methods
_logger.debug("Monkey patching sessions")
http.session_gc = session_gc
