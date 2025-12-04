import streamlit as st
import pandas as pd
import geopandas as gpd
import os
import sys
import base64
from shapely.geometry import Point

# Setup Path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_PATH = os.path.join(BASE_DIR, 'data', 'sample', 'default.json')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data_loader import load_geojson, process_upload
from ui.components import render_map, render_charts

st.set_page_config(layout="wide", page_title="تقرير إستبيان حصر المساكن", page_icon="🏢", initial_sidebar_state="expanded")

def reset_zoom():
    st.session_state['zoom_target'] = None
# --- Helper: Images ---
def get_img_as_base64(file_path):
    if not os.path.exists(file_path): return ""
    with open(file_path, "rb") as f: data = f.read()
    return base64.b64encode(data).decode()

logo_r_path = "assets/logo_right.png" 
logo_l_path = "assets/logo_left.png"
img_r_b64 = get_img_as_base64(logo_r_path)
img_l_b64 = get_img_as_base64(logo_l_path)

# --- CSS Styling ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'Cairo', sans-serif; }}
    .stApp {{ background-color: #f8f9fa; }}

    /* Header */
    .custom-header {{
        display: flex; justify-content: space-between; align-items: center;
        background: linear-gradient(to bottom, #ffffff, #f1f5f9); 
        padding: 10px 20px; border-radius: 15px;
        border-bottom: 3px solid #1e3a8a; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }}
    .header-title h1 {{ color: #1e3a8a; font-weight: 800; margin: 0; font-size: 1.6rem; text-align: center; }}
    .header-img {{ height: 60px; width: auto; }}

    /* --- STYLE 1: TOP CARDS (Gradient Blue) --- */
    .kpi-card-top {{
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; padding: 15px; border-radius: 12px; text-align: center;
        box-shadow: 0 4px 6px rgba(30, 58, 138, 0.2); margin-bottom: 10px;
        transition: transform 0.2s;
    }}
    .kpi-card-top:hover {{ transform: translateY(-3px); }}
    .kpi-top-val {{ font-size: 1.8rem; font-weight: 800; margin-bottom: 5px; }}
    .kpi-top-lbl {{ font-size: 0.9rem; opacity: 0.9; font-weight: 600; }}

    /* --- STYLE 2: BOTTOM CARDS (Dark Tech) --- */
    .kpi-card-bottom {{
        background: linear-gradient(145deg, #1f2937, #111827);
        color: #f3f4f6; padding: 15px; border-radius: 8px; text-align: center;
        border-left: 4px solid #10b981; /* Emerald Accent */
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    .kpi-bot-val {{ font-size: 1.6rem; font-weight: bold; color: #34d399; }}
    .kpi-bot-lbl {{ font-size: 0.85rem; color: #9ca3af; letter-spacing: 0.5px; }}

    /* Project Card */
    .project-card {{
        background-color: white; padding: 12px; margin-bottom: 8px;
        border-radius: 6px; border: 1px solid #e5e7eb;
        border-right: 4px solid #f59e0b;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        direction: rtl; text-align: right;
    }}
    .card-row {{ display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 4px; }}
    .card-label {{ color: #6b7280; font-weight: 600; }}
    .card-val {{ color: #1f2937; font-weight: 700; }}
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown(f"""
<div class="custom-header">
    <img src="data:image/png;base64,{img_r_b64}" class="header-img" onerror="this.style.display='none'">
    <div class="header-title"><h1>المساكن الحكومية على مستوى محافظات جمهورية مصر العربية</h1></div>
    <img src="data:image/png;base64,{img_l_b64}" class="header-img" onerror="this.style.display='none'">
</div>
""", unsafe_allow_html=True)

# if 'data' not in st.session_state:
    # محاولة تحميل الملف الافتراضي أولاً
if os.path.exists(DEFAULT_DATA_PATH):
    try:
        st.session_state['data'] = load_geojson(DEFAULT_DATA_PATH)
        st.session_state['is_default'] = True # علامة لمعرفة أننا نستخدم الافتراضي
    except Exception:
        st.session_state['data'] = gpd.GeoDataFrame()
else:
    st.session_state['data'] = gpd.GeoDataFrame()
# --- Sidebar Filters ---
# --- Sidebar ---
with st.sidebar:
    st.markdown("## 🌪️  Filters")
    
    # 1. تعريف المتغيرات الأساسية للبيانات
    gdf = st.session_state['data']
    filtered_gdf = gdf.copy() if not gdf.empty else gpd.GeoDataFrame()
    
    # 2. كود الفلاتر (وضعناه في الأول ليظهر في الأعلى)
    if not gdf.empty:
        # فلتر المحافظة
        if 'governorate' in gdf.columns:
            govs = ['الكل'] + sorted(list(gdf['governorate'].dropna().unique()))
            sel_gov = st.selectbox("📍 المحافظة", govs, on_change=reset_zoom)
            if sel_gov != 'الكل':
                filtered_gdf = filtered_gdf[filtered_gdf['governorate'] == sel_gov]

        # فلتر المدينة
        if 'city' in gdf.columns:
            cities = ['الكل'] + sorted(list(filtered_gdf['city'].dropna().unique()))
            sel_city = st.selectbox("🏙️ المدينة / المركز", cities, on_change=reset_zoom)
            if sel_city != 'الكل':
                filtered_gdf = filtered_gdf[filtered_gdf['city'] == sel_city]

        st.markdown("---")
        
        # باقي الفلاتر
        if 'housing_type' in gdf.columns:
            types = ['الكل'] + sorted(list(filtered_gdf['housing_type'].dropna().unique()))
            sel_type = st.selectbox("🏠 نوع الإسكان", types, on_change=reset_zoom)
            if sel_type != 'الكل':
                filtered_gdf = filtered_gdf[filtered_gdf['housing_type'] == sel_type]

        if 'owner' in gdf.columns:
            owners = ['الكل'] + sorted(list(filtered_gdf['owner'].dropna().unique()))
            sel_owner = st.selectbox("🏢 الجهة المالكة", owners, on_change=reset_zoom)
            if sel_owner != 'الكل':
                filtered_gdf = filtered_gdf[filtered_gdf['owner'] == sel_owner]

        if 'condition' in gdf.columns:
            conds = ['الكل'] + sorted(list(filtered_gdf['condition'].dropna().unique()))
            sel_cond = st.selectbox("🛠️ الحالة العامة", conds, on_change=reset_zoom)
            if sel_cond != 'الكل':
                filtered_gdf = filtered_gdf[filtered_gdf['condition'] == sel_cond]

        if 'decisions' in gdf.columns:
            decs = ['الكل'] + sorted(list(filtered_gdf['decisions'].dropna().unique()))
            sel_dec = st.selectbox("📜 القرارات الصادرة", decs, on_change=reset_zoom)
            if sel_dec != 'الكل':
                filtered_gdf = filtered_gdf[filtered_gdf['decisions'] == sel_dec]
        
        if 'gas_connection' in gdf.columns:
            gas_opts = ['الكل'] + sorted(list(filtered_gdf['gas_connection'].dropna().unique()))
            sel_gas = st.selectbox("🔥 توصيل الغاز", gas_opts, on_change=reset_zoom)
            if sel_gas != 'الكل':
                filtered_gdf = filtered_gdf[filtered_gdf['gas_connection'] == sel_gas]
                
        st.caption(f"المشاريع المطابقة: {len(filtered_gdf)}")
    else:
        filtered_gdf = gpd.GeoDataFrame()
        st.info("لا توجد بيانات لعرض الفلاتر.")

    # 3. فاصل لتوضيح نهاية الفلاتر
    st.markdown("---")
    
    # 4. كود رفع البيانات (نقلناه للأسفل)
    # جعلنا expanded=False عشان ما ياخدش مساحة إلا لو احتاجته
    with st.expander("📂 إدارة البيانات (رفع/حذف)", expanded=False):
        uploaded_file = st.file_uploader("رفع ملف بيانات جديد", type=['xlsx', 'csv', 'geojson', 'json'])
        
        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1]
            with st.spinner('جاري المعالجة...'):
                new_data = process_upload(uploaded_file, file_type)
                if not new_data.empty:
                    st.session_state['data'] = new_data
                    st.session_state['is_default'] = False
                    st.success("تم التحميل!")
        
        # # زر الاستعادة
        # if not st.session_state.get('is_default', False) and os.path.exists(DEFAULT_DATA_PATH):
        #     if st.button("🔄 استعادة الافتراضي"):
        #         st.session_state['data'] = load_geojson(DEFAULT_DATA_PATH)
        #         st.session_state['is_default'] = True
        #         st.rerun()
                
        # # زر الحذف
        # if not st.session_state['data'].empty:
        #     if st.button("🗑️ حذف البيانات", type="primary"):
        #         st.session_state['data'] = gpd.GeoDataFrame()
        #         st.session_state['is_default'] = False
        #         st.rerun()

    # المتغير النهائي المستخدم في الخريطة
    final_map_gdf = filtered_gdf

# --- TOP BAR (Blue/Gradient) ---
# Logic: Using 'top_bar_gdf' which is only filtered by Governorate (as per previous request)
if 'final_map_gdf' in locals() and not final_map_gdf.empty:
    top_bar_gdf = final_map_gdf
else:
    # حالة احتياطية لو مفيش بيانات
    top_bar_gdf = gdf.copy() if not gdf.empty else gpd.GeoDataFrame()

tp = len(top_bar_gdf)
tu = int(top_bar_gdf['units_count'].sum()) if not top_bar_gdf.empty else 0
tb = int(top_bar_gdf['buildings_count'].sum()) if not top_bar_gdf.empty else 0
au = int(tu / tp) if tp > 0 else 0

c1, c2, c3 = st.columns(3)
c1.markdown(f'<div class="kpi-card-top"><div class="kpi-top-val">{tp}</div><div class="kpi-top-lbl">إجمالي عدد المواقع </div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-card-top"><div class="kpi-top-val">{tu:,}</div><div class="kpi-top-lbl">إجمالي عدد الوحدات</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-card-top"><div class="kpi-top-val">{tb:,}</div><div class="kpi-top-lbl">عدد عدد العمارات</div></div>', unsafe_allow_html=True)
# c4.markdown(f'<div class="kpi-card-top"><div class="kpi-top-val">{au}</div><div class="kpi-top-lbl">متوسط وحدات/مشروع</div></div>', unsafe_allow_html=True)

st.markdown("<hr style='margin: 15px 0; opacity:0.3;'>", unsafe_allow_html=True)

# --- Map & List ---
col_map, col_list = st.columns([2.5, 1])
visible_gdf = final_map_gdf.copy() # نستخدم نسخة عشان الترتيب
selected_project_index = None      # متغير لتخزين رقم المشروع المختار
with col_map:
    # 1. نجهز البيانات:
    # display_data: كل البيانات (عشان تظهر في الخريطة كلها وما تختفيش)
    # zoom_data: البيانات المفلترة (عشان الخريطة تعمل زووم عليها بس)
    
    display_data = gdf if not gdf.empty else gpd.GeoDataFrame()
    zoom_data = final_map_gdf if not final_map_gdf.empty else None

    # 2. رسم الخريطة
    # نرسل display_data للرسم، ونرسل zoom_data لضبط حدود الزووم
    map_output = render_map(
        display_data, 
        zoom_gdf=zoom_data, 
        zoom_target=st.session_state.get('zoom_target')
    )
    
    # (تم حذف كود تنظيف الزووم من هنا لكي تثبت الخريطة على المشروع المختار)
    # if st.session_state.get('zoom_target'):
    #    st.session_state['zoom_target'] = None

    # 4. تحديث القائمة بناءً على حدود الخريطة الحالية (Bounds)
    if map_output and "bounds" in map_output and not display_data.empty:
        bounds = map_output["bounds"]
        if bounds:
            try:
                minx, miny = bounds['_southWest']['lng'], bounds['_southWest']['lat']
                maxx, maxy = bounds['_northEast']['lng'], bounds['_northEast']['lat']
                # نحدث visible_gdf لتكون هي المشاريع الظاهرة في الكادر من "كل البيانات"
                visible_gdf = display_data.cx[minx:maxx, miny:maxy]
            except: pass

    # 5. منطق النقر (Click Logic)
    if map_output and map_output.get('last_object_clicked'):
        clicked_loc = map_output['last_object_clicked']
        if clicked_loc:
            pt = Point(clicked_loc['lng'], clicked_loc['lat'])
            # البحث في "كل البيانات" لأن المستخدم قد يضغط على مشروع خارج الفلتر
            hits = display_data[display_data.contains(pt)]
            
            if hits.empty:
                hits = display_data[display_data.intersects(pt.buffer(0.0001))]

            if not hits.empty:
                found_idx = hits.index[0]
                if st.session_state.get('selected_project_idx') != found_idx:
                    st.session_state['selected_project_idx'] = found_idx
                    st.rerun()
with col_list:
    # 1. منطق إعادة الترتيب (المختار يظهر في الأعلى)
    sel_idx = st.session_state.get('selected_project_idx')
    
    if sel_idx is not None and not visible_gdf.empty:
        if sel_idx in visible_gdf.index:
            sel_row = visible_gdf.loc[[sel_idx]]
            rest_rows = visible_gdf.drop(sel_idx)
            visible_gdf = pd.concat([sel_row, rest_rows])

    count_visible = len(visible_gdf) if not visible_gdf.empty else 0
    st.markdown(f"<div style='text-align:right; font-weight:bold; margin-bottom:10px; color:#1f2937;'>📋 قائمة المواقع الظاهرة على الخريطة ({count_visible})</div>", unsafe_allow_html=True)
    
    with st.container(height=600):
        if not visible_gdf.empty:
            for idx, row in visible_gdf.head(50).iterrows():
                # تجهيز البيانات
                bldgs = int(row.get('buildings_count', 0))
                floors = int(row.get('floors_count', 0))
                u_per_floor = int(row.get('units_per_floor', 0))
                total_u = int(row.get('units_count', 0))
                proj_name = row.get('project_name', 'غير معروف')
                
                # هل هذا المشروع مختار؟
                is_selected = (idx == sel_idx)
                
                # --- الفكرة هنا: الإطار الخارجي ---
                # إذا كان المشروع مختاراً، نضعه داخل حاوية بحدود (Border)
                # إذا لم يكن مختاراً، نضعه في حاوية شفافة عادية
                if is_selected:
                    # يمكنك تغيير icon إلى أي رمز تحبه
                    st.success(f"📍 **المشروع المحدد:** {proj_name}") 
                    wrapper = st.container(border=True)
                else:
                    wrapper = st.container()

                # نبدأ الرسم داخل الحاوية (سواء كانت بحدود أو بدون)
                with wrapper:
                    # 1. الكارت (بنفس الكود الخاص بك حرفياً)
                    st.markdown(f"""
                    <div class="project-card" style="margin-bottom: 0px; border-bottom-left-radius: 0; border-bottom-right-radius: 0; border-bottom: 0;">
                        <div style="font-weight:bold; color:#1e3a8a; margin-bottom:5px;">{row.get('project_name', 'غير معروف')}</div>
                        <div class="card-row">
                            <span><span class="card-label">المدينة:</span> {row.get('city', '-')}</span>
                        </div>
                        <div class="card-row">
                            <span><span class="card-label">نوع الإسكان:</span> {row.get('housing_type', '-')}</span>
                        </div>
                        <div class="card-row">
                            <span><span class="card-label">حالة العمارات:</span> {row.get('condition', '-')}</span>
                        </div>
                        <hr style="margin:4px 0; border-top:1px dashed #eee;">
                        <div class="card-row">
                            <span><span class="card-label">عمارات:</span> <b>{bldgs}</b></span>
                            <span><span class="card-label">أدوار:</span> <b>{floors}</b></span>
                            <span><span class="card-label">و/دور:</span> <b>{u_per_floor}</b></span>
                        </div>
                        <div style="background:#f0f9ff; padding:3px; border-radius:4px; margin-top:5px; text-align:center; color:#0369a1; font-weight:bold;">
                            إجمالي عدد الوحدات: {total_u} وحدة
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 2. الزر (بنفس طريقتنا لضمان عمله)
                    # نغير نوع الزر فقط ليكون primary (ملون) لو مختار
                    btn_type = "primary" if is_selected else "secondary"
                    
                    if st.button("🔍 عرض الموقع على الخريطة", key=f"zoom_btn_{idx}", type=btn_type, use_container_width=True):
                        st.session_state['zoom_target'] = row.geometry.bounds
                        st.session_state['selected_project_idx'] = idx
                        st.rerun()
                
                # فاصل بسيط بين الكروت
                st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

            if len(visible_gdf) > 50: st.caption(f"... و {len(visible_gdf) - 50} مشروع آخر")
        else:
            st.info("لا توجد مشاريع.")

# --- BOTTOM BAR (Restored Dark Tech Style) ---
if not visible_gdf.empty:
    st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)
    
    vis_proj = len(visible_gdf)
    vis_units = int(visible_gdf['units_count'].sum())
    vis_bldgs = int(visible_gdf['buildings_count'].sum())
    
    st.markdown('<h4 style="text-align:right; color:#1f2937; margin-bottom:10px;"> إحصائيات النطاق الجغرافي (المعروض)</h4>', unsafe_allow_html=True)
    
    b1, b2, b3 = st.columns(3)
    # Applied 'kpi-card-bottom' class for the Dark Tech style
    b1.markdown(f'<div class="kpi-card-bottom"><div class="kpi-bot-val">{vis_proj}</div><div class="kpi-bot-lbl">عدد المواقع المعروضة على الخريطة </div></div>', unsafe_allow_html=True)
    b2.markdown(f'<div class="kpi-card-bottom"><div class="kpi-bot-val">{vis_units:,}</div><div class="kpi-bot-lbl">إجمالي عدد الوحدات المعروض على الخريطة</div></div>', unsafe_allow_html=True)
    b3.markdown(f'<div class="kpi-card-bottom"><div class="kpi-bot-val">{vis_bldgs:,}</div><div class="kpi-bot-lbl">إجمالي عدد العمارات المعروض على الخريطة</div></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown('<h3 style="text-align:right; color:#1e3a8a;">📊 التحليلات البيانية التفصيلية</h3>', unsafe_allow_html=True)
    render_charts(visible_gdf)

elif final_map_gdf.empty:
    st.info("قم برفع البيانات لظهور التحليلات.")