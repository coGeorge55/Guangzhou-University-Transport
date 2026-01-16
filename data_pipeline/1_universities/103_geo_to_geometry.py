import pandas as pd
from shapely.geometry import Polygon
from shapely.ops import unary_union
import re
import os

def parse_baidu_geo(geo_str):
    """
    Parses Baidu Map 'geo' string into a Shapely geometry.
    Format detected: '4|bound|1-x1,y1,x2,y2...;1-x1,y1...'
    """
    if pd.isna(geo_str) or not isinstance(geo_str, str):
        return None

    try:
        # The geometry data is usually in the 3rd part (index 2)
        parts = geo_str.split('|')
        if len(parts) < 3:
            return None
        
        geo_data = parts[2]
        
        # Segments are separated by ';' (e.g. multiple campuses or rings)
        segments = [s for s in geo_data.split(';') if s.strip()]
        
        polygons = []
        
        for seg in segments:
            # Each segment is a comma-separated list of coordinates
            coords_raw = seg.split(',')
            
            # Clean the first element which may contain a prefix like '1-'
            # e.g. "1-12621779.35" -> "12621779.35"
            if coords_raw:
                if '-' in coords_raw[0] and not coords_raw[0].startswith('-'):
                    # Remove prefix up to the first dash
                    coords_raw[0] = coords_raw[0].split('-', 1)[1]
            
            # Must have an even number of coordinates (x, y pairs)
            if len(coords_raw) < 6: # At least 3 points (6 numbers) for a polygon
                continue
                
            # Parse into (x, y) tuples
            try:
                coords_float = [float(x) for x in coords_raw]
            except ValueError:
                continue
                
            points = list(zip(coords_float[::2], coords_float[1::2]))
            
            # Create Polygon
            if len(points) >= 3:
                poly = Polygon(points)
                if not poly.is_valid:
                    poly = poly.buffer(0) # Fix self-intersections
                if not poly.is_empty:
                    polygons.append(poly)
        
        if not polygons:
            return None
            
        # Merge all parts (e.g. North Campus + South Campus)
        return unary_union(polygons)

    except Exception as e:
        # print(f"Error parsing geo: {e}")
        return None

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    data_raw_dir = os.path.join(project_root, 'data', 'raw')

    input_csv = os.path.join(data_raw_dir, "university_geo.csv")
    output_pkl = os.path.join(data_raw_dir, "university_bd09mc.pkl")

    print(f"Reading {input_csv}...")
    try:
        df = pd.read_csv(input_csv, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(input_csv, encoding='gbk')
    
    if 'geo' not in df.columns:
        print("Error: 'geo' column not found in CSV.")
        return

    print("Parsing geometries...")
    df['geometry'] = df['geo'].apply(parse_baidu_geo)
    
    # Filter valid results
    valid_df = df[df['geometry'].notnull()].copy()
    print(f"Successfully parsed {len(valid_df)} out of {len(df)} records.")
    
    print(f"Saving to {output_pkl}...")
    valid_df.to_pickle(output_pkl)
    print("Done.")

if __name__ == "__main__":
    main()
