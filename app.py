import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. ตั้งค่าหน้าเพจ
st.set_page_config(page_title="GEM System", page_icon="⚽", layout="wide")

st.title("⚽ GEM System - Betting AI Manager")
st.markdown("---")

# คอลัมน์มาตรฐานที่ระบบต้องการ
REQUIRED_COLUMNS = [
    'League', 'Handicap', 'O/U', 'AI Handicap', 'Tip H/A', 'AI O/U',
    'Tip O/U', 'ผลสกอร์', 'Status Handicap', 'Status O/U'
]

# 2. เชื่อมต่อ Google Sheets
try:
    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("❌ ไม่พบการตั้งค่า Google Sheets URL ใน Secrets")
    st.stop()


@st.cache_data(ttl=10)
def load_data():
    """โหลดข้อมูลแบบมีแคช ใช้สำหรับแสดงผล/ค้นหาเท่านั้น"""
    df = conn.read(
        spreadsheet=spreadsheet_url,
        worksheet="DATA",
        ttl="0"
    )
    df = df.dropna(how='all')
    return df


def load_fresh_data():
    """โหลดข้อมูลสดจาก Google Sheets โดยไม่ใช้แคช - ใช้ก่อนบันทึกข้อมูลเสมอ
    เพื่อลดความเสี่ยงข้อมูลของคนอื่นถูกเขียนทับ (race condition)"""
    df = conn.read(
        spreadsheet=spreadsheet_url,
        worksheet="DATA",
        ttl="0"
    )
    df = df.dropna(how='all')
    return df


def clean_df(df_in: pd.DataFrame) -> pd.DataFrame:
    df_out = df_in.copy()
    df_out.columns = df_out.columns.str.strip()
    for col in df_out.columns:
        df_out[col] = df_out[col].astype(str).str.strip().replace('nan', '')
    return df_out


def ensure_columns(df_in: pd.DataFrame) -> pd.DataFrame:
    """เติมคอลัมน์ที่ขาดหายไปให้ครบ เพื่อป้องกัน KeyError ตอนกรอง/บันทึก"""
    df_out = df_in.copy()
    for col in REQUIRED_COLUMNS:
        if col not in df_out.columns:
            df_out[col] = ''
    return df_out


def normalize_match(series: pd.Series, value: str) -> pd.Series:
    """เทียบค่าแบบยืดหยุ่น: ตัดช่องว่าง, ไม่สนตัวพิมพ์เล็ก-ใหญ่, contains แทน exact match"""
    value_clean = value.strip().lower()
    return series.astype(str).str.strip().str.lower().str.contains(
        value_clean, na=False, regex=False
    )


# 3. โหลดข้อมูลสำหรับแสดงผล/ค้นหา
try:
    df_raw = load_data()
    df = ensure_columns(clean_df(df_raw))
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df_raw.columns]
    if missing_cols:
        st.warning(f"⚠️ ไม่พบคอลัมน์ต่อไปนี้ในชีต (ระบบเติมค่าว่างให้ชั่วคราว): {', '.join(missing_cols)}")
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลจาก Google Sheets: {e}")
    st.stop()

# สร้าง Tabs
tab_search, tab_add = st.tabs(["🔍 ค้นหาข้อมูล", "➕ บันทึกข้อมูลใหม่"])

