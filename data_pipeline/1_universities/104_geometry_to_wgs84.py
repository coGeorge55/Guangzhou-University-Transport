import geopandas as gpd
import pandas as pd
from shapely.ops import transform
import math
import os

# 坐标转换算法模块
# 包含：BD09MC -> BD09 -> GCJ02 -> WGS84
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
    if cf is None: return x, y # Fallback or Error
    
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
    组合变换函数: BD09MC -> BD09 -> GCJ02 -> WGS84
    """
    # 1. 墨卡托 -> 百度经纬度
    lon_bd, lat_bd = bdmc_to_bdll(x, y)
    # 2. 百度经纬度 -> GCJ02
    lon_gcj, lat_gcj = BD09_to_GCJ02(lon_bd, lat_bd)
    # 3. GCJ02 -> WGS84
    lon_wgs, lat_wgs = GCJ02_to_WGS84(lon_gcj, lat_gcj)
    
    if z is not None:
        return lon_wgs, lat_wgs, z
    return lon_wgs, lat_wgs

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    data_raw_dir = os.path.join(project_root, 'data', 'raw')
    output_dir = os.path.join(project_root, 'data', 'raw')

    input_path = os.path.join(data_raw_dir, "university_bd09mc.pkl")
    output_path = os.path.join(output_dir, "university_wgs84.shp")
    
    if not os.path.exists(input_path):
        print(f"找不到输入文件: {input_path}")
        print("   请先运行 03_geo_to_geometry.py 生成该文件")
        return

    print(f"Loading data: {input_path}")
    df = pd.read_pickle(input_path)
    
    # 转换为 GeoDataFrame
    # 注意：EPSG:3857 只是一个占位符，用来告诉 geopandas 这是投影坐标，
    # 实际上它是百度特有的投影，我们马上就会手动 transform 掉它
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:3857")

    print(f"Transforming coordinates for {len(gdf)} features...")
    print("Step: BD09MC -> BD09 -> GCJ02 -> WGS84")
    
    # 使用 shapely 的 transform 对 geometry 列的所有点进行各种数学变换
    gdf["geometry"] = gdf["geometry"].apply(
        lambda g: transform(transform_point_logic, g)
    )

    # 转换完成后，坐标系就是 WGS84 (EPSG:4326) 了
    gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    
    print(f"Saving Shapefile to: {output_path}")
    # Shapefile 字段名有截断风险，确保没有超长字段名
    try:
        gdf.to_file(output_path, encoding='utf-8')
        print("转换成功！Shapefile 已保存。")
    except Exception as e:
        print(f"保存失败: {e}")
        # 如果 shp 保存失败，尝试保存为 GeoJSON
        json_path = output_path.replace(".shp", ".geojson")
        gdf.to_file(json_path, driver='GeoJSON')
        print(f"已备份保存为 GeoJSON: {json_path}")

if __name__ == "__main__":
    main()
