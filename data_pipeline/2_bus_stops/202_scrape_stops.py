#coding:utf-8
import requests
from bs4 import BeautifulSoup
from time import sleep
import random
import os
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- 配置区 ---

# 获取当前脚本所在目录 (.../data_pipeline/2_bus_stops)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (.../Guangzhou-University-Transport)
project_root = os.path.dirname(os.path.dirname(current_dir))
# 设置保存目录为 data/raw/bus_stations_stops
SAVE_DIR = os.path.join(project_root, 'data', 'raw', 'bus_stations_stops')

TIMEOUT = 30  # 超时时间延长到30秒
MAX_RETRIES = 3 # 最大重试次数

# 随机 User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
]

def get_random_header():
    return {
        'user-agent': random.choice(USER_AGENTS),
        'Referer': 'https://www.icauto.com.cn/chuxing/bus_440100.html'
    }

def create_session():
    """创建一个带有重试机制的 session"""
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def clean_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def extract_line_id(url):
    match = re.search(r'bl_(\d+)', url)
    if match: return match.group(1)
    return str(random.randint(1000, 9999))

def is_valid_station_name(text):
    text = text.strip()
    if not text: return False
    if text.isdigit(): return False
    invalid_words = ["站名", "站序", "换乘", "备注", "地图", "报错", "返程", "方向", "点击查看"]
    if any(w in text for w in invalid_words): return False
    if len(text) < 2 or len(text) > 20: return False
    return True

def get_bus_stations_with_retry(session, link):
    """带重试机制的抓取函数"""
    for attempt in range(MAX_RETRIES):
        try:
            if not link.startswith('http'):
                link = 'https://www.icauto.com.cn' + link
                
            res = session.get(link, headers=get_random_header(), timeout=TIMEOUT)
            
            if res.status_code != 200:
                print(f"    (状态码 {res.status_code}，重试中...)")
                sleep(2)
                continue
                
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            stations = []
            
            # 锁定 class='bordered' 表格
            target_tables = soup.find_all('table', class_='bordered')
            
            for table in target_tables:
                if "站名" not in table.get_text() and "站序" not in table.get_text():
                    continue
                tds = table.find_all('td')
                for td in tds:
                    text = td.get_text(strip=True)
                    if is_valid_station_name(text):
                        stations.append(text)
            
            return stations

        except requests.exceptions.RequestException as e:
            print(f"尝试 {attempt+1}/{MAX_RETRIES} 失败: {e}")
            sleep(3) # 出错后多休息一会儿
            
    return [] 

if __name__ == "__main__":
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    
    # 创建全局Session
    session = create_session()
    
    try:
        print("正在获取线路列表...")
        firstPageUrl = 'https://www.icauto.com.cn/chuxing/bus_440100.html'
        
        # 列表页也可能超时，加上简单的重试
        for _ in range(3):
            try:
                res = session.get(firstPageUrl, headers=get_random_header(), timeout=TIMEOUT)
                if res.status_code == 200: break
            except:
                sleep(2)
        
        if res.status_code == 200:
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            element_table = soup.find('table', class_='bordered')
            
            if not element_table:
                print("错误：无法在主页找到线路表格。")
                exit()
                
            busLineList = element_table.find('tbody').find_all('tr')
            total = len(busLineList)
            print(f"找到 {total} 条线路，开始任务 (已开启断点续传)...")

            for index, busLine in enumerate(busLineList):
                tds = busLine.find_all('td')
                if len(tds) < 2: continue
                
                name = tds[0].text.strip()
                link_element = busLine.find('a')
                
                if link_element and link_element.has_attr('href'):
                    link = link_element['href']
                    line_id = extract_line_id(link)
                    
                    # --- 断点续传检查 ---
                    clean_name = clean_filename(name)
                    file_name = f"{clean_name}_{line_id}.txt"
                    file_path = os.path.join(SAVE_DIR, file_name)
                    
                    # 如果文件已经存在且大小不为0，说明之前抓过了，跳过
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        # 仅打印简略信息，不刷屏
                        # print(f"[{index+1}/{total}] {name} 已存在，跳过。") 
                        continue
                    
                    print(f"[{index+1}/{total}] 正在抓取: {name} ... ", end="")
                    
                    # 执行抓取
                    stations = get_bus_stations_with_retry(session, link)
                    
                    if stations:
                        # 去重 (保留顺序)
                        seen = set()
                        unique_stations = []
                        for s in stations:
                            if s not in seen:
                                unique_stations.append(s)
                                seen.add(s)
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            for station in unique_stations:
                                f.write(station + '\n')
                        print(f"成功 ({len(unique_stations)} 站)")
                    else:
                        print(f"失败 (多次重试后无数据)")
                    
                    # 每次请求后休息，避免被封
                    sleep(random.uniform(0.5, 1.2))
        else:
            print(f"主页访问失败: {res.status_code}")

    except Exception as e:
        print(f"\n严重错误: {e}")