# ==========================================
# TAB 1: ระบบค้นหาข้อมูล (Search)
# ==========================================
with tab_search:
    st.subheader("🔍 ระบุเงื่อนไขการค้นหา")

    col1, col2 = st.columns(2)
    with col1:
        search_hcap = st.text_input("Handicap (เช่น 0.5, 0.5/1)", "").strip()
        search_ou = st.text_input("O/U (เช่น 3, 2.5/3)", "").strip()
        search_tip_ha = st.selectbox("Tip H/A", ["", "Home", "Away"])

    with col2:
        search_ai_hcap = st.text_input("AI Handicap", "").strip()
        search_ai_ou = st.text_input("AI O/U", "").strip()
        search_tip_ou = st.selectbox("Tip O/U", ["", "Over", "Under"])

    try:
        filtered_df = df.copy()

        if search_hcap:
            filtered_df = filtered_df[normalize_match(filtered_df['Handicap'], search_hcap)]
        if search_ou:
            filtered_df = filtered_df[normalize_match(filtered_df['O/U'], search_ou)]
        if search_ai_hcap:
            filtered_df = filtered_df[normalize_match(filtered_df['AI Handicap'], search_ai_hcap)]
        if search_ai_ou:
            filtered_df = filtered_df[normalize_match(filtered_df['AI O/U'], search_ai_ou)]
        if search_tip_ha:
            filtered_df = filtered_df[filtered_df['Tip H/A'].str.lower() == search_tip_ha.lower()]
        if search_tip_ou:
            filtered_df = filtered_df[filtered_df['Tip O/U'].str.lower() == search_tip_ou.lower()]

        st.markdown("---")
        st.subheader(f"📊 ผลลัพธ์การค้นหา ({len(filtered_df)} รายการ)")

        if not filtered_df.empty:
            display_cols = [c for c in ['League', 'ผลสกอร์', 'Status Handicap', 'Handicap', 'Status O/U'] if c in filtered_df.columns]
            st.dataframe(
                filtered_df[display_cols if display_cols else filtered_df.columns],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("ไม่พบข้อมูลที่ตรงกับเงื่อนไข")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดขณะค้นหาข้อมูล: {e}")

# ==========================================
# TAB 2: บันทึกข้อมูลใหม่ (Add New Data)
# ==========================================
with tab_add:
    st.subheader("📝 ฟอร์มบันทึกข้อมูลลง Sheet: DATA")

    with st.form("add_data_form", clear_on_submit=True):
        f_col1, f_col2 = st.columns(2)

        with f_col1:
            league = st.text_input("League (ชื่อลีก)")
            handicap = st.text_input("Handicap (เช่น 0.5, 1.0)")
            ou = st.text_input("O/U (เช่น 2.5, 3.0)")
            ai_handicap = st.text_input("AI Handicap")
            ai_ou = st.text_input("AI O/U")

        with f_col2:
            tip_ha = st.selectbox("Tip H/A", ["Home", "Away"])
            tip_ou = st.selectbox("Tip O/U", ["Over", "Under"])
            score = st.text_input("ผลสกอร์ (เช่น 2-1)")
            status_hcap = st.selectbox("Status Handicap", ["ชนะเต็ม", "ชนะครึ่ง", "เสมอ", "แพ้ครึ่ง", "แพ้เต็ม"])
            status_ou = st.selectbox("Status O/U", ["ชนะเต็ม", "ชนะครึ่ง", "เสมอ", "แพ้ครึ่ง", "แพ้เต็ม"])

        submit_btn = st.form_submit_button("💾 บันทึกข้อมูลลง Google Sheet")

        if submit_btn:
            # --- Validation ---
            errors = []
            if not league.strip():
                errors.append("กรุณากรอกชื่อลีก (League)")
            if not handicap.strip():
                errors.append("กรุณากรอก Handicap")
            if not ou.strip():
                errors.append("กรุณากรอก O/U")
            if not score.strip():
                errors.append("กรุณากรอกผลสกอร์")

            if errors:
                for err in errors:
                    st.warning(f"⚠️ {err}")
            else:
                try:
                    new_row = {
                        'League': league.strip(),
                        'Handicap': handicap.strip(),
                        'O/U': ou.strip(),
                        'AI Handicap': ai_handicap.strip(),
                        'Tip H/A': tip_ha,
                        'AI O/U': ai_ou.strip(),
                        'Tip O/U': tip_ou,
                        'ผลสกอร์': score.strip(),
                        'Status Handicap': status_hcap,
                        'Status O/U': status_ou
                    }

                    # โหลดข้อมูลสดล่าสุดก่อนบันทึก เพื่อลดความเสี่ยงเขียนทับข้อมูลคนอื่น
                    latest_df = load_fresh_data()
                    latest_df = ensure_columns(latest_df)
                    new_data = pd.DataFrame([new_row])
                    updated_df = pd.concat([latest_df, new_data], ignore_index=True)

                    conn.update(spreadsheet=spreadsheet_url, worksheet="DATA", data=updated_df)

                    st.success("🎉 บันทึกข้อมูลใหม่สำเร็จแล้ว!")
                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดขณะบันทึกข้อมูล: {e}")
