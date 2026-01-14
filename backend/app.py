from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text
from flask_cors import CORS 

app = Flask(__name__)
CORS(app)  

# 1. 数据库配置
engine = create_engine("postgresql://postgres:your_password@localhost:5432/gis_db")

@app.route('/api/nearest_bus_stop', methods=['GET'])
def get_nearest_bus_stop():
    uni_name = request.args.get('name')
    if not uni_name:
        return jsonify({"error": "Missing 'name' parameter"}), 400
    
    # SQL 查询
    sql_query = text("""
        SELECT 
            b.station as station_name, 
            ST_X(b.geometry) as lon, 
            ST_Y(b.geometry) as lat,
            ST_Distance(b.geometry::geography, ST_Centroid(u.geometry)::geography) as dist
        FROM "Gz_BusStops" b, "Gz_universities" u
        WHERE u.name = :name
        ORDER BY b.geometry <-> ST_Centroid(u.geometry)
        LIMIT 1;
    """)
    
    try:
        with engine.connect() as conn:
            print(f"正在查询学校: {uni_name}") 
            result = conn.execute(sql_query, {"name": uni_name}).fetchone()
            
            if result:
                return jsonify({
                    "station": result.station_name,
                    "distance_meters": round(result.dist, 2),
                    "coordinates": [result.lon, result.lat]
                })
            else:
                return jsonify({"error": "未找到该学校或附近无站点"}), 404
        
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500 
    


@app.route('/api/stats', methods=['GET'])
def get_university_stats():
    # SQL 查询
    sql_query = text("""
        SELECT 
            u.name, 
            COUNT(b.station) as count,
            ST_X(ST_Centroid(u.geometry)) as lon,
            ST_Y(ST_Centroid(u.geometry)) as lat
        FROM "Gz_universities" u
        LEFT JOIN "Gz_BusStops" b 
        ON ST_DWithin(ST_Centroid(u.geometry)::geography, b.geometry::geography, 100) -- 100米范围
        GROUP BY u.name, u.geometry
        ORDER BY count DESC;
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(sql_query).fetchall()
            
            # 将数据库查询结果转换为 JSON 格式列表
            data = []
            for row in result:
                data.append({
                    "name": row.name,
                    "count": row.count,
                    "lat": row.lat,
                    "lon": row.lon
                })
            
            return jsonify(data)
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500 





if __name__ == '__main__':
    app.run(debug=True, port=5000)