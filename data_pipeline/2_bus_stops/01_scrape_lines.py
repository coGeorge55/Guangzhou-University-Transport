#coding:utf-8
import requests
from bs4 import BeautifulSoup
from time import sleep
import random
import os

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    raw_dir = os.path.join(project_root, 'data', 'raw')
    
    if not os.path.exists(raw_dir):
        os.makedirs(raw_dir)
        
    file_path = os.path.join(raw_dir, 'bus_names.txt')

    try:
        firstPageUrl = 'https://www.icauto.com.cn/chuxing/bus_440100.html'

        headers = {'user-agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50'}
        res = requests.get(firstPageUrl, headers=headers, timeout=10)

        if (res.status_code == 200):
            res.encoding = 'utf-8'
            content = res.text

            soup = BeautifulSoup(content, 'html5lib')

            element_table = soup.find('table', attrs={'class': 'bordered'})

            element_tbody = element_table.find('tbody')

            busLineList = element_tbody.find_all('tr')

            # 打开文件准备写入
            with open(file_path, 'w', encoding='utf-8') as file:
                for busLine in busLineList:
                    # 提取线路名称
                    td_centers = busLine.find_all('td')
                    name = td_centers[0].text.strip()
                    
                    # 只将线路名称写入文件，每行一个
                    file.write(name + '\n')
                    
            print(f"线路名称已保存到: {file_path}")
            print(f"共保存了 {len(busLineList)} 条公交线路")
        else:
            print(firstPageUrl + " 爬取失败")

        sleep(random.uniform(3, 5))
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main()