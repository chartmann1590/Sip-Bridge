import socket
import logging

logger = logging.getLogger(__name__)

def apply():
    """
    Monkey-patch socket.getaddrinfo to force IPv4 (AF_INET).
    This helps avoid IPv6 timeouts in Docker/Eventlet environments.
    """
    logger.info("Applying IPv4-only patch to socket.getaddrinfo")
    
    # Capture the current getaddrinfo (which might already be eventlet-patched)
    _original_getaddrinfo = socket.getaddrinfo
    
    def ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        # Force family to AF_INET (IPv4)
        # This prevents the resolver from trying IPv6 (AAAA) lookups which can hang
        return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    
    socket.getaddrinfo = ipv4_only_getaddrinfo
