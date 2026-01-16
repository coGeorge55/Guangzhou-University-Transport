import geopandas as gpd
from sqlalchemy import create_engine, text
from geoalchemy2 import Geometry
from shapely.geometry import Polygon, MultiPolygon
import os

# 【配置区】
DB_USER = "postgres"
#请确认这里填的是正确的密码
DB_PASSWORD = "your_password_here" 
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "gis_db"

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
processed_dir = os.path.join(project_root, 'data', 'processed')

# 指向第5步生成的 Gz_university.shp
INPUT_SHP = os.path.join(processed_dir, "Gz_university.shp")


TABLE_NAME = "Gz_universities"

def promote_to_multi(geom):
    if geom is None: return None
    if geom.geom_type == 'Polygon':
        return MultiPolygon([geom])
    elif geom.geom_type == 'MultiPolygon':
        return geom
    return geom

def ingest_data_to_postgis():
    # 使用 gbk 以便能看清中文报错
    connection_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?client_encoding=gbk"
    
    if not os.path.exists(INPUT_SHP):
        print(f"错误：找不到文件 {INPUT_SHP}")
        return

    try:
        engine = create_engine(connection_url)

        # 自动为数据库开启 PostGIS 插件
 
        print("正在连接数据库...", end="")
        with engine.connect() as conn:
            # 1. 启用 PostGIS 扩展 
            print("正在启用 PostGIS 扩展...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit() # 提交更改
            print("PostGIS 扩展已启用！")     
   
        # 入库流程
 
        print(f"正在读取 Shapefile: {INPUT_SHP}")
        try:
            gdf = gpd.read_file(INPUT_SHP, encoding='utf-8')
        except:
            print(" UTF-8 读取失败，尝试 GBK...")
            gdf = gpd.read_file(INPUT_SHP, encoding='gbk')

        print("正在规范化几何数据 (Polygon -> MultiPolygon)...")
        gdf["geometry"] = gdf["geometry"].apply(promote_to_multi)
        
        print(f"正在写入表 '{TABLE_NAME}' (SRID: 4326)...") 
        gdf.to_postgis(
            name=TABLE_NAME, # 数据库表名
            con=engine,
            if_exists='replace',
            index=False,
            dtype={'geometry': Geometry('MULTIPOLYGON', srid=4326)},
            chunksize=100
        )
        print(f"\n{len(gdf)} 条大学边界数据已成功存入数据库！")
        
    except Exception as e:
        print("\n 发生错误")
        print(f"详细报错: {e}")

if __name__ == "__main__":
    ingest_data_to_postgis()
