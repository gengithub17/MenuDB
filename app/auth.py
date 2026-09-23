"""Optional JWT verification, layered on top of the X-Auth-Request-Email
header oauth2-proxy sets.

Why this exists: the app has always trusted X-Auth-Request-Email with no
verification of its own, relying entirely on the network being locked down
so nothing but oauth2-proxy can reach the app. That assumption briefly broke
(Docker-published ports bypassing ufw let anyone on the LAN forge the header
and impersonate any user) before being fixed at the network layer. This
module adds a second, independent layer that doesn't rely on network
topology at all: it verifies the ID token's signature against Keycloak's
public keys, so identity can't be forged just by setting a header.

Disabled by default (JWT_AUTH_ENABLED=false) so it can be rolled out once
oauth2-proxy is configured to forward the token (pass_authorization_header),
without breaking logins in the meantime. When enabled, verification is
mandatory: a request with no token, an invalid token, or a token that fails
any check is treated as logged out. It does not fall back to trusting the
plain header - that would defeat the point of turning this on.
"""
import jwt
from flask import current_app, request

_jwks_clients = {}


def _get_jwks_client():
    """One PyJWKClient per JWKS URL, reused across requests so its internal
    signing-key cache (default ~5 min) actually gets hit instead of fetching
    Keycloak's JWKS on every request."""
    jwks_url = current_app.config.get('JWT_JWKS_URL')
    if not jwks_url:
        return None
    client = _jwks_clients.get(jwks_url)
    if client is None:
        client = jwt.PyJWKClient(jwks_url)
        _jwks_clients[jwks_url] = client
    return client


def verify_jwt_email():
    """Return the verified email claim from the request's bearer token, or
    None if it's missing, malformed, or fails any check. Never raises."""
    issuer = current_app.config.get('JWT_ISSUER')
    audience = current_app.config.get('JWT_AUDIENCE')
    jwks_client = _get_jwks_client()
    if not issuer or not audience or jwks_client is None:
        current_app.logger.error(
            'JWT_AUTH_ENABLED is true but JWT_ISSUER/JWT_AUDIENCE/JWT_JWKS_URL '
            'is not fully configured; treating all requests as logged out.'
        )
        return None

    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[len('Bearer '):].strip()
    if not token:
        return None

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=['RS256'],
            issuer=issuer,
            audience=audience,
            leeway=current_app.config.get('JWT_LEEWAY_SECONDS', 0),
            options={'require': ['exp', 'iss', 'aud']},
        )
    except jwt.PyJWTError as e:
        current_app.logger.info('JWT verification failed: %s', e)
        return None

    email = claims.get('email')
    if not email:
        current_app.logger.info('JWT verified but has no email claim')
        return None
    return email
