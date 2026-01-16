import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os

def fetch_university_list():
    url = "https://www.dxsbb.com/news/1683.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response.encoding = 'utf-8' # 确保中文不乱码
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # 定位主要表格，通常在文章内容区域
        tables = soup.find_all('table')
        
        universities = []
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if not cols:
                    continue
                # 提取文本并清洗
                cols_text = [ele.text.strip() for ele in cols]
                
                # 简单校验：列数足够且城市列包含"广州"
                # 根据DXSBB通常格式：排名, 学校名称, 省市, 城市, ...
                # 假设：学校名称在第2列（索引1），城市在第3列或第4列
                if len(cols_text) >= 3 and "广州" in cols_text:
                     # 尝试找到学校名称列（通常是第二列）
                    uni_name = cols_text[1]
                    universities.append(uni_name)
        
        # 去重处理
        universities = list(set(universities))
        
        # 写入CSV
        df = pd.DataFrame(universities, columns=["University Name"])
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 向两级找到项目根目录 (data_pipeline -> 根目录)
        project_root = os.path.dirname(os.path.dirname(current_dir))
        # 构建相对输出路径
        output_dir = os.path.join(project_root, 'data', 'raw')
        
        # 确保目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output_file = os.path.join(output_dir, "universities.csv")

        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"成功爬取 {len(universities)} 所广州高校名单，已保存至 {output_file}。")
        
    except Exception as e:
        print(f"爬取失败: {e}")

if __name__ == "__main__":
    fetch_university_list()
