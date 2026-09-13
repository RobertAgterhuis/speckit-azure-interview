# Azure Architecture Interview

## Document Control

| Field | Value |
|---|---|
| Schema version | 1.0 |
| Interview status | Draft |
| Ready for specification | No |
| Created | |
| Last updated | |
| Interviewed by | |
| Confirmed by | |

## 1. Workload Overview

- **Workload name:**
- **Business purpose:**
- **Business owner:**
- **Technical owner:**
- **Deployment lifecycle:** Greenfield / Brownfield / Migration / Extension
- **Infrastructure-as-Code language:** Bicep / Terraform
- **AVM strategy:** AVM only / AVM preferred / Other
- **Target environments:**
- **Production criticality:**
- **Requested delivery date:**

## 2. Scope

### In Scope

- TBD

### Out of Scope

- TBD

### Success Criteria

- TBD

## 3. Azure Estate

- **Tenant:**
- **Management group:**
- **Subscription per environment:**
- **Resource group strategy:**
- **Primary Azure region:**
- **Secondary Azure region:**
- **Data residency requirements:**
- **Existing landing zone:** Yes / No / Unknown

## 4. Network Architecture

- **Topology:** Standalone / Existing hub-spoke / New hub-spoke / Virtual WAN / Other
- **Hub name:**
- **Hub resource ID:**
- **Hub owner:**
- **Spoke name:**
- **Spoke resource ID:**
- **Address spaces:**
- **Subnet requirements:**
- **Peering ownership:**
- **Internet ingress path:**
- **Internet egress path:**
- **Azure Firewall usage:**
- **Route table requirements:**
- **On-premises connectivity:** None / VPN / ExpressRoute / Both
- **Overlapping address-space validation completed:** Yes / No

## 5. Private Connectivity and DNS

- **Private endpoints required:** Yes / No
- **Public network access permitted:** Yes / No / Conditional
- **Private endpoint subnet:**
- **Private DNS ownership:** Hub / Spoke / Central platform / Other
- **Private DNS subscription:**
- **Existing Private DNS zones:**
- **VNet-link ownership:**
- **Azure Private DNS Resolver present:** Yes / No
- **On-premises DNS integration:**
- **DNS changes permitted by this deployment:**

## 6. Existing Resources

| Resource type | Resource name or ID | Intent | Owner | Modifiable | Required integration |
|---|---|---|---|---:|---|
| TBD | TBD | Discover / Reuse / Create / Migrate / Replace | TBD | No | TBD |

## 7. Identity and Access

- **Deployment identity:**
- **Authentication model:**
- **Managed identities required:**
- **RBAC model:**
- **Privileged roles required:**
- **Role-assignment ownership:**
- **Microsoft Entra groups:**
- **Administrative Unit requirements:**
- **Cross-tenant access requirements:**

## 8. Security and Compliance

- **Applicable compliance frameworks:**
- **Azure Policy assignments:**
- **Security baseline:**
- **Encryption requirements:**
- **Customer-managed keys required:** Yes / No
- **Key Vault strategy:** Existing / New / Not required
- **Key Vault resource ID:**
- **Secret-management requirements:**
- **Resource locks required:**
- **Defender for Cloud requirements:**
- **Permitted public exposure:**

## 9. Governance

- **Naming convention:**
- **Required tags:**
- **Tag values per environment:**
- **Cost center:**
- **Resource ownership model:**
- **FinOps requirements:**
- **Allowed SKUs:**
- **Denied SKUs or resource types:**
- **Exception process:**

## 10. Reliability and Operations

- **Availability target:**
- **High availability required:** Yes / No
- **Disaster recovery required:** Yes / No
- **Recovery Time Objective:**
- **Recovery Point Objective:**
- **Backup requirements:**
- **Maintenance requirements:**
- **Patch-management requirements:**
- **Operational support team:**

## 11. Monitoring and Observability

- **Log Analytics strategy:** Existing / New / Central
- **Log Analytics workspace resource ID:**
- **Diagnostic settings required:**
- **Metrics required:**
- **Alert rules required:**
- **Action group resource ID:**
- **Retention requirements:**
- **Integration with external monitoring:**

## 12. Deployment and Delivery

- **CI/CD platform:**
- **Repository:**
- **Deployment scope:**
- **Service connection or federated identity:**
- **Environment approval requirements:**
- **Validation requirements:**
- **What-If required:** Yes / No
- **Deployment mode:**
- **Rollback strategy:**
- **Parameter-management strategy:**
- **Secret injection strategy:**

## 13. Testing and Acceptance

- **Static-analysis tools:**
- **Policy-validation tools:**
- **Security scanning tools:**
- **Deployment-test environment:**
- **Integration tests:**
- **Acceptance owner:**
- **Evidence required:**

## 14. Prohibited Changes

- TBD

## 15. Dependencies

| ID | Dependency | Owner | Status | Blocking |
|---|---|---|---|---:|
| DEP-001 | TBD | TBD | Open | Yes |

## 16. Decisions

| ID | Decision | Rationale | Source | Status |
|---|---|---|---|---|
| DEC-001 | TBD | TBD | User / Repository / Azure / Documentation | Proposed |

## 17. Assumptions

| ID | Assumption | Validation required | Owner | Status |
|---|---|---:|---|---|
| ASM-001 | TBD | Yes | TBD | Unvalidated |

## 18. Open Questions

| ID | Question | Owner | Blocking | Status |
|---|---|---|---:|---|
| OQ-001 | TBD | TBD | Yes | Open |

## 19. Readiness Assessment

- **Blocking questions remaining:**
- **Unvalidated critical assumptions:**
- **Missing resource identifiers:**
- **Conflicting requirements:**
- **Ready for `/speckit.specify`:** No
- **Readiness rationale:**

## 20. Specification Handoff

Use this interview as authoritative discovery input for `/speckit.specify`.

The specification must:

1. Preserve all confirmed requirements and constraints.
2. Distinguish existing resources from resources to be created.
3. Preserve all prohibited changes.
4. Never convert an assumption into a confirmed fact.
5. Retain unresolved non-blocking questions explicitly.
6. Refuse specification handoff while blocking questions remain.
7. Describe what and why without prematurely prescribing implementation details.