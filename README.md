# 🚌 广州高校公共交通可达性分析系统

基于 Flask + PostGIS + Leaflet 的 WebGIS 应用，用于查询广州高校周边的公交站点分布及便捷度分析。

## ✨ 功能特性
- **最近站点查询**：输入高校名称，自动计算最近的公交站及距离。
- **空间统计**：一键统计并展示各高校 500m 缓冲区内的公交站点数量排行。
- **可视化交互**：基于 Leaflet 地图的交互式展示。

## 🛠️ 技术栈
- **后端**：Python (Flask), SQLAlchemy
- **数据库**：PostgreSQL + PostGIS 插件
- **前端**：HTML5, Leaflet.js
- **数据处理**：GeoPandas

## 🚀 快速开始

### 1. 环境准备
确保已安装 PostgreSQL 和 PostGIS，并创建数据库 `gis_db`。

### 2. 安装依赖
```bash
pip install -r backend/requirements.txt

## 📂 数据流水线 (Data Pipeline)

本项目包含完整的数据获取与处理脚本，位于 `data_pipeline/` 目录下。

### 1. 高校数据处理 (`data_pipeline/1_universities/`)
- `01_scrape_names.py`: 从教育网爬取广州高校名单。
- ...
- `05_ingest_universities.py`: 将处理好的 Shapefile 导入 PostGIS。

### 2. 公交网络处理 (`data_pipeline/2_bus_network/`)
- `01_scrape_lines.py`: 爬取公交线路基础信息。
- `03_fetch_stop_coords.py`: 调用地图 API 获取站点精确坐标。
- `04_ingest_stops.py`: 数据清洗并入库。

### ⚠️ 注意事项
运行爬虫脚本前，请确保在 `data/` 目录下创建相应的文件夹，并替换代码中的 API Key。