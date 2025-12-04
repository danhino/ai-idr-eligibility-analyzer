"""
CRUD forms for managing CPT, CAS, and Remark codes.
"""
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session

from src.db import get_session, CPTCode, CASCode, RemarkCode
from src.utils.logging import logger


def render_code_management_form():
    """Render code management form in Streamlit."""
    st.header("Code Management")
    
    tab1, tab2, tab3, tab4 = st.tabs(["CPT Codes", "CAS Codes", "Remark Codes", "Bulk Import"])
    
    with tab1:
        _render_cpt_form()
    
    with tab2:
        _render_cas_form()
    
    with tab3:
        _render_remark_form()
    
    with tab4:
        _render_bulk_import()


def _render_cpt_form():
    """Render CPT code management form."""
    st.subheader("CPT Codes")
    
    session = get_session()
    
    # Initialize session state for selected codes
    if "cpt_selected" not in st.session_state:
        st.session_state.cpt_selected = set()
    
    # Display existing codes
    codes = session.query(CPTCode).all()
    
    if codes:
        # Create DataFrame with select column
        data = []
        for c in codes:
            data.append({
                "Select": c.code in st.session_state.cpt_selected,
                "Code": c.code,
                "Description": c.description,
                "Active": "Yes" if c.active else "No"
            })
        df = pd.DataFrame(data)
        
        # Bulk actions
        col1, col2, col3 = st.columns([2, 2, 4])
        with col1:
            if st.button("Select All", key="cpt_select_all"):
                st.session_state.cpt_selected = {c.code for c in codes}
                st.rerun()
        with col2:
            if st.button("Deselect All", key="cpt_deselect_all"):
                st.session_state.cpt_selected = set()
                st.rerun()
        with col3:
            if st.button("Delete Selected", key="cpt_bulk_delete", type="primary"):
                if st.session_state.cpt_selected:
                    try:
                        deleted_count = 0
                        for code in st.session_state.cpt_selected:
                            existing = session.query(CPTCode).filter_by(code=code).first()
                            if existing:
                                session.delete(existing)
                                deleted_count += 1
                        session.commit()
                        st.session_state.cpt_selected = set()
                        st.success(f"Deleted {deleted_count} CPT code(s)")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Error: {e}")
                        logger.error(f"Bulk delete error: {e}")
                else:
                    st.warning("No codes selected")
        
        # Display table with checkboxes
        for idx, row in df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([1, 2, 6, 1, 2])
            with col1:
                selected = st.checkbox(
                    "",
                    value=row["Select"],
                    key=f"cpt_check_{row['Code']}",
                    label_visibility="collapsed"
                )
                if selected:
                    st.session_state.cpt_selected.add(row["Code"])
                else:
                    st.session_state.cpt_selected.discard(row["Code"])
            with col2:
                st.write(f"**{row['Code']}**")
            with col3:
                st.write(row["Description"])
            with col4:
                st.write(row["Active"])
            with col5:
                if st.button("Edit", key=f"cpt_edit_btn_{row['Code']}"):
                    st.session_state.cpt_edit_code = row["Code"]
                    st.session_state.cpt_edit_description = row["Description"]
                    st.session_state.cpt_edit_active = row["Active"] == "Yes"
                    st.rerun()
        
        st.divider()
    else:
        st.info("No CPT codes in database.")
    
    # Add/Edit form
    st.subheader("Add or Edit CPT Code")
    with st.form("cpt_form"):
        # Pre-fill form if editing
        edit_code = st.session_state.get("cpt_edit_code", "")
        edit_description = st.session_state.get("cpt_edit_description", "")
        edit_active = st.session_state.get("cpt_edit_active", True)
        
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("CPT Code (5 digits)", value=edit_code, max_chars=10, disabled=bool(edit_code))
        with col2:
            active = st.checkbox("Active", value=edit_active)
        
        description = st.text_area("Description", value=edit_description)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            add_btn = st.form_submit_button("Add/Update", type="primary")
        with col2:
            if edit_code:
                cancel_btn = st.form_submit_button("Cancel Edit")
                if cancel_btn:
                    for key in list(st.session_state.keys()):
                        if key.startswith("cpt_edit"):
                            del st.session_state[key]
                    st.rerun()
        with col3:
            clear_btn = st.form_submit_button("Clear")
        
        if add_btn and code:
            try:
                existing = session.query(CPTCode).filter_by(code=code).first()
                if existing:
                    existing.description = description
                    existing.active = active
                    st.success(f"Updated CPT code {code}")
                else:
                    session.add(CPTCode(code=code, description=description, active=active))
                    st.success(f"Added CPT code {code}")
                session.commit()
                # Clear edit state
                for key in list(st.session_state.keys()):
                    if key.startswith("cpt_edit"):
                        del st.session_state[key]
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"Error: {e}")
                logger.error(f"CPT code management error: {e}")
        
        if clear_btn:
            for key in list(st.session_state.keys()):
                if key.startswith("cpt_edit"):
                    del st.session_state[key]
            st.rerun()
    
    session.close()


