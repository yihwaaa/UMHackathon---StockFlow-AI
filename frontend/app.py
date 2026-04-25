import json
import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("STOCKFLOW_API_URL", "http://127.0.0.1:8000")


st.set_page_config(
    page_title="StockFlow AI",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp {
        background: radial-gradient(circle at top right, #e8ecff 0%, #f8faff 38%, #f5f7fb 100%);
      }
      .block-container {
        padding-top: 1.1rem;
        padding-bottom: 2rem;
        max-width: 1200px;
      }
      .hero {
        background: linear-gradient(135deg, #0f172a, #1e3a8a);
        color: #f8fafc;
        padding: 1.1rem 1.3rem;
        border-radius: 14px;
        box-shadow: 0 8px 30px rgba(15, 23, 42, 0.22);
        margin-bottom: 1rem;
      }
      .hero h2 { margin: 0; font-size: 1.35rem; }
      .hero p { margin: .35rem 0 0 0; opacity: .92; font-size: .94rem; }
      .glass {
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 14px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
        padding: .85rem 1rem;
      }
      .mini-kpi {
        border-radius: 12px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.07);
        padding: .7rem .85rem;
      }
      .mini-kpi-label {
        color: #475569;
        font-size: .8rem;
        margin-bottom: .15rem;
      }
      .mini-kpi-value {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0f172a;
      }
      .stButton>button {
        border-radius: 10px;
        border: 1px solid #cbd5e1;
        font-weight: 600;
      }
      .stTextInput>div>div>input,
      .stTextArea textarea,
      .stNumberInput input {
        border-radius: 10px !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def _api_request(method: str, path: str, payload: dict | None = None, timeout: int = 20):
    try:
        response = requests.request(method, f"{API_URL}{path}", json=payload, timeout=timeout)
    except requests.RequestException as exc:
        return None, None, f"Cannot connect to API: {exc}"

    try:
        data = response.json()
    except ValueError:
        data = None

    if response.status_code >= 400:
        if isinstance(data, dict):
            detail = data.get("detail")
            if isinstance(detail, dict):
                return response.status_code, data, detail.get("message", "Request failed.")
            if isinstance(detail, str):
                return response.status_code, data, detail
        return response.status_code, data, f"Request failed ({response.status_code})."

    return response.status_code, data, None


def _health():
    status, data, _ = _api_request("GET", "/api/v1/health", timeout=5)
    if status != 200 or not isinstance(data, dict):
        return False, {}
    return True, data


def _missing_fields(value: str | None) -> list[str]:
    if not value:
        return []
    return [field.strip() for field in value.split(",") if field.strip()]


def _extract_case_notes(raw_details: str | None) -> str | None:
    if not raw_details:
        return None

    text = str(raw_details).strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and isinstance(parsed.get("notes"), str) and parsed["notes"].strip():
            return parsed["notes"].strip()
    except (ValueError, TypeError):
        pass

    return text


def _fmt_time(raw: str) -> str:
    try:
        return datetime.fromisoformat(raw).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw


def _render_hero(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="hero">
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_kpi(label: str, value: str | int):
    st.markdown(
        f"""
        <div class="mini-kpi">
          <div class="mini-kpi-label">{label}</div>
          <div class="mini-kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _show_case_result(data: dict):
    ai = data.get("ai_analysis", {})
    entities = ai.get("entities", {})
    workflow = ai.get("workflow", {})
    missing = workflow.get("missing_fields", []) or []

    st.success(f"Case #{data.get('case_id')} created successfully.")
    c1, c2, c3 = st.columns(3)
    with c1:
        _render_kpi("Issue Type", ai.get("issue_type", "UNKNOWN"))
    with c2:
        _render_kpi("Priority", ai.get("urgency", "LOW"))
    with c3:
        _render_kpi("Next Action", workflow.get("next_action", "Operations Review"))

    summary = pd.DataFrame(
        [
            ("Supplier", entities.get("supplier")),
            ("Invoice No", entities.get("invoice_no")),
            ("Product", entities.get("product")),
            ("Expected Qty", entities.get("expected_qty")),
            ("Actual Qty", entities.get("actual_qty")),
        ],
        columns=["Field", "Value"],
    )
    st.table(summary)

    if missing:
        st.warning(f"Missing fields: {', '.join(missing)}. Complete them in **Manage Cases**.")
    else:
        st.info("All required fields are complete and routable.")


def _render_new_case_page(backend_online: bool):
    _render_hero(
        "Create New Case",
        "Premium intake experience: fast input, cleaner results, and immediate workflow recommendation.",
    )

    st.markdown(
        """
        <div class="glass">
          <b>Recommended:</b> Use <i>Smart Text</i> when receiving unstructured notes/OCR/chat.  
          Use <i>Structured Form</i> when your team already has clear invoice values.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    tab_text, tab_form = st.tabs(["Smart Text Intake", "Structured Form Intake"])

    with tab_text:
        left, right = st.columns([1.5, 1])
        with left:
            raw_input = st.text_area(
                "Describe discrepancy",
                height=230,
                placeholder=(
                    "Supplier ABC, invoice INV-001, product canned tuna, expected 20 cartons, "
                    "received 15 cartons, short by 5."
                ),
            )
            force_create_text = st.checkbox(
                "Create anyway if duplicate case is detected",
                key="force_create_text",
            )
            submit_text = st.button("Create Case from Smart Text", type="primary", key="submit_text")

        with right:
            st.markdown(
                """
                **Tips for best extraction**
                1. Include supplier and invoice number.
                2. Include product name.
                3. Include expected and actual quantities.
                4. Mention duplicate concern if relevant.
                """
            )

        if submit_text:
            if not backend_online:
                st.error("API is offline.")
                return
            if not raw_input.strip():
                st.warning("Please enter discrepancy details.")
                return

            payload = {"raw_input": raw_input.strip(), "force_create": force_create_text}
            status, data, message = _api_request("POST", "/api/v1/analyze", payload, timeout=45)
            if status == 200 and isinstance(data, dict):
                _show_case_result(data)
            elif status == 409 and isinstance(data, dict):
                existing = (data.get("detail") or {}).get("existing_case_id")
                st.error(f"{message} Existing open case: #{existing}")
            else:
                st.error(message or "Unable to create case.")

    with tab_form:
        col1, col2 = st.columns(2)
        with col1:
            supplier = st.text_input("Supplier")
            product = st.text_input("Product")
            expected_qty = st.number_input("Expected Qty", min_value=0.0, value=0.0, step=1.0)
        with col2:
            invoice_no = st.text_input("Invoice Number")
            actual_qty = st.number_input("Actual Qty", min_value=0.0, value=0.0, step=1.0)
            store = st.text_input("Store / Branch (optional)")
        notes = st.text_area("Notes (optional)", height=100)
        force_create_form = st.checkbox(
            "Create anyway if duplicate case is detected",
            key="force_create_form",
        )

        if st.button("Create Case from Structured Form", type="primary", key="submit_form"):
            if not backend_online:
                st.error("API is offline.")
                return
            if not supplier.strip() or not invoice_no.strip() or not product.strip():
                st.warning("Please complete Supplier, Invoice Number, and Product.")
                return

            payload = {
                "supplier": supplier.strip(),
                "invoice_no": invoice_no.strip(),
                "store": store.strip() or None,
                "line_items": [
                    {
                        "product": product.strip(),
                        "sku": None,
                        "expected_qty": float(expected_qty),
                        "actual_qty": float(actual_qty),
                    }
                ],
                "notes": notes.strip() or None,
                "force_create": force_create_form,
            }
            status, data, message = _api_request("POST", "/api/v1/cases/manual", payload, timeout=30)
            if status == 200 and isinstance(data, dict):
                _show_case_result(data)
            elif status == 409 and isinstance(data, dict):
                existing = (data.get("detail") or {}).get("existing_case_id")
                st.error(f"{message} Existing open case: #{existing}")
            else:
                st.error(message or "Unable to create case.")


def _render_case_actions(selected_case: dict):
    case_id = int(selected_case["id"])
    missing = _missing_fields(selected_case.get("missing_fields"))

    st.markdown("### Case Details")
    c1, c2, c3 = st.columns(3)
    with c1:
        _render_kpi("Status", selected_case.get("status", "-"))
    with c2:
        _render_kpi("Issue Type", selected_case.get("issue_type", "-"))
    with c3:
        _render_kpi("Priority", selected_case.get("urgency", "-"))
    st.caption(f"Next action: {selected_case.get('next_action') or 'Operations Review'}")

    st.markdown(
        f"""
        <div class="glass">
          <b>Supplier:</b> {selected_case.get('supplier') or '-'}<br/>
          <b>Invoice No:</b> {selected_case.get('invoice_no') or '-'}<br/>
          <b>Product:</b> {selected_case.get('product') or '-'}<br/>
          <b>Expected Qty:</b> {selected_case.get('expected_qty') if selected_case.get('expected_qty') is not None else '-'}<br/>
          <b>Actual Qty:</b> {selected_case.get('actual_qty') if selected_case.get('actual_qty') is not None else '-'}
        </div>
        """,
        unsafe_allow_html=True,
    )

    notes = _extract_case_notes(selected_case.get("discrepancy_details"))
    if notes:
        with st.expander("Notes"):
            st.write(notes)

    st.markdown("### Update Status")
    target_status = st.selectbox(
        "Set status",
        ["NEW", "PENDING_INFO", "ROUTED", "RESOLVED"],
        key=f"status_{case_id}",
    )
    if st.button("Save Status", key=f"save_status_{case_id}"):
        status, _, message = _api_request(
            "PATCH",
            f"/api/v1/cases/{case_id}/status",
            {"status": target_status},
            timeout=10,
        )
        if status == 200:
            st.success("Status updated.")
            st.rerun()
        else:
            st.error(message or "Unable to update status.")

    st.markdown("### Clarify / Fix Case Data")
    if missing:
        st.warning(f"Required now: {', '.join(missing)}")
    else:
        st.info("No required fields missing. You can still update fields if needed.")

    with st.form(f"clarify_{case_id}"):
        col_l, col_r = st.columns(2)
        with col_l:
            supplier = st.text_input("Supplier", value=selected_case.get("supplier") or "")
            invoice_no = st.text_input("Invoice Number", value=selected_case.get("invoice_no") or "")
            product = st.text_input("Product", value=selected_case.get("product") or "")
        with col_r:
            expected_qty = st.text_input(
                "Expected Qty",
                value="" if selected_case.get("expected_qty") is None else str(selected_case.get("expected_qty")),
            )
            actual_qty = st.text_input(
                "Actual Qty",
                value="" if selected_case.get("actual_qty") is None else str(selected_case.get("actual_qty")),
            )
            notes_input = st.text_area("Notes", value=notes or "", height=80)

        submitted = st.form_submit_button("Submit Clarification")

    if submitted:
        payload: dict[str, str | float] = {}
        if supplier.strip():
            payload["supplier"] = supplier.strip()
        if invoice_no.strip():
            payload["invoice_no"] = invoice_no.strip()
        if product.strip():
            payload["product"] = product.strip()
        if notes_input.strip():
            payload["notes"] = notes_input.strip()

        if expected_qty.strip():
            try:
                payload["expected_qty"] = float(expected_qty.strip())
            except ValueError:
                st.error("Expected Qty must be a valid number.")
                payload = {}
        if actual_qty.strip():
            try:
                payload["actual_qty"] = float(actual_qty.strip())
            except ValueError:
                st.error("Actual Qty must be a valid number.")
                payload = {}

        if not payload:
            st.warning("No valid fields to update.")
        else:
            status, data, message = _api_request(
                "PATCH",
                f"/api/v1/cases/{case_id}/clarify",
                payload,
                timeout=12,
            )
            if status == 200:
                still_missing = (data or {}).get("missing_fields", [])
                if still_missing:
                    st.warning(f"Saved, but still missing: {', '.join(still_missing)}")
                else:
                    st.success("Clarification saved. Case is complete.")
                st.rerun()
            else:
                st.error(message or "Unable to clarify case.")

    with st.expander("Timeline"):
        status, events, message = _api_request("GET", f"/api/v1/cases/{case_id}/events", timeout=10)
        if status == 200 and isinstance(events, list) and events:
            for event in events:
                st.write(
                    f"- {_fmt_time(str(event.get('created_at', '')))} | "
                    f"{event.get('event_type', 'EVENT')} | {event.get('message', '')}"
                )
        elif status == 200:
            st.info("No timeline events yet.")
        else:
            st.error(message or "Unable to load timeline.")


def _render_manage_cases_page(backend_online: bool):
    _render_hero(
        "Manage Cases",
        "Monitor queue, update status, and resolve missing information from one workspace.",
    )

    if not backend_online:
        st.error("API is offline.")
        return

    status, data, message = _api_request("GET", "/api/v1/cases", timeout=12)
    if status != 200 or not isinstance(data, list):
        st.error(message or "Unable to load cases.")
        return
    if not data:
        st.info("No cases found.")
        return

    df = pd.DataFrame(data)
    for column in ["supplier", "invoice_no", "product", "status", "urgency"]:
        if column not in df.columns:
            df[column] = ""

    total = len(df)
    pending = int((df["status"] == "PENDING_INFO").sum())
    routed = int((df["status"] == "ROUTED").sum())
    resolved = int((df["status"] == "RESOLVED").sum())

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        _render_kpi("Total Cases", total)
    with k2:
        _render_kpi("Pending Info", pending)
    with k3:
        _render_kpi("Routed", routed)
    with k4:
        _render_kpi("Resolved", resolved)
    st.write("")

    f1, f2 = st.columns([1, 2])
    with f1:
        status_filter = st.selectbox("Filter by status", ["ALL", "NEW", "PENDING_INFO", "ROUTED", "RESOLVED"])
    with f2:
        search = st.text_input("Search supplier / invoice / product")

    filtered = df.copy()
    if status_filter != "ALL":
        filtered = filtered[filtered["status"] == status_filter]
    if search.strip():
        query = search.strip().lower()
        filtered = filtered[
            filtered["supplier"].fillna("").astype(str).str.lower().str.contains(query)
            | filtered["invoice_no"].fillna("").astype(str).str.lower().str.contains(query)
            | filtered["product"].fillna("").astype(str).str.lower().str.contains(query)
        ]

    filtered = filtered.sort_values("id", ascending=False)
    if filtered.empty:
        st.info("No matching case.")
        return

    table = filtered[
        ["id", "status", "issue_type", "urgency", "supplier", "invoice_no", "product", "next_action"]
    ].rename(
        columns={
            "id": "Case ID",
            "status": "Status",
            "issue_type": "Type",
            "urgency": "Priority",
            "supplier": "Supplier",
            "invoice_no": "Invoice No",
            "product": "Product",
            "next_action": "Next Action",
        }
    )
    st.dataframe(table, use_container_width=True, hide_index=True)

    selected_id = st.selectbox("Select case", filtered["id"].tolist())
    selected_case = filtered[filtered["id"] == selected_id].iloc[0].to_dict()
    _render_case_actions(selected_case)


def _render_benefits_page():
    _render_hero(
        "Why This System Is Better Than Manual-only Workflow",
        "Users still type input, but workflow decisions and controls are automated and standardized.",
    )

    st.markdown("### What gets automated after typing once")
    a1, a2, a3 = st.columns(3)
    with a1:
        _render_kpi("Automated #1", "Issue Classification")
    with a2:
        _render_kpi("Automated #2", "Priority + Next Action")
    with a3:
        _render_kpi("Automated #3", "Duplicate + Missing-field Checks")

    st.write("")
    comparison = pd.DataFrame(
        [
            {
                "Manual process": "Retype data in multiple tools",
                "StockFlow AI": "Single intake creates structured case",
                "Operational impact": "Less repetitive entry and fewer errors",
            },
            {
                "Manual process": "Reviewer decides with inconsistent logic",
                "StockFlow AI": "System suggests issue type, urgency, and action",
                "Operational impact": "More consistent routing decisions",
            },
            {
                "Manual process": "Missing fields discovered late",
                "StockFlow AI": "Missing fields detected immediately",
                "Operational impact": "Faster closure and less back-and-forth",
            },
            {
                "Manual process": "Duplicate cases are common",
                "StockFlow AI": "Duplicate guard before create",
                "Operational impact": "Cleaner queue and less noise",
            },
            {
                "Manual process": "Weak audit trail",
                "StockFlow AI": "Event timeline by case",
                "Operational impact": "Clear traceability for review",
            },
        ]
    )
    st.table(comparison)

    st.markdown(
        """
        ### Core benefits
        1. Faster case intake and triage.
        2. Standardized decisions with lower dependency on individual interpretation.
        3. Better reliability through deterministic fallback when GLM key is unavailable.
        4. Better governance via status lifecycle and timeline events.
        """
    )


backend_online, health_data = _health()

with st.sidebar:
    st.title("🧊 StockFlow AI")
    st.caption("High-clarity operations workspace")
    st.divider()

    page = st.radio(
        "Navigation",
        ["New Case", "Manage Cases", "Why This System"],
        label_visibility="collapsed",
    )

    st.divider()
    st.subheader("Service Status")
    if backend_online:
        st.success("API Online", icon="🟢")
        st.caption(f"AI Mode: {health_data.get('ai_mode', 'unknown')}")
        st.caption(f"Model: {health_data.get('glm_model', 'unknown')}")
    else:
        st.error("API Offline", icon="🔴")
        st.caption("Start backend: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000")

if page == "New Case":
    _render_new_case_page(backend_online)
elif page == "Manage Cases":
    _render_manage_cases_page(backend_online)
else:
    _render_benefits_page()
