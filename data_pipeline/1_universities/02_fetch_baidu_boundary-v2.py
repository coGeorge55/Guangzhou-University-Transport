import requests
import time
import pandas as pd
import json
import random
from urllib.parse import quote
import os

# 【配置区】请在此处更新你的 Cookie

BAIDU_COOKIE = '''YOUR_BAIDU_MAP_COOKIE_HERE'''

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://map.baidu.com/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Cookie": BAIDU_COOKIE
}

SEARCH_URL = "https://map.baidu.com/?qt=s&wd={}&rn=10&ie=utf-8&c=1"
EXT_URL = "https://map.baidu.com/?qt=ext&uid={}&l=18&ext_ver=new"

def search_place(keyword):
    """搜索地点，返回结果列表"""
    encoded_kw = quote(keyword)
    url = SEARCH_URL.format(encoded_kw)
    try:
        # 随机延迟，避免触发反爬
        time.sleep(random.uniform(0.8, 1.5))
        r = requests.get(url, headers=HEADERS, timeout=10)
        
        # 检查是否被百度拦截
        if "反爬" in r.text or r.status_code == 403:
            print(f" 警告：可能触发了验证码，建议更新 Cookie 或在浏览器访问一次 map.baidu.com")
            return []
            
        data = r.json()
        content = data.get("content", [])
        return content if isinstance(content, list) else []
    except Exception as e:
        print(f" 搜索请求异常: {e}")
        return []

def fetch_geo(uid):
    """根据 UID 获取 geo 字符串"""
    url = EXT_URL.format(uid)
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        content = data.get("content")
        if isinstance(content, dict):
            return content.get("geo")
        return None
    except Exception as e:
        print(f" 获取 geo 异常: {e}")
        return None

def is_polygon(geo_str):
    """
    判断 geo 字符串是否为多边形（边界）。
    点数据的 geo 格式通常为 '1|123.45,23.45' (短，无分号)
    面数据的 geo 格式通常为 '1|123.45,23.45;123.46,23.46...' (长，含分号)
    """
    if not geo_str:
        return False
    # 如果包含分号 ';'，说明由多个点组成，是线或面
    # 如果长度非常长 (>100)，也大概率是面
    return ";" in geo_str and len(geo_str) > 100

def find_best_geo_in_results(results, strict_polygon=True):
    """
    在搜索结果列表中寻找最佳的 geo 数据。
    strict_polygon=True 表示只接受面数据（有边界的），忽略单纯的点。
    """
    for i, item in enumerate(results):
        uid = item.get("uid")
        name = item.get("name")
        
        if not uid: continue
        
        geo = fetch_geo(uid)
        
        # 判断是否为面数据
        if geo and is_polygon(geo):
            print(f"    found polygon at result #{i+1}: {name}")
            return uid, geo
            
    return None, None

def fetch_university_geo_smart(name):
    """
    智能抓取策略：
    1. 搜原名 -> 遍历前10个结果找面数据
    2. 搜 "原名+校区" -> 遍历找面数据
    3. 搜 "原名+广州" -> 遍历找面数据
    """
    
    # --- 策略 1: 直接搜索原名 ---
    # print(f"尝试策略1: 搜索 '{name}'")
    results = search_place(name)
    uid, geo = find_best_geo_in_results(results)
    if uid: return uid, geo

    # --- 策略 2: 尝试添加 '校区' (针对大学) ---
    # 很多大学的主词条没边界，但 'xx大学xx校区' 有边界
    keyword_2 = name + "校区"
    print(f"未找到，尝试策略2: 搜索 '{keyword_2}'")
    results = search_place(keyword_2)
    uid, geo = find_best_geo_in_results(results)
    if uid: return uid, geo
    
    # --- 策略 3: 尝试添加 '学院' 或 '广州' (针对职业技术学院) ---
    # 有些学校名字比较短，或者需要具体到城市
    keyword_3 = name + "广州"
    print(f"未找到，尝试策略3: 搜索 '{keyword_3}'")
    results = search_place(keyword_3)
    uid, geo = find_best_geo_in_results(results)
    if uid: return uid, geo

    # --- 兜底: 如果只要是点也行，可以在这里放宽限制 ---
    # 目前保持严格，只返回有边界的数据
    return None, None

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    data_raw_dir = os.path.join(project_root, 'data', 'raw')

    # 输入文件 (对应上一步生成的 guangzhou_universities.csv)
    input_path = os.path.join(data_raw_dir, "guangzhou_universities.csv")
    # 输出文件
    output_path = os.path.join(data_raw_dir, "university_geo_v2.csv")

    # 读取文件
    try:
        # 注意：这里读取的列名可能需要根据 1_scrape_names.py 的输出微调
        # 上一步输出的列名是 "University Name"
        df = pd.read_csv(input_path, encoding='utf-8')
    except:
        df = pd.read_csv(input_path, encoding='gbk')

    rows = []
    total = len(df)
    print(f"开始任务，共 {total} 所学校")

    for index, row in df.iterrows():
        name = str(row["University Name"]).strip()
        print(f"[{index+1}/{total}] 正在抓取: {name} ...", end="", flush=True)
        
        try:
            uid, geo = fetch_university_geo_smart(name)
            
            if geo:
                rows.append({"name": name, "uid": uid, "geo": geo})
                print(f"成功 (Geo长度: {len(geo)})")
            else:
                print(f"彻底未找到边界")
            
            # 这里的sleep稍微短一点，因为 search_place 内部已经有 sleep 了
            # 但为了安全，还是稍微停顿一下
            time.sleep(0.5)
            
        except Exception as e:
            print(f" Error: {e}")

    # 保存
    if rows:
        pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"\n完成！已保存 {len(rows)} 条数据到 {output_path}")
    else:
        print("\n未获取到任何数据，请检查 Cookie 或网络。")

if __name__ == "__main__":
    main()