def _render_cas_form():
    """Render CAS code management form."""
    st.subheader("CAS Codes")
    
    session = get_session()
    
    # Initialize session state for selected codes
    if "cas_selected" not in st.session_state:
        st.session_state.cas_selected = set()
    
    # Display existing codes
    codes = session.query(CASCode).all()
    
    if codes:
        # Bulk actions
        col1, col2, col3 = st.columns([2, 2, 4])
        with col1:
            if st.button("Select All", key="cas_select_all"):
                st.session_state.cas_selected = {(c.group_code, c.reason_code) for c in codes}
                st.rerun()
        with col2:
            if st.button("Deselect All", key="cas_deselect_all"):
                st.session_state.cas_selected = set()
                st.rerun()
        with col3:
            if st.button("Delete Selected", key="cas_bulk_delete", type="primary"):
                if st.session_state.cas_selected:
                    try:
                        deleted_count = 0
                        for group_code, reason_code in st.session_state.cas_selected:
                            existing = session.query(CASCode).filter_by(
                                group_code=group_code,
                                reason_code=reason_code
                            ).first()
                            if existing:
                                session.delete(existing)
                                deleted_count += 1
                        session.commit()
                        st.session_state.cas_selected = set()
                        st.success(f"Deleted {deleted_count} CAS code(s)")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Error: {e}")
                        logger.error(f"Bulk delete error: {e}")
                else:
                    st.warning("No codes selected")
        
        # Display table with checkboxes
        for c in codes:
            key = (c.group_code, c.reason_code)
            selected = key in st.session_state.cas_selected
            
            col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 6, 2])
            with col1:
                checkbox_selected = st.checkbox(
                    "",
                    value=selected,
                    key=f"cas_check_{c.group_code}_{c.reason_code}",
                    label_visibility="collapsed"
                )
                if checkbox_selected:
                    st.session_state.cas_selected.add(key)
                else:
                    st.session_state.cas_selected.discard(key)
            with col2:
                st.write(f"**{c.group_code}**")
            with col3:
                st.write(f"**{c.reason_code}**")
            with col4:
                st.write(c.description)
            with col5:
                col5a, col5b = st.columns(2)
                with col5a:
                    st.write("Yes" if c.active else "No")
                with col5b:
                    if st.button("Edit", key=f"cas_edit_btn_{c.group_code}_{c.reason_code}"):
                        st.session_state.cas_edit_group = c.group_code
                        st.session_state.cas_edit_reason = c.reason_code
                        st.session_state.cas_edit_description = c.description
                        st.session_state.cas_edit_active = c.active
                        st.rerun()
        
        st.divider()
    else:
        st.info("No CAS codes in database.")
    
    # Add/Edit form
    st.subheader("Add or Edit CAS Code")
    with st.form("cas_form"):
        # Pre-fill form if editing
        edit_group = st.session_state.get("cas_edit_group", "")
        edit_reason = st.session_state.get("cas_edit_reason", "")
        edit_description = st.session_state.get("cas_edit_description", "")
        edit_active = st.session_state.get("cas_edit_active", True)
        
        col1, col2 = st.columns(2)
        with col1:
            group_code = st.text_input("Group Code (CO, PR, PI, OA, etc.)", value=edit_group, max_chars=2, disabled=bool(edit_group)).upper()
        with col2:
            reason_code = st.text_input("Reason Code", value=edit_reason, max_chars=10, disabled=bool(edit_reason))
        
        description = st.text_area("Description", value=edit_description)
        active = st.checkbox("Active", value=edit_active)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            add_btn = st.form_submit_button("Add/Update", type="primary")
        with col2:
            if edit_group and edit_reason:
                cancel_btn = st.form_submit_button("Cancel Edit")
                if cancel_btn:
                    for key in list(st.session_state.keys()):
                        if key.startswith("cas_edit"):
                            del st.session_state[key]
                    st.rerun()
        with col3:
            clear_btn = st.form_submit_button("Clear")
        
        if add_btn and group_code and reason_code:
            try:
                existing = session.query(CASCode).filter_by(
                    group_code=group_code,
                    reason_code=reason_code
                ).first()
                if existing:
                    existing.description = description
                    existing.active = active
                    st.success(f"Updated CAS code {group_code}-{reason_code}")
                else:
                    session.add(CASCode(
                        group_code=group_code,
                        reason_code=reason_code,
                        description=description,
                        active=active
                    ))
                    st.success(f"Added CAS code {group_code}-{reason_code}")
                session.commit()
                # Clear edit state
                for key in list(st.session_state.keys()):
                    if key.startswith("cas_edit"):
                        del st.session_state[key]
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"Error: {e}")
                logger.error(f"CAS code management error: {e}")
        
        if clear_btn:
            for key in list(st.session_state.keys()):
                if key.startswith("cas_edit"):
                    del st.session_state[key]
            st.rerun()
    
    session.close()


