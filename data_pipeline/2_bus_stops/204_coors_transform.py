import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import transform
import math
import os

# 坐标转换算法模块

x_pi = 3.14159265358979324 * 3000.0 / 180.0
pi = math.pi
a = 6378245.0
es = 0.00669342162296594323

# 百度墨卡托转经纬度所需的系数表
MCBAND = [12890594.86, 8362377.87, 5591021, 3481989.83, 1678043.12, 0]
MC2LL = [
    [1.410526172116255e-8, 0.00000898305509648872, -1.9939833816331, 200.9824383106796, -187.2403703815547, 91.6087516669843, -23.38765649603339, 2.57121317296198, -0.03801003308653, 17337981.2],
    [-7.435856389565537e-9, 0.000008983055097726239, -0.78625201886289, 96.32687599759846, -1.85204757529826, -59.36935905485877, 47.40033549296737, -16.50741931063887, 2.28786674699375, 10260144.86],
    [-3.030883460898826e-8, 0.00000898305509983578, 0.30071316287616, 59.74293618442277, 7.357984074871, -25.38371002664745, 13.45380521110908, -3.29883767235584, 0.32710905363475, 6856817.37],
    [-1.981981304930552e-8, 0.000008983055099779535, 0.03278182852591, 40.31678527705744, 0.65659298677277, -4.44255534477492, 0.85341911805263, 0.12923347998204, -0.04625736007561, 4482777.06],
    [3.09191371068437e-9, 0.000008983055096812155, 0.00006995724062, 23.10934304144901, -0.00023663490511, -0.6321817810242, -0.00663494467273, 0.03430082397953, -0.00466043876332, 2555164.4],
    [2.890871144776878e-9, 0.000008983055095805407, -3.068298e-8, 7.47137025468032, -0.00000353937994, -0.02145144861037, -0.00001234426596, 0.00010322952773, -0.00000323890364, 826088.5]
]

def bdmc_to_bdll(x, y):
    """百度墨卡托 -> 百度经纬度"""
    abs_x, abs_y = abs(x), abs(y)
    cf = None
    for i in range(len(MCBAND)):
        if abs_y >= MCBAND[i]:
            cf = MC2LL[i]
            break
    if cf is None: return x, y
    
    lon = cf[0] + cf[1] * abs_x
    cc = abs_y / cf[9]
    lat = cf[2] + cf[3]*cc + cf[4]*cc**2 + cf[5]*cc**3 + cf[6]*cc**4 + cf[7]*cc**5 + cf[8]*cc**6
    
    if x < 0: lon = -lon
    if y < 0: lat = -lat
    return lon, lat

def BD09_to_GCJ02(bd_lng, bd_lat):
    """百度经纬度 -> GCJ02"""
    x = bd_lng - 0.0065
    y = bd_lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)
    gcj_lng = z * math.cos(theta)
    gcj_lat = z * math.sin(theta)
    return gcj_lng, gcj_lat

def _transformlat(lng, lat):
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 * math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * pi) + 40.0 * math.sin(lat / 3.0 * pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * pi) + 320 * math.sin(lat * pi / 30.0)) * 2.0 / 3.0
    return ret

def _transformlng(lng, lat):
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 * math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * pi) + 40.0 * math.sin(lng / 3.0 * pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * pi) + 300.0 * math.sin(lng / 30.0 * pi)) * 2.0 / 3.0
    return ret

def GCJ02_to_WGS84(gcj_lng, gcj_lat):
    """GCJ02 -> WGS84"""
    dlat = _transformlat(gcj_lng - 105.0, gcj_lat - 35.0)
    dlng = _transformlng(gcj_lng - 105.0, gcj_lat - 35.0)
    radlat = gcj_lat / 180.0 * pi
    magic = math.sin(radlat)
    magic = 1 - es * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - es)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
    mglat = gcj_lat + dlat
    mglng = gcj_lng + dlng
    lng = gcj_lng * 2 - mglng
    lat = gcj_lat * 2 - mglat
    return lng, lat

