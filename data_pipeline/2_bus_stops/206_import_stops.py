import geopandas as gpd
from sqlalchemy import create_engine, text
from geoalchemy2 import Geometry
import os

# 【配置区】
DB_USER = "postgres"
DB_PASSWORD = "your_password" 
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "gis_db"

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
data_processed_dir = os.path.join(project_root, 'data', 'processed')

INPUT_SHP = os.path.join(data_processed_dir, "Gz_BusStops.shp")

TABLE_NAME = "Gz_BusStops" # 数据库中表的名称

def ingest_bus_stops_to_postgis():
    # 构建数据库连接 URL
    # client_encoding=gbk 用于防止控制台中文乱码，可视情况调整
    connection_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # 创建数据库引擎
    engine = create_engine(connection_url)

    if not os.path.exists(INPUT_SHP):
        print(f"错误：找不到文件 {INPUT_SHP}，请检查路径。")
        return

    # ---------------------------------------------------------
    # 步骤 0：自动为数据库开启 PostGIS 插件 (如果尚未开启)
    # ---------------------------------------------------------
    print("正在连接数据库...", end="")
    try:
        with engine.connect() as conn:
            # 启用 PostGIS 扩展
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
            print(" 连接成功且 PostGIS 扩展已就绪！")
    except Exception as e:
        print(f"\n数据库连接失败: {e}")
        return
        
    # ---------------------------------------------------------
    # 步骤 1：读取 Shapefile 数据
    # ---------------------------------------------------------
    print(f"正在读取 Shapefile: {INPUT_SHP}")
    try:
        gdf = gpd.read_file(INPUT_SHP, encoding='utf-8')
    except:
        print("   UTF-8 读取失败，尝试 GBK...")
        gdf = gpd.read_file(INPUT_SHP, encoding='gbk')

    print(f"   共读取到 {len(gdf)} 条公交站点数据。")

    # ---------------------------------------------------------
    # 步骤 2：数据清洗与检查
    # ---------------------------------------------------------
    # 确保坐标系是 WGS84 (EPSG:4326)
    if gdf.crs is None:
        print("   警告：源数据缺少坐标系信息，默认为 EPSG:4326")
        gdf.set_crs("EPSG:4326", inplace=True)
    elif gdf.crs.to_string() != "EPSG:4326":
        print(f"   正在将坐标系从 {gdf.crs.to_string()} 转换为 EPSG:4326...")
        gdf = gdf.to_crs("EPSG:4326")

    # ---------------------------------------------------------
    # 步骤 3：写入 PostGIS 数据库
    # ---------------------------------------------------------
    print(f"正在写入表 '{TABLE_NAME}' (SRID: 4326)...")
    
    try:
        gdf.to_postgis(
            name=TABLE_NAME,          # 表名
            con=engine,               # 数据库引擎
            if_exists='replace',      # 如果表存在则替换 ('fail', 'replace', 'append')
            index=False,              # 不将 DataFrame 的索引写入为单独的列
            dtype={
                'geometry': Geometry('POINT', srid=4326) # 关键：指定几何类型为点 (POINT)
            }
        )
        print(f"写入成功！公交站点数据已存入表: {TABLE_NAME}")
        
        # 可选：打印前几行验证
        print("-" * 30)
        print("数据预览 (前2行):")
        print(gdf.drop(columns='geometry').head(2))
        
    except Exception as e:
        print(f"写入数据库失败: {e}")

if __name__ == "__main__":
    ingest_bus_stops_to_postgis()