def _render_remark_form():
    """Render Remark code management form."""
    st.subheader("Remark Codes (RARC)")
    
    session = get_session()
    
    # Initialize session state for selected codes
    if "remark_selected" not in st.session_state:
        st.session_state.remark_selected = set()
    
    # Display existing codes
    codes = session.query(RemarkCode).all()
    
    if codes:
        # Bulk actions
        col1, col2, col3 = st.columns([2, 2, 4])
        with col1:
            if st.button("Select All", key="remark_select_all"):
                st.session_state.remark_selected = {c.rarc for c in codes}
                st.rerun()
        with col2:
            if st.button("Deselect All", key="remark_deselect_all"):
                st.session_state.remark_selected = set()
                st.rerun()
        with col3:
            if st.button("Delete Selected", key="remark_bulk_delete", type="primary"):
                if st.session_state.remark_selected:
                    try:
                        deleted_count = 0
                        for rarc in st.session_state.remark_selected:
                            existing = session.query(RemarkCode).filter_by(rarc=rarc).first()
                            if existing:
                                session.delete(existing)
                                deleted_count += 1
                        session.commit()
                        st.session_state.remark_selected = set()
                        st.success(f"Deleted {deleted_count} RARC code(s)")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Error: {e}")
                        logger.error(f"Bulk delete error: {e}")
                else:
                    st.warning("No codes selected")
        
        # Display table with checkboxes
        for c in codes:
            selected = c.rarc in st.session_state.remark_selected
            
            col1, col2, col3, col4 = st.columns([1, 2, 6, 2])
            with col1:
                checkbox_selected = st.checkbox(
                    "",
                    value=selected,
                    key=f"remark_check_{c.rarc}",
                    label_visibility="collapsed"
                )
                if checkbox_selected:
                    st.session_state.remark_selected.add(c.rarc)
                else:
                    st.session_state.remark_selected.discard(c.rarc)
            with col2:
                st.write(f"**{c.rarc}**")
            with col3:
                st.write(c.description)
            with col4:
                col4a, col4b = st.columns(2)
                with col4a:
                    st.write("Yes" if c.active else "No")
                with col4b:
                    if st.button("Edit", key=f"remark_edit_btn_{c.rarc}"):
                        st.session_state.remark_edit_rarc = c.rarc
                        st.session_state.remark_edit_description = c.description
                        st.session_state.remark_edit_active = c.active
                        st.rerun()
        
        st.divider()
    else:
        st.info("No Remark codes in database.")
    
    # Add/Edit form
    st.subheader("Add or Edit Remark Code")
    with st.form("remark_form"):
        # Pre-fill form if editing
        edit_rarc = st.session_state.get("remark_edit_rarc", "")
        edit_description = st.session_state.get("remark_edit_description", "")
        edit_active = st.session_state.get("remark_edit_active", True)
        
        rarc = st.text_input("RARC Code (e.g., MA130, N130)", value=edit_rarc, max_chars=10, disabled=bool(edit_rarc)).upper()
        description = st.text_area("Description", value=edit_description)
        active = st.checkbox("Active", value=edit_active)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            add_btn = st.form_submit_button("Add/Update", type="primary")
        with col2:
            if edit_rarc:
                cancel_btn = st.form_submit_button("Cancel Edit")
                if cancel_btn:
                    for key in list(st.session_state.keys()):
                        if key.startswith("remark_edit"):
                            del st.session_state[key]
                    st.rerun()
        with col3:
            clear_btn = st.form_submit_button("Clear")
        
        if add_btn and rarc:
            try:
                existing = session.query(RemarkCode).filter_by(rarc=rarc).first()
                if existing:
                    existing.description = description
                    existing.active = active
                    st.success(f"Updated RARC {rarc}")
                else:
                    session.add(RemarkCode(rarc=rarc, description=description, active=active))
                    st.success(f"Added RARC {rarc}")
                session.commit()
                # Clear edit state
                for key in list(st.session_state.keys()):
                    if key.startswith("remark_edit"):
                        del st.session_state[key]
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"Error: {e}")
                logger.error(f"Remark code management error: {e}")
        
        if clear_btn:
            for key in list(st.session_state.keys()):
                if key.startswith("remark_edit"):
                    del st.session_state[key]
            st.rerun()
    
    session.close()


