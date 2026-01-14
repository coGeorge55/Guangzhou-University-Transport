import geopandas as gpd
import os

def main():
    # 1. 设定相对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    
    input_dir = os.path.join(project_root, 'data', 'raw')
    output_dir = os.path.join(project_root, 'data', 'processed')
    
    # 2. 定义文件路径
    gz_boundary_path = os.path.join(input_dir, '广州市.shp')
    bus_stops_path = os.path.join(input_dir, 'bus_stops_wgs84.shp')
    output_path = os.path.join(output_dir, 'Gz_BusStops.shp')

    print(f"工作目录设定:")
    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")

    # 3. 读取数据
    if not os.path.exists(gz_boundary_path) or not os.path.exists(bus_stops_path):
        print("错误：找不到输入文件，请检查文件是否在 data/raw 目录下。")
        return

    print("正在读取 Shapefile (公交数据量较大，请稍候)...")
    try:
        gdf_gz = gpd.read_file(gz_boundary_path)
        gdf_bus = gpd.read_file(bus_stops_path)
    except Exception as e:
        print(f"读取失败: {e}")
        return

    # 4. 统一坐标系
    target_crs = gdf_gz.crs
    print(f"目标坐标系: {target_crs}")

    if gdf_bus.crs != target_crs:
        print("正在转换公交数据坐标系以匹配底图...")
        gdf_bus = gdf_bus.to_crs(target_crs)

    # 5. 执行裁剪
    print("正在执行掩膜/裁剪 (Clip)...")
    try:
        bus_clipped = gpd.clip(gdf_bus, gdf_gz)
    except Exception as e:
        print(f"裁剪过程出错 (可能是内存不足或拓扑错误): {e}")
        return

    # 6. 保存结果
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"正在保存至: {output_path}")
    try:
        bus_clipped.to_file(output_path, driver='ESRI Shapefile', encoding='utf-8')
        print(f"处理完成！保留了 {len(bus_clipped)} 个公交站点。")
    except Exception as e:
        print(f"保存失败: {e}")

if __name__ == "__main__":
    main()
