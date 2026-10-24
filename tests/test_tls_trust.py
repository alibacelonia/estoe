"""Check SDK default trust stores offline; never construct authenticated clients."""

import hashlib
import ssl
from pathlib import Path

import botocore.httpsession
import certifi
import pytest

# Public certificate SHA-256 fingerprints, not secret material:
# https://emudhra.we-have-a-problem.com/roots.json (2026-10-24)
INCIDENT_ROOTS = {
    "7dd78d5f4f13459a83dff9abbba62edbaf6f2d102bf257fd712f4d9f2746ed8d",
    "f2edaaff3d9b701fb4d14c9f285f8c0bad90fc3bcc1fa07d47f4718edaba34a5",
    "d7a7a0fb5d7e2731d771e9484ebcdef71d5f0c3e0a2948782bc83ee0ea699ef4",
    "86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b",
}


@pytest.mark.parametrize(
    "bundle", [certifi.where, lambda: botocore.httpsession.get_cert_path(True)]
)
def test_default_sdk_ca_bundle_excludes_incident_roots(bundle):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=bundle())
    fingerprints = {
        hashlib.sha256(certificate).hexdigest()
        for certificate in context.get_ca_certs(binary_form=True)
    }
    assert fingerprints, "CA bundle must contain trust anchors"
    assert fingerprints.isdisjoint(INCIDENT_ROOTS)


def test_aws_uses_updated_certifi_instead_of_its_fallback_bundle():
    assert Path(botocore.httpsession.get_cert_path(True)).samefile(certifi.where())