def _render_bulk_import():
    """Render bulk import form."""
    st.subheader("Bulk Import from CSV")
    
    uploaded_file = st.file_uploader(
        "Upload CSV file",
        type=["csv"],
        help="CSV should have columns: code/group_code/reason_code/rarc, description, active"
    )
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df.head(10))
            
            if st.button("Import Codes"):
                session = get_session()
                imported = 0
                
                # Detect code type from columns
                if "code" in df.columns:
                    # CPT codes
                    for _, row in df.iterrows():
                        code = str(row["code"]).strip()
                        desc = str(row.get("description", "")).strip()
                        active = bool(row.get("active", True))
                        
                        existing = session.query(CPTCode).filter_by(code=code).first()
                        if not existing:
                            session.add(CPTCode(code=code, description=desc, active=active))
                            imported += 1
                
                elif "group_code" in df.columns and "reason_code" in df.columns:
                    # CAS codes
                    for _, row in df.iterrows():
                        group = str(row["group_code"]).strip().upper()
                        reason = str(row["reason_code"]).strip()
                        desc = str(row.get("description", "")).strip()
                        active = bool(row.get("active", True))
                        
                        existing = session.query(CASCode).filter_by(
                            group_code=group,
                            reason_code=reason
                        ).first()
                        if not existing:
                            session.add(CASCode(
                                group_code=group,
                                reason_code=reason,
                                description=desc,
                                active=active
                            ))
                            imported += 1
                
                elif "rarc" in df.columns:
                    # Remark codes
                    for _, row in df.iterrows():
                        rarc = str(row["rarc"]).strip().upper()
                        desc = str(row.get("description", "")).strip()
                        active = bool(row.get("active", True))
                        
                        existing = session.query(RemarkCode).filter_by(rarc=rarc).first()
                        if not existing:
                            session.add(RemarkCode(rarc=rarc, description=desc, active=active))
                            imported += 1
                
                session.commit()
                session.close()
                st.success(f"Imported {imported} codes")
                st.rerun()
        
        except Exception as e:
            st.error(f"Import error: {e}")
            logger.error(f"Bulk import error: {e}")

