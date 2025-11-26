import pandas as pd
import geopandas as gpd
import os
import json
from shapely.geometry import shape

# Updated Mapping

GOV_CODES = {
    '21': 'أسوان', '18': 'أسيوط', '22': 'الأقصر', '2': 'الإسكندرية',
    '13': 'الإسماعيلية', '12': 'البحيرة', '14': 'الجيزة', '6': 'الدقهلية',
    '4': 'السويس', '7': 'الشرقية', '10': 'الغربية', '16': 'الفيوم',
    '1': 'القاهرة', '8': 'القليوبية', '11': 'المنوفية', '17': 'المنيا',
    '15': 'بني سويف', '3': 'بورسعيد', '35': 'جنوب سيناء', '5': 'دمياط',
    '19': 'سوهاج', '20': 'قنا', '9': 'كفر الشيخ'
}

COLUMN_MAPPING = {
    "المحافظة": "governorate",
    "المدينة_المركز": "city",
    "اسم_الموقع": "project_name",
    "الجهة_المالكة": "owner",
    "نوع_الحيازة": "tenure",
    "عدد_العمارات": "buildings_count",
    "عدد_الوحدات_الاجمالي": "units_count_orig", # Keep original as backup
    "عدد_الوحدات_بالدور": "units_per_floor",
    "عدد_الأدوار": "floors_count",
    "نوع_الاسكان": "housing_type",
    "الحالة_العامة_للمبني": "condition",
    "الحالة_العامة_للعمارات": "condition",
    "سنة_الانشاء": "construction_year",
    "القرارات_الصادرة_للمبني": "decisions",
    "اتصال_المشروع_بالغاز": "gas_connection"
}

def load_geojson(filepath):
    try:
        gdf = gpd.read_file(filepath)
    except Exception:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        rows = []
        for feature in data['features']:
            props = feature['properties']
            geom = shape(feature['geometry']) if feature['geometry'] else None
            props['geometry'] = geom
            rows.append(props)
        gdf = gpd.GeoDataFrame(rows)
        gdf.set_crs(epsg=32636, inplace=True, allow_override=True)
    
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
        
    return normalize_columns(gdf)

def normalize_columns(df):
    # 1. Rename columns
    df = df.rename(columns=COLUMN_MAPPING)
    
    # 2. Handle duplicate columns
    df = df.loc[:, ~df.columns.duplicated()]

    # 3. Force Numeric Conversion for Calculation Fields
    # (Coerce errors to NaN, then fill with 0)
    calc_cols = ['buildings_count', 'units_per_floor', 'floors_count']
    for col in calc_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

    # 4. Calculate Total Units (The Formula)
    # Units = Buildings * Floors * Units_Per_Floor
    df['units_count'] = df['buildings_count'] * df['floors_count'] * df['units_per_floor']

    if 'governorate' in df.columns:
        # التأكد من أن العمود نصي
        if isinstance(df['governorate'], pd.DataFrame):
            s_gov = df['governorate'].iloc[:, 0].astype(str)
        else:
            s_gov = df['governorate'].astype(str)
        
        # تنظيف الرقم (إزالة .0 إذا كانت موجودة)
        s_gov = s_gov.str.replace(r'\.0$', '', regex=True).str.strip()
        
        # استبدال الكود بالاسم
        df['governorate'] = s_gov.map(GOV_CODES).fillna(s_gov)
    # ---------------------------------------------

    # 5. Normalize text columns
    text_cols = ['governorate', 'housing_type', 'owner', 'condition', 'decisions', 'gas_connection', 'tenure', 'city', 'project_name']
    
    for col in text_cols:
        if col in df.columns:
            if isinstance(df[col], pd.DataFrame):
                s = df[col].iloc[:, 0].astype(str)
            else:
                s = df[col].astype(str)
            s = s.str.strip()
            s = s.replace(['nan', 'None', 'null', '<NA>', 'nan'], 'غير محدد')
            df[col] = s
        else:
            df[col] = 'غير محدد'
            
    return df

def process_upload(file_obj, file_type):
    if file_type in ['geojson', 'json']:
        with open("temp_up.geojson", "wb") as f:
            f.write(file_obj.getbuffer())
        return load_geojson("temp_up.geojson")
    
    elif file_type in ['xlsx', 'csv']:
        if file_type == 'xlsx':
            df = pd.read_excel(file_obj)
        else:
            df = pd.read_csv(file_obj)
            
        if 'lat' in df.columns and 'lon' in df.columns:
            gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
            return normalize_columns(gdf)
        else:
            return normalize_columns(df)
    return gpd.GeoDataFrame()