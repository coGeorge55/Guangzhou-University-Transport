# Guangzhou University Public Transport Accessibility Analysis
# 广州高校公共交通可达性分析

本项目旨在构建一个基于 GIS 的后端系统，用于分析广州市各高校周边的公共交通覆盖情况。项目包含完整的数据处理流水线，涵盖数据抓取、坐标转换、空间裁剪（Spatial Clip）到 PostGIS 数据库自动化入库。

## 📂 目录结构 (Directory Structure)

```text
├── backend/                # Flask 后端服务 (API)
├── data/
│   ├── raw/                # 原始数据 (需包含 广州市.shp 等行政边界文件)
│   └── processed/          # 处理后的标准空间数据 (Shapefile)
├── data_pipeline/
│   ├── 1_universities/     # 高校数据处理流
│   └── 2_bus_stops/        # 公交站点数据处理流
└── requirements.txt        # 项目依赖库
运行爬虫脚本前，请确保在 `data/` 目录下创建相应的文件夹，并替换代码中的 API Key。
