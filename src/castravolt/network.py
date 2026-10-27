"""Use native certificate-chain validation without weakening HTTPS verification."""
from functools import lru_cache
import ssl
import truststore


@lru_cache
def tls_context():
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
