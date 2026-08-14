import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. ตั้งค่าหน้าเพจ
st.set_page_config(page_title="GEM System", page_icon="⚽", layout="wide")

st.title("⚽ GEM System - Betting AI Manager")
st.markdown("---")

# 2. เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# ฟังก์ชันดึงข้อมูลล่าสุด
@st.cache_data(ttl=10)  # ดึงข้อมูลใหม่ทุกๆ 10 วินาที
def load_data():
    df = conn.read(worksheet="DATA", ttl="0")
    df = df.dropna(how='all') # ลบแถวที่เป็นว่างทั้งหมด
    return df

try:
    df_raw = load_data()
    # ทำความสะอาดข้อมูลสำหรับแสดงผล
    df = df_raw.copy()
    df.columns = df.columns.str.strip()
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().replace('nan', '')
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลจาก Google Sheets: {e}")
    st.stop()

# สร้าง แท็บ สำหรับแยกสลับหน้าจอ (ค้นหา / บันทึก)
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

    # การกรองข้อมูล
    filtered_df = df.copy()

    if search_hcap:
        filtered_df = filtered_df[filtered_df['Handicap'] == search_hcap]
    if search_ou:
        filtered_df = filtered_df[filtered_df['O/U'] == search_ou]
    if search_ai_hcap:
        filtered_df = filtered_df[filtered_df['AI Handicap'] == search_ai_hcap]
    if search_ai_ou:
        filtered_df = filtered_df[filtered_df['AI O/U'] == search_ai_ou]
    if search_tip_ha:
        filtered_df = filtered_df[filtered_df['Tip H/A'].str.lower() == search_tip_ha.lower()]
    if search_tip_ou:
        filtered_df = filtered_df[filtered_df['Tip O/U'].str.lower() == search_tip_ou.lower()]

    st.markdown("---")
    st.subheader(f"📊 ผลลัพธ์การค้นหา ({len(filtered_df)} รายการ)")

    if not filtered_df.empty:
        display_cols = [c for c in ['League', 'ผลสกอร์', 'Status Handicap', 'Handicap', 'Status O/U'] if c in filtered_df.columns]
        st.dataframe(filtered_df[display_cols if display_cols else filtered_df.columns], use_container_width=True, hide_index=True)
    else:
        st.warning("ไม่พบข้อมูลที่ตรงกับเงื่อนไข")


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
            tip_ha = st.selectbox("Tip H/A", ["Home", "Away", "-"])
            tip_ou = st.selectbox("Tip O/U", ["Over", "Under", "-"])
            score = st.text_input("ผลสกอร์ (เช่น 2-1)")
            status_hcap = st.selectbox("Status Handicap", ["ชนะเต็ม", "ชนะครึ่ง", "เสมอ", "แพ้ครึ่ง", "แพ้เต็ม", "-"])
            status_ou = st.selectbox("Status O/U", ["ชนะเต็ม", "ชนะครึ่ง", "เสมอ", "แพ้ครึ่ง", "แพ้เต็ม", "-"])

        submit_btn = st.form_submit_button("💾 บันทึกข้อมูลลง Google Sheet")

        if submit_btn:
            try:
                # สร้างข้อมูลแถวใหม่ตามโครงสร้างคอลัมน์เดิม
                new_row = {
                    'League': league,
                    'Handicap': handicap,
                    'O/U': ou,
                    'AI Handicap': ai_handicap,
                    'Tip H/A': tip_ha,
                    'AI O/U': ai_ou,
                    'Tip O/U': tip_ou,
                    'ผลสกอร์': score,
                    'Status Handicap': status_hcap,
                    'Status O/U': status_ou
                }
                
                # นำแถวใหม่ไปรวมกับ Dataframe เดิม
                new_data = pd.DataFrame([new_row])
                updated_df = pd.concat([df_raw, new_data], ignore_index=True)
                
                # บันทึกกลับไปยัง Google Sheets ใน worksheet 'DATA'
                conn.update(worksheet="DATA", data=updated_df)
                
                st.success("🎉 บันทึกข้อมูลใหม่ต่อท้ายแถวใน Google Sheet สำเร็จแล้ว!")
                st.cache_data.clear()  # เคลียร์แคชเพื่อให้ข้อมูลอัปเดตทันที
                
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดขณะบันทึกข้อมูล: {e}")
