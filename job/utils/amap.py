from datetime import datetime
import urllib
import requests
import json
import os
import sys
root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, root)

from metagpt.config import CONFIG


class AmapGeocoding:
    def __init__(self):
        self.api_key = CONFIG.AMAP_KEY
        self.base_url = "https://restapi.amap.com/v3/geocode/geo"

    def geocode(self, address, city=None, batch=False, output="json"):
        """
        地理编码（将地址转换为经纬度）

        :param address: 需要解析的地址
        :param city: 地址所在的城市，可选
        :param batch: 是否批量请求，可选
        :param output: 输出格式，可选，默认为json
        :return: 高德地图地理编码结果
        """
        params = {
            "key": self.api_key,
            "address": address,
            "city": city,
            "batch": batch,
            "output": output
        }
        response = requests.get(self.base_url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def reverse_geocode(self, location, radius=200, extensions=None, output="json"):
        """
        逆地理编码（将经纬度转换为地址）

        :param location: 需要解析的经纬度，格式为"纬度,经度"
        :param radius: 搜索半径，可选，默认为200米
        :param extensions: 返回结果中包含的额外信息，可选
        :param output: 输出格式，可选，默认为json
        :return: 高德地图逆地理编码结果
        """
        params = {
            "key": self.api_key,
            "location": location,
            "radius": radius,
            "extensions": extensions,
            "output": output
        }
        response = requests.get(self.base_url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return None


class AmapWeather:
    def __init__(self):
        self.api_key = CONFIG.AMAP_KEY
        self.base_url = "https://restapi.amap.com/v3/weather/weatherInfo"

    def get_weather(self, city, extensions=None, output="json"):
        """
        查询天气信息

        :param city: 需要查询天气的城市名称
        :param extensions: 返回结果中包含的额外信息，如实况天气等，可选
        :param output: 输出格式，可选，默认为json
        :return: 高德地图天气查询结果
        """
        params = {
            "key": self.api_key,
            "city": city,
            "extensions": extensions,
            "output": output
        }
        response = requests.get(self.base_url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return None

        
class AmapPOISearch:
    def __init__(self):
        self.api_key = CONFIG.AMAP_KEY
        self.base_url = "https://restapi.amap.com/v3/place/text"

    def search(self, keywords, city=None, page=1, offset=10, extensions=None, output="json"):
        """
        POI搜索

        :param keywords: 搜索关键词
        :param city: 搜索的城市名称，可选
        :param page: 分页的页码，可选，默认为1
        :param offset: 分页的偏移量，可选，默认为10
        :param extensions: 返回结果中包含的额外信息，如周边搜索等，可选
        :param output: 输出格式，可选，默认为json
        :return: 高德地图POI搜索结果
        """
        params = {
            "key": self.api_key,
            "keywords": keywords,
            "city": city,
            "page": page,
            "offset": offset,
            "extensions": extensions,
            "output": output,
            "show_fields": "children,business"
        }
        response = requests.get(self.base_url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return None


# class AmapTraffic:
#     def __init__(self):
#         self.api_key = CONFIG.AMAP_KEY
#         self.base_url = "https://restapi.amap.com/v3"

#     def traffic_status(self, city, road=None, output="json"):
#         """
#         交通路况查询

#         :param city: 查询的城市名称
#         :param road: 道路名称，可选
#         :param output: 输出格式，可选，默认为json
#         :return: 高德地图交通路况查询结果
#         """
#         url = f"{self.base_url}/traffic/status"
#         params = {
#             "key": self.api_key,
#             "city": city,
#             "road": road,
#             "output": output
#         }
#         response = requests.get(url, params=params)
#         if response.status_code == 200:
#             return response.json()
#         else:
#             return None

#     def bus_line(self, city, bus_line_id, output="json"):
#         """
#         公交线路查询

#         :param city: 查询的城市名称
#         :param bus_line_id: 公交线路ID
#         :param output: 输出格式，可选，默认为json
#         :return: 高德地图公交线路查询结果
#         """
#         url = f"{self.base_url}/bus/line"
#         params = {
#             "key": self.api_key,
#             "city": city,
#             "bus_line_id": bus_line_id,
#             "output": output
#         }
#         response = requests.get(url, params=params)
#         if response.status_code == 200:
#             return response.json()
#         else:
#             return None

            

class AmapPathPlanner:
    """路径规划
    """
    def __init__(self):
        self.api_key = CONFIG.AMAP_KEY
        self.base_url = "https://restapi.amap.com/v5/direction"

    def _call_api(self, mode, origin, destination, extensions=None):
        """
        调用路径规划API

        :param mode: 路径规划模式
        :param origin: 起点坐标
        :param destination: 终点坐标
        :param city: 城市名称，可选
        :param extensions: 返回结果中包含的额外信息，可选
        :return: API返回的结果
        """
        params = {
            "key": self.api_key,
            "origin": origin,
            "destination": destination,
            "extensions": extensions or "all",
            "output": "json"
        }
        url = f"{self.base_url}/{mode}"
        response = requests.post(url, json=params)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def driving(self, origin, destination, city=None, extensions=None):
        """
        驾车路径规划

        :param origin: 起点坐标
        :param destination: 终点坐标
        :param city: 城市名称，可选
        :param extensions: 返回结果中包含的额外信息，可选
        :return: 高德地图驾车路径规划结果
        """
        return self._call_api("driving", origin, destination, city, extensions)

    def walking(self, origin, destination, city=None, extensions=None):
        """
        步行路径规划

        :param origin: 起点坐标
        :param destination: 终点坐标
        :param city: 城市名称，可选
        :param extensions: 返回结果中包含的额外信息，可选
        :return: 高德地图步行路径规划结果
        """
        return self._call_api("walking", origin, destination, city, extensions)

    def riding(self, origin, destination, city=None, extensions=None):
        """
        骑行路径规划

        :param origin: 起点坐标
        :param destination: 终点坐标
        :param city: 城市名称，可选
        :param extensions: 返回结果中包含的额外信息，可选
        :return: 高德地图骑行路径规划结果
        """
        return self._call_api("riding", origin, destination, city, extensions)

    def bus(self, origin, destination, city=None, extensions=None):
        """
        公交路径规划

        :param origin: 起点坐标
        :param destination: 终点坐标
        :param city: 城市名称，可选
        :param extensions: 返回结果中包含的额外信息，可选
        :return: 高德地图公交路径规划结果
        """
        return self._call_api("bus", origin, destination, city, extensions)
        

class TrainTicketService:
    def __init__(self, base_url="https://huoche.tuniu.com/yii.php"):
        self.base_url = base_url

    def get_tickets(self, arrival_city, departure_city="广州", departure_date=datetime.date):
        """
        获取火车票信息

        :param departure_date: 发车日期，格式为yyyy-MM-dd
        :param departure_city: 出发城市名称
        :param arrival_city: 到达城市名称
        :return: JSON格式的火车票信息
        """
        # 构建请求参数
        params = {
            'r': 'train/trainTicket/getTickets',
            'primary[departureDate]': departure_date,
            'primary[departureCityName]': departure_city,
            'primary[arrivalCityName]': arrival_city
        }

        # 发送GET请求
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()  # 如果请求失败，会抛出HTTPError异常
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP请求失败: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"请求异常: {e}")
            return None
        

if __name__ == "__main__":

    city = "百色"
    # 使用示例
    # service = TrainTicketService()
    # departure_date = "2024-01-30"
    # departure_city = "北京"
    # arrival_city = "上海"

    # # 获取火车票信息
    # tickets_info = service.get_tickets(arrival_city, departure_city, departure_date)
    # if tickets_info:
    #     print(tickets_info)
    # else:
    #     print("获取火车票信息失败。")
    
    # exit()


    # 查询北京的交通路况
    # city = "百色"
    # road = "解放街"

        
    # 使用示例
    planner = AmapPathPlanner()
    # # # 起点和终点坐标
    origin = "39.916979,116.397473"  # 北京市天安门广场
    destination = "39.989629,116.307509"  # 北京市颐和园

    # # # 进行路径规划
    # driving_result = planner.driving(origin, destination)
    # walking_result = planner.walking(origin, destination)
    # riding_result = planner.riding(origin, destination)
    # bus_result = planner.bus(origin, destination)
    driving_result = planner._call_api("driving", origin, destination)

    # # 输出结果
    # for result in [driving_result, walking_result, riding_result, bus_result]:
    for result in [driving_result]:
        if result:
            print(f"{result['route'][0]['paths'][0]['steps'][0]['instruction']}")
        else:
            print("路径规划失败")


    # # 使用示例
    # geocoding = AmapGeocoding()

    # # # 地址地理编码
    # result = geocoding.geocode(city)
    # if result:
    #     geocodes = result["geocodes"][0]
    #     print(result)
    #     print(result["infocode"])
    #     print(geocodes["formatted_address"])
    #     print(geocodes["adcode"])
    #     print(geocodes["citycode"])
    #     print(geocodes["location"])

    
    # 使用示例
    # weather = AmapWeather()

    # # # 查询北京的天气信息
    # result = weather.get_weather(city)
    # print(result)
    # if result:
    #     print(result)

    
    # 使用示例
    # poi_search = AmapPOISearch()

    # # 搜索北京的餐馆
    # keywords = ["酒店", "网吧"]
    # for keyword in keywords:
    #     result = poi_search.search(keyword, city)
    #     if result:
    #         result = [{
    #             "address": item["address"],
    #             "biz_ext": item["biz_ext"],
    #             "type": item["type"],
    #             "adname": item["adname"],
    #             "name": item["name"],
    #             "tel": item["tel"],
    #                 } for item in result["pois"]]
    #         print(result)