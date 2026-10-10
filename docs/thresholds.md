# PM2.5 status policy

The dashboard's GREEN, YELLOW, and RED labels are a configurable school
decision-support policy for hourly PM2.5 forecasts. They are **not official
CPCB AQI categories**, not a medical assessment, and not a guarantee of safety.
The default values preserve the prototype:

| Policy | GREEN | YELLOW | RED |
|---|---:|---:|---:|
| Regular | ≤60 µg/m³ | >60 to ≤120 µg/m³ | >120 µg/m³ |
| Sensitive | ≤40 µg/m³ | >40 to ≤90 µg/m³ | >90 µg/m³ |

The thresholds are project placeholders. They can be set through the
`PM25_GREEN_MAX`, `PM25_YELLOW_MAX`, `PM25_SENSITIVE_GREEN_MAX`, and
`PM25_SENSITIVE_YELLOW_MAX` backend environment variables. `ACTIVITY_FACTOR`
remains undefined and unused until its purpose and value are clarified.

CPCB's national AQI framework has six categories and uses pollutant-specific
concentrations averaged over short-term periods up to 24 hours. It therefore
cannot be represented accurately by treating this simplified, hourly school
policy as official AQI. See the [CPCB National AQI report](https://cpcb.nic.in/displaypdf.php?id=bWFudWFsLW1vbml0b3JpbmcvQVFJX05BTVBfUmVwX1NlcHRlbWJlciUyMDE2LnBkZg==).

The API includes the policy classification and existing project advice for
decision support. The advice is informational only, not medical advice.
