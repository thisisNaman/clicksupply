# ClickSupply: Security & DPDPA Compliance

As a platform operating in India, ClickSupply must adhere strictly to the Digital Personal Data Protection Act (DPDPA) of 2023.

## 1. Compliance Architecture
*   **Data Mapping & Inventory:** The system must maintain an automated map of all personal data flows (what is collected, why, where it is stored).
*   **Verifiable Consent Management:** Implement granular consent tracking for any user data collected, ensuring direct communication links for users to withdraw consent or exercise Data Principal rights (access, correction, erasure).

## 2. Significant Data Fiduciary (SDF) Readiness
If ClickSupply processes high volumes of data, it may be classed as an SDF, requiring:
*   Appointment of a Data Protection Officer (DPO) based in India.
*   Engagement of an independent data auditor.
*   Algorithmic due diligence to ensure AI tracking systems do not cause unfair outcomes.
*   **Data Localization:** Ensuring sensitive customer and brand data is kept within Indian jurisdictions (e.g., using AWS/GCP regions in Mumbai/Hyderabad).

## 3. Infrastructure Security
*   Implement encryption at rest and in transit.
*   Maintain mandatory audit logs and retain personal data/system logs for a minimum of one year to support potential breach investigations.
*   Establish automated alerting to notify the Data Protection Board of India and affected users within 72 hours in the event of a breach.