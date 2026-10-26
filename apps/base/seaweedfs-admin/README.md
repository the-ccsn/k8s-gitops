# SeaweedFS Admin

`https://swfs-admin.ccsn.dev` uses the production Gateway and the shared
`oauth2-gateway.ccsn.dev` login session. The Gateway verifies the returned Logto
JWT and requires the non-default `swfs:admin` role. Assign this role explicitly
to storage administrators. Browser-origin checks protect write operations.

The existing `seaweedfs-admin` Role resource is renamed in place through its
provider `name` field, preserving its Logto ID and user assignments. Sign in
again through the shared gateway after the role name changes to refresh claims.

The single Admin container connects to the OMV master and discovers its filers
and volume servers. It retains the existing 1Gi PVC and Deployment selector.
Strict ambient mTLS, a Gateway-only identity policy and ingress filtering protect
its HTTP listener. The worker gRPC port has no permitted ingress. S3 remains a
separate service; automatic maintenance stays disabled.

This component uses no dedicated OAuth client, login proxy or cookie Secret.
Previously deployed dedicated identity/session resources become unused and are
not deleted by this adoption. The existing S3 gateways still read their static
credential file; IAM changes made in Admin do not update that file.
