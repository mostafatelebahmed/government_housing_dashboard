import folium
from streamlit_folium import st_folium
import plotly.express as px
import streamlit as st
import json

# def get_color(housing_type):
#     """Returns a hex color based on housing type hash."""
#     colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
#     if not housing_type: return '#3388ff'
#     idx = hash(str(housing_type)) % len(colors)
#     return colors[idx]

def render_map(display_gdf, zoom_gdf=None, zoom_target=None):
    """
    display_gdf: البيانات التي ستُرسم (كل المشاريع).
    zoom_gdf: البيانات التي سنأخذ حدودها للزووم (المحافظة المختارة).
    zoom_target: حدود مشروع معين (لو داس على الزر).
    """
    egypt_center = [26.8206, 30.8025]
    start_zoom = 6
    has_data = not display_gdf.empty and 'geometry' in display_gdf.columns

    # 1. تحديد الزووم (الكاميرا)
    fit_bounds_coords = None
    
    # الحالة 1: المستخدم ضغط على زر مشروع معين (أعلى أولوية)
    if zoom_target:
        fit_bounds_coords = [[zoom_target[1], zoom_target[0]], [zoom_target[3], zoom_target[2]]]
    
    # الحالة 2: المستخدم اختار فلتر مكان (محافظة/مدينة)
    elif zoom_gdf is not None and not zoom_gdf.empty:
        try:
            # نأخذ حدود المحافظة/المدينة المختارة فقط
            bounds = zoom_gdf.total_bounds
            fit_bounds_coords = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]
        except: pass
        
    # الحالة 3: عرض عام (أول ما يفتح)
    # لا نقوم بعمل fit_bounds هنا لنترك الحرية للمستخدم، أو نتركه على مصر

    # 2. إنشاء الخريطة
    m = folium.Map(location=egypt_center, zoom_start=start_zoom, tiles=None)

    # 3. الطبقات (الترتيب مهم: الأولى هي الافتراضية)
    
    # --- (1) Street Map: الافتراضي (خفيف وسريع) ---
    folium.TileLayer(
        'OpenStreetMap', 
        name='Street Map (شوارع)', 
        control=True
    ).add_to(m)

    # --- (2) Satellite: اختياري (ثقيل) ---
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite (واقعي)',
        overlay=False,
        control=True
    ).add_to(m)

    # 4. رسم البيانات (نرسم display_gdf بالكامل - لا نخفي شيئاً)
    if has_data:
        # تطبيق الزووم إذا وجدنا إحداثيات (من زر أو فلتر)
        if fit_bounds_coords:
            m.fit_bounds(fit_bounds_coords)
        
        geojson_data = json.loads(display_gdf.to_json())
        folium.GeoJson(
            geojson_data,
            name="Projects",
            style_function=lambda x: {'fillColor': '#3b82f6', 'color': '#1e40af', 'weight': 2, 'fillOpacity': 0.5},
            highlight_function=lambda x: {'fillColor': '#f59e0b', 'color': 'white', 'weight': 3, 'fillOpacity': 0.8},
            tooltip=folium.GeoJsonTooltip(
                fields=['project_name', 'city', 'housing_type', 'condition', 'buildings_count', 'floors_count', 'units_count'],
                aliases=['المشروع:', 'الموقع:', 'النوع:', 'الحالة:', 'عمارات:', 'أدوار:', 'وحدات:'],
                localize=True,
                style="font-family: 'Cairo', sans-serif; font-size: 14px;"
            )
        ).add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)
    return st_folium(m, width="100%", height=600, returned_objects=["bounds", "last_object_clicked"])
def render_charts(gdf):
    if gdf.empty: return

    # --- Global Styling Config ---
    font_family = "Cairo, sans-serif"
    title_style = dict(family=font_family, size=20, color="#1e3a8a") 
    label_style = dict(family=font_family, size=12, color="#4a5568")
    
    def polish_chart(fig, title_text):
        """Applies consistent styling to all charts."""
        fig.update_layout(
            title=dict(
                text=title_text,
                x=0.5,              # Center title
                xanchor='center',
                yanchor='top',
                font=title_style
            ),
            font=dict(family=font_family),
            margin=dict(t=60, b=40, l=20, r=20),
            height=350,
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5,
                font=label_style
            )
        )
        return fig

    # 1. Pie Chart Helper
    def create_pie(col, title):
        df = gdf[col].value_counts().reset_index()
        df.columns = ['Label', 'Count']
        
        fig = px.pie(
            df, names='Label', values='Count', 
            hole=0.5, 
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        # Put labels inside if possible, or connected
        fig.update_traces(textposition='inside', textinfo='percent+label')
        return polish_chart(fig, f"<b>{title}</b>")

    # 2. Horizontal Bar Chart Helper (Better for text labels)
    def create_bar(col, title):
        df = gdf[col].value_counts().reset_index()
        df.columns = ['Label', 'Count']
        df = df.sort_values('Count', ascending=True) # Sort for visual hierarchy
        
        fig = px.bar(
            df, x='Count', y='Label', 
            orientation='h', # Horizontal is better for Arabic labels
            text='Count',
            color='Count',
            color_continuous_scale='Blues'
        )
        fig.update_traces(textposition='outside', textfont=dict(size=12, weight='bold'))
        fig = polish_chart(fig, f"<b>{title}</b>")
        fig.update_layout(
            xaxis_title=None, 
            yaxis_title=None, 
            coloraxis_showscale=False
        )
        return fig

    # --- Grid Layout ---
    
    # Row 1
    c1, c2, c3 = st.columns(3)
    with c1: st.plotly_chart(create_pie('decisions', ' القرارات الصادرة'), use_container_width=True)
    with c2: st.plotly_chart(create_bar('housing_type', ' نوع الإسكان'), use_container_width=True)
    with c3: st.plotly_chart(create_pie('owner', ' الجهة المالكة'), use_container_width=True)

    # Row 2
    c4, c5, c6 = st.columns(3)
    with c4: st.plotly_chart(create_bar('tenure', ' نوع الحيازة'), use_container_width=True)
    with c5: st.plotly_chart(create_pie('condition', ' الحالة العامة'), use_container_width=True)
    with c6: st.plotly_chart(create_pie('gas_connection', ' توصيل الغاز'), use_container_width=True)