def transform_point_logic(x, y, z=None):
    """
    组合变换逻辑：被 transform 自动调用
    """
    # 1. 墨卡托 -> 百度经纬度
    # 注意：这里的输入 x, y 已经是除以 100 后的标准墨卡托单位了，因为我们在 main 中预处理了
    lon_bd, lat_bd = bdmc_to_bdll(x, y)
    # 2. 百度经纬度 -> GCJ02
    lon_gcj, lat_gcj = BD09_to_GCJ02(lon_bd, lat_bd)
    # 3. GCJ02 -> WGS84
    lon_wgs, lat_wgs = GCJ02_to_WGS84(lon_gcj, lat_gcj)
    
    if z is not None:
        return lon_wgs, lat_wgs, z
    return lon_wgs, lat_wgs

# 主逻辑
def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    data_raw_dir = os.path.join(project_root, 'data', 'raw')

    input_csv = os.path.join(data_raw_dir, "bus_stops_bd09mc.csv")
    output_shp = os.path.join(data_raw_dir, "bus_stops_wgs84.shp")
    
    if not os.path.exists(input_csv):
        # 尝试在 data 文件夹下查找（如果存在）
        if os.path.exists(os.path.join("data", input_csv)):
            input_csv = os.path.join("data", input_csv)
            output_shp = os.path.join("data", output_shp)
        else:
            print(f"找不到文件: {input_csv}。")
            return

    print("开始读取坐标数据...")
    try:
        df = pd.read_csv(input_csv, encoding='utf-8')
    except UnicodeDecodeError:
        print("检测到编码不是 UTF-8，尝试使用 GBK...")
        df = pd.read_csv(input_csv, encoding='gbk')
        
    print(f"共 {len(df)} 个站点数据。")
    print(df.head(2))

    # 关键步骤：数据单位修正
    # 公交站点数据中的坐标被放大了100倍 (e.g., 1261171716 -> 12611717.16)
    # 必须先除以 100 才能匹配标准墨卡托算法
    print("正在修正坐标单位 (除以100)...")
    df['bd_x'] = pd.to_numeric(df['bd_x'], errors='coerce') / 100.0
    df['bd_y'] = pd.to_numeric(df['bd_y'], errors='coerce') / 100.0
    df.dropna(subset=['bd_x', 'bd_y'], inplace=True)

    print("正在生成几何对象并进行坐标转换 (BD09MC -> WGS84)...")
    
    # 1. 先创建 GeoDataFrame，此时坐标系是“缩放修正后”的百度墨卡托
    # 使用 gpd.points_from_xy 比逐行 apply Point 更快
    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.bd_x, df.bd_y),
        crs="EPSG:3857" # 临时占位，实际是 Baidu Mercator
    )

    # 2. 使用 apply + transform 进行几何转换 (参考 03_geometry_to_wgs84.py 的写法)
    gdf["geometry"] = gdf["geometry"].apply(
        lambda g: transform(transform_point_logic, g)
    )
    
    # 转换完成后，重置 CRS 为 WGS84
    gdf = gdf.set_crs("EPSG:4326", allow_override=True)

    print("正在保存 Shapefile...")
    # 整理字段名：Shapefile 字段名限制 10 字符，且最好避免中文
    # input: line_name, stop_name, sequence
    rename_map = {
        "line_name": "line",
        "stop_name": "station",
        "sequence": "seq"
    }
    # 只重命名存在的列
    cols_to_rename = {k: v for k, v in rename_map.items() if k in gdf.columns}
    out_gdf = gdf.rename(columns=cols_to_rename)
    
    # 仅保留关键列和 geometry
    keep_cols = list(cols_to_rename.values()) + ['geometry']
    out_gdf = out_gdf[keep_cols]

    try:
        out_gdf.to_file(output_shp, encoding='utf-8')
        print(f"转换完成！Shapefile 已保存至: {output_shp}")
    except Exception as e:
        print(f"保存 Shapefile 失败: {e}")
        # 备份方案：保存为 GeoJSON
        json_path = output_shp.replace('.shp', '.geojson')
        out_gdf.to_file(json_path, driver='GeoJSON')
        print(f"   已备份保存为 GeoJSON: {json_path}")

if __name__ == "__main__":
    main()
