import requests
import pandas as pd
import time
import random
import os
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 【配置区】
# 替换为你的百度地图 Cookie 
BAIDU_COOKIE = '''YOUR_BAIDU_MAP_COOKIE_HERE''' 

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
data_raw_dir = os.path.join(project_root, 'data', 'raw')

# 输入文件夹: data/raw/bus_stops
INPUT_DIR = os.path.join(data_raw_dir, "bus_stops")
# 输出文件: data/raw/bus_stops_bd09mc.csv
OUTPUT_CSV = os.path.join(data_raw_dir, "bus_stops_bd09mc.csv")

# 百度地图城市代码：广州=257
CITY_CODE = 257 

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://map.baidu.com/",
    "Cookie": BAIDU_COOKIE,
    "Connection": "keep-alive"
}

# 搜索接口
SEARCH_URL = "https://map.baidu.com/?qt=s&wd={}&c={}&rn=1&ie=utf-8"

# 【核心功能封装】

def create_session():
    """创建带有自动重试功能的 Session"""
    session = requests.Session()
    # connect=3: 连接错误重试3次
    # read=3: 读取超时重试3次
    # backoff_factor=1: 失败后等待 1s, 2s, 4s...
    retry = Retry(total=5, connect=3, read=3, backoff_factor=1, 
                  status_forcelist=[500, 502, 503, 504, 429])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def load_cache_from_csv(csv_path):
    """从现有的 CSV 中加载已抓取的坐标到内存缓存"""
    cache = {}
    if os.path.exists(csv_path):
        try:
            print(f"检测到已存在的数据文件: {csv_path}，正在加载缓存...")
            df = pd.read_csv(csv_path)
            # 确保列名存在
            if 'stop_name' in df.columns and 'bd_x' in df.columns:
                # 建立 站点名 -> (x, y) 的映射
                # 注意：这里去重了，如果不同线路有同名站点，坐标认为是一样的
                for _, row in df.iterrows():
                    if pd.notnull(row['bd_x']) and pd.notnull(row['bd_y']):
                        cache[row['stop_name']] = (row['bd_x'], row['bd_y'])
            print(f"成功加载 {len(cache)} 个站点的坐标缓存，将跳过这些站点的网络请求。")
        except Exception as e:
            print(f"加载缓存失败 (可能是文件损坏)，将重新开始: {e}")
    return cache

def fetch_stop_coordinate(session, stop_name):
    """
    搜索站点，返回 (x, y) 百度墨卡托坐标
    """
    search_wd = stop_name
    # 优化搜索关键词
    if "公交" not in stop_name and "总站" not in stop_name and "站" not in stop_name:
        search_wd += "公交站"
    
    url = SEARCH_URL.format(quote(search_wd), CITY_CODE)
    
    try:
        # 使用 session 发送请求，自带重试
        res = session.get(url, headers=HEADERS, timeout=10)
        
        # 检查内容是否可能是验证码或错误页面
        if "验证" in res.text and len(res.text) < 500:
             print("  警告：可能触发了百度验证码，请更新 Cookie 或暂停一段时间！")
             time.sleep(10)
             return None, None

        data = res.json()
        
        if "content" in data:
            first_result = data["content"][0]
            
            # 情况1: 直接有 x, y
            if "x" in first_result and "y" in first_result:
                return first_result["x"], first_result["y"]
            
            # 情况2: 只有 geo 字符串
            if "geo" in first_result:
                geo_str = first_result["geo"]
                parts = geo_str.split('|')[-1].split(';')[0].split(',')
                if len(parts) >= 2:
                    return float(parts[0]), float(parts[1])
                    
        return None, None
        
    except Exception as e:
        print(f"  {stop_name} 请求最终失败: {e}")
        return None, None

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"找不到文件夹: {INPUT_DIR}")
        return
    
    if not os.path.exists("data"):
        os.makedirs("data")

    # 1. 准备工作
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")]
    print(f"找到 {len(files)} 个线路文件，准备开始处理...")

    # 2. 加载断点续传缓存
    stop_cache = load_cache_from_csv(OUTPUT_CSV)
    
    # 全局 Session
    session = create_session()
    all_data = []

    # 3. 循环处理文件
    # 我们重新遍历所有文件，利用缓存“秒过”已抓取的，只抓未抓取的
    # 这样可以保证数据的完整性（re-build 模式）
    
    start_time = time.time()
    
    for i, filename in enumerate(files):
        # 解析线路名，例如 "1路_812.txt" -> "1路"
        line_name = filename.split('_')[0]
        file_path = os.path.join(INPUT_DIR, filename)
        
        # 读取站点
        with open(file_path, 'r', encoding='utf-8') as f:
            stops = [line.strip() for line in f if line.strip()]
        
        # 检查该线路是否所有站点都已在缓存中（如果是，则静默快速处理，不打印刷屏）
        all_cached = all(stop in stop_cache for stop in stops)
        
        if not all_cached:
            print(f"[{i+1}/{len(files)}] 正在处理: {line_name} ({len(stops)}站)...")
        
        for seq, stop_name in enumerate(stops):
            x, y = None, None
            
            # --- 步骤 A: 查缓存 ---
            if stop_name in stop_cache:
                x, y = stop_cache[stop_name]
            
            # --- 步骤 B: 抓取 (仅当缓存未命中时) ---
            else:
                # 打印日志，只显示实际发起的请求
                print(f"   Network -> 获取: {stop_name}")
                x, y = fetch_stop_coordinate(session, stop_name)
                
                if x and y:
                    stop_cache[stop_name] = (x, y) # 更新缓存
                else:
                    print(f"   未找到坐标: {stop_name}")
                
                # 只有发起网络请求后才需要延时
                time.sleep(random.uniform(0.8, 1.5))

            # --- 步骤 C: 收集数据 ---
            if x and y:
                all_data.append({
                    "line_name": line_name,
                    "stop_name": stop_name,
                    "sequence": seq + 1,
                    "bd_x": x,
                    "bd_y": y
                })

        # --- 步骤 D: 定期保存 (断点续传的关键) ---
        # 每 5 个文件保存一次，或者遇到刚抓取过数据的时候保存
        if (i + 1) % 5 == 0 or not all_cached:
            if len(all_data) > 0:
                pd.DataFrame(all_data).to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
                # print(f"   (已自动保存进度)")

    # 4. 最终保存
    df_result = pd.DataFrame(all_data)
    df_result.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    duration = time.time() - start_time
    print(f"\n全部完成！耗时: {duration:.2f}秒")
    print(f"共收集 {len(df_result)} 条数据，已保存至: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
