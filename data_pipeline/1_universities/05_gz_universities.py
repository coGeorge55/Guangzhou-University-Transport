import geopandas as gpd
import os

def main():
    # 1. 设定相对路径
    # 当前脚本所在目录: .../data_pipeline/1_universities
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 项目根目录 (回退两级): .../Guangzhou-University-Transport
    project_root = os.path.dirname(os.path.dirname(current_dir))
    
    # 定义输入输出目录
    # 根据你的要求，输入数据在 data/raw，输出在 data/processed
    input_dir = os.path.join(project_root, 'data', 'raw')
    output_dir = os.path.join(project_root, 'data', 'processed')
    
    # 2. 定义文件路径
    # 假设 '广州市.shp' 也在 data/raw 目录下，如果不是请修改此处
    gz_boundary_path = os.path.join(input_dir, '广州市.shp')
    university_path = os.path.join(input_dir, 'university_wgs84.shp')
    output_path = os.path.join(output_dir, 'Gz_university.shp')

    print(f"工作目录设定:")
    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")

    # 3. 读取数据
    if not os.path.exists(gz_boundary_path) or not os.path.exists(university_path):
        print("错误：找不到输入文件，请检查文件是否在 data/raw 目录下。")
        return

    print("正在读取 Shapefile...")
    try:
        gdf_gz = gpd.read_file(gz_boundary_path)
        gdf_uni = gpd.read_file(university_path)
    except Exception as e:
        print(f"读取失败: {e}")
        return

    # 4. 统一坐标系 (以广州市边界为准)
    target_crs = gdf_gz.crs
    print(f"目标坐标系: {target_crs}")

    if gdf_uni.crs != target_crs:
        print("正在转换大学数据坐标系以匹配底图...")
        gdf_uni = gdf_uni.to_crs(target_crs)

    # 5. 执行裁剪
    print("正在执行掩膜/裁剪 (Clip)...")
    # clip 函数自动保留在 gdf_gz 范围内的点
    uni_clipped = gpd.clip(gdf_uni, gdf_gz)

    # 6. 保存结果
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"正在保存至: {output_path}")
    try:
        uni_clipped.to_file(output_path, driver='ESRI Shapefile', encoding='utf-8')
        print(f"处理完成！保留了 {len(uni_clipped)} 个大学点位。")
    except Exception as e:
        print(f"保存失败: {e}")

if __name__ == "__main__":
    main()