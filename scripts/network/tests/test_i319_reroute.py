from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / "infra/configs/base/i319-reroute/service.yaml"
README = ROOT / "infra/configs/base/i319-reroute/README.md"
GATEWAY_README = ROOT / "README.gateway.md"


class I319RerouteTest(unittest.TestCase):
    def test_service_requires_ipv6_and_ipv4(self) -> None:
        service = yaml.safe_load(SERVICE.read_text())

        self.assertEqual(service["spec"]["ipFamilyPolicy"], "RequireDualStack")
        self.assertEqual(service["spec"]["ipFamilies"], ["IPv6", "IPv4"])

    def test_firewall_ports_cover_http_https_and_quic(self) -> None:
        service = yaml.safe_load(SERVICE.read_text())
        ports = {
            (port["port"], port["protocol"])
            for port in service["spec"]["ports"]
        }

        self.assertEqual(ports, {(80, "TCP"), (443, "TCP"), (443, "UDP")})

    def test_repository_docs_describe_nat_and_direct_ipv6(self) -> None:
        docs = README.read_text() + GATEWAY_README.read_text()

        self.assertIn("319 NAT router", docs)
        self.assertIn("DNAT", docs)
        self.assertIn("IPv6", docs)
        self.assertIn("443/UDP", docs)
        self.assertIn("blocks unsolicited", docs)
        self.assertIn("both address families", docs)


if __name__ == "__main__":
    unittest.main()
