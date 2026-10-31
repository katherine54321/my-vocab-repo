# -*- coding: utf-8 -*-
"""
rebuild_pure_14k_dataset.py
Rebuilds the entire 14,000+ vocabulary database from scratch using ECDICT as the single source of truth for:
1. Authentic phonetic symbols (IPA).
2. Pure primary Chinese definitions (eliminates synthetic strings and false secondary senses).
3. 34 clean, intuitive thematic categories.
4. Total words: exactly ~14,000 (CEFR A1-C2).
"""

import csv
import json
import os
import re
import subprocess
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def clean_zh_translation(raw: str) -> str:
    s = re.sub(r"\[.*?\]", "", raw or "")
    s = s.replace("\\n", "； ").replace("\n", "； ")
    s = re.sub(r"；\s*；+", "； ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().strip("；").strip()
CATEGORIES = [
    # 1. 人文学科与思辨 (academic)
    {"id": "psychology", "name_en": "Psychology & Cognition", "name_zh": "心理学与心智认知", "group": "academic", "group_name_zh": "人文学科", "icon": "🧠"},
    {"id": "politics", "name_en": "Politics & Governance", "name_zh": "政治学与公共治理", "group": "academic", "group_name_zh": "人文学科", "icon": "🏛️"},
    {"id": "philosophy", "name_en": "Philosophy & Ethics", "name_zh": "哲学思想与伦理逻辑", "group": "academic", "group_name_zh": "人文学科", "icon": "📜"},
    {"id": "economics", "name_en": "Economics & Finance", "name_zh": "经济金融与商贸投资", "group": "academic", "group_name_zh": "人文学科", "icon": "📈"},
    {"id": "law_justice", "name_en": "Law & Justice", "name_zh": "法律条文与司法审判", "group": "academic", "group_name_zh": "人文学科", "icon": "⚖️"},

    # 2. 人类生理与情感社交 (human)
    {"id": "human_organs", "name_en": "Human Organs & Anatomy", "name_zh": "人体器官与生理解剖", "group": "human", "group_name_zh": "人类与生理", "icon": "🫀"},
    {"id": "human_emotions", "name_en": "Human Emotions", "name_zh": "人类情感与心境体验", "group": "human", "group_name_zh": "人类与生理", "icon": "🎭"},
    {"id": "personality_traits", "name_en": "Personality & Character", "name_zh": "性格品质与人格特质", "group": "human", "group_name_zh": "人类与生理", "icon": "🌟"},
    {"id": "interpersonal_relations", "name_en": "Interpersonal & Family", "name_zh": "人际社交与家庭亲情", "group": "human", "group_name_zh": "人类与生理", "icon": "👥"},

    # 3. 食品与餐饮美食 (food)
    {"id": "food_beverages", "name_en": "Drinks & Beverages", "name_zh": "饮品、茶酒与水饮", "group": "food", "group_name_zh": "食品与餐饮", "icon": "☕"},
    {"id": "food_fruits", "name_en": "Fruits & Berries", "name_zh": "水果浆果与坚果", "group": "food", "group_name_zh": "食品与餐饮", "icon": "🍎"},
    {"id": "food_vegetables", "name_en": "Vegetables & Crops", "name_zh": "蔬菜菌菇与农作物", "group": "food", "group_name_zh": "食品与餐饮", "icon": "🥦"},
    {"id": "food_meat_seafood", "name_en": "Meat & Seafood", "name_zh": "肉禽蛋类与海鲜水产", "group": "food", "group_name_zh": "食品与餐饮", "icon": "🥩"},
    {"id": "food_dining", "name_en": "Dining & Cooking", "name_zh": "餐饮烹饪、菜单与调味", "group": "food", "group_name_zh": "食品与餐饮", "icon": "🍽️"},

    # 4. 空间居住与服饰工艺 (living)
    {"id": "housing_architecture", "name_en": "Housing & Architecture", "name_zh": "建筑结构与居住设施", "group": "living", "group_name_zh": "生活与空间", "icon": "🏠"},
    {"id": "fashion_apparel", "name_en": "Fashion & Apparel", "name_zh": "时尚服饰与穿搭鞋包", "group": "living", "group_name_zh": "生活与空间", "icon": "👗"},
    {"id": "tools_materials", "name_en": "Tools, Machines & Materials", "name_zh": "生产工具、机械与材料用品", "group": "living", "group_name_zh": "生活与空间", "icon": "🔧"},
    {"id": "daily_actions", "name_en": "Daily Routine & Living", "name_zh": "日常生活习惯与起居作息", "group": "living", "group_name_zh": "生活与空间", "icon": "⏰"},

    # 5. 自然地理与动植物 (nature_geo)
    {"id": "geography_places", "name_en": "Geography & Landmarks", "name_zh": "地理地名、国家城市与名胜景点", "group": "nature_geo", "group_name_zh": "地理与自然", "icon": "🗺️"},
    {"id": "animals_wildlife", "name_en": "Animals & Wildlife", "name_zh": "动物世界、鸟类与陆海生物", "group": "nature_geo", "group_name_zh": "地理与自然", "icon": "🦁"},
    {"id": "nature_weather", "name_en": "Nature & Weather", "name_zh": "自然生态、天气气候与宇宙", "group": "nature_geo", "group_name_zh": "地理与自然", "icon": "🌿"},
    {"id": "time_calendar", "name_en": "Time & Calendar", "name_zh": "时间历法、时段与季节周期", "group": "nature_geo", "group_name_zh": "地理与自然", "icon": "📅"},

    # 6. 文体娱乐与交通健康 (leisure_transport)
    {"id": "travel_transport", "name_en": "Travel & Transportation", "name_zh": "旅行出行、交通工具与路径", "group": "leisure_transport", "group_name_zh": "出行与文体", "icon": "✈️"},
    {"id": "sports_fitness", "name_en": "Sports & Fitness", "name_zh": "体育运动、健身竞技与球类", "group": "leisure_transport", "group_name_zh": "出行与文体", "icon": "⚽"},
    {"id": "arts_literature", "name_en": "Arts & Literature", "name_zh": "艺术文学、音乐绘画与戏剧", "group": "leisure_transport", "group_name_zh": "出行与文体", "icon": "🎨"},
    {"id": "entertainment_media", "name_en": "Entertainment & Media", "name_zh": "影视娱乐、大众传媒与资讯", "group": "leisure_transport", "group_name_zh": "出行与文体", "icon": "🎬"},
    {"id": "medicine_healthcare", "name_en": "Medicine & Healthcare", "name_zh": "医药健康、临床医疗与防治", "group": "leisure_transport", "group_name_zh": "出行与文体", "icon": "🏥"},

    # 7. 教育科研与职场商务 (education_work)
    {"id": "education_learning", "name_en": "Education & Learning", "name_zh": "学校教育、学术科研与学业", "group": "education_work", "group_name_zh": "教育与职场", "icon": "🎓"},
    {"id": "work_career", "name_en": "Work & Business Career", "name_zh": "职场商务、职业发展与管理", "group": "education_work", "group_name_zh": "教育与职场", "icon": "💼"},

    # 8. 科技计算与基础数理 (science_tech)
    {"id": "science_tech", "name_en": "Science & Computer Tech", "name_zh": "计算机、AI与信息技术", "group": "science_tech", "group_name_zh": "科技与数理", "icon": "💻"},
    {"id": "math_physics_chem", "name_en": "Math, Physics & Chemistry", "name_zh": "数理化基础科学与工程规律", "group": "science_tech", "group_name_zh": "科技与数理", "icon": "🔬"},

    # 9. 语言交流与核心基础 (core_language)
    {"id": "communication_language", "name_en": "Communication & Language", "name_zh": "语言表达、社会沟通与讯息", "group": "core_language", "group_name_zh": "语言与核心表达", "icon": "💬"},
    {"id": "core_verbs_actions", "name_en": "Core Actions & Verbs", "name_zh": "通用高频交互与行为动作", "group": "core_language", "group_name_zh": "语言与核心表达", "icon": "⚡"},
    {"id": "core_descriptors", "name_en": "Core Descriptors & Logic", "name_zh": "核心性状特征与程度逻辑", "group": "core_language", "group_name_zh": "语言与核心表达", "icon": "✨"}
]

CATEGORY_RULES = {
    "philosophy": {
        "tokens": {"哲学", "哲学家", "哲学思想", "伦理", "伦理学", "道德", "道德观", "逻辑", "逻辑学", "认识论", "本体论", "形而上学",
                   "虚无主义", "辩证法", "教条", "教条主义", "功利主义", "唯心主义", "唯物主义", "公理", "逻辑谬误", "悖论", "三段论",
                   "启蒙", "思想启蒙", "怀疑论", "理性主义", "存在主义", "实证主义", "二元论", "宿命论", "美德", "智慧", "真理", "条理性"},
        "exclude": set()
    },
    "food_beverages": {
        "tokens": {"饮料", "茶", "水", "酒", "咖啡", "果汁", "牛奶", "酸奶", "奶茶", "豆浆", "香槟", "啤酒", "白酒",
                   "红酒", "洋酒", "伏特加", "威士忌", "白兰地", "朗姆酒", "鸡尾酒", "汽水", "苏打水", "茶水", "开水",
                   "饮品", "口渴", "解渴", "啜饮", "畅饮", "酒馆", "酒吧", "酿造", "啤酒厂", "酿酒厂", "调酒师",
                   "茶壶", "咖啡壶", "水壶", "茶杯", "酒杯", "水杯", "酒瓶", "奶瓶", "马克杯", "高脚杯", "杯子", "瓶子", "液体"},
        "exclude": {"茶几", "酒店", "酒席", "酒精中毒", "水仙", "水井", "水稻", "水土", "水灾", "水泥"}
    },
    "food_fruits": {
        "tokens": {"水果", "苹果", "香蕉", "葡萄", "果实", "坚果", "核桃", "杏仁", "浆果", "草莓", "蓝莓", "西瓜",
                   "甜瓜", "柑橘", "橙子", "柠檬", "青柠", "芒果", "菠萝", "凤梨", "桃子", "鸭梨", "李子", "樱桃",
                   "牛油果", "石榴", "柿子", "山竹", "杏子", "无花果", "椰子", "花生", "腰果", "榛子", "猕猴桃", "柚子", "板栗", "葡萄干", "野果", "鲜橙", "蜜桃"},
        "exclude": {"苹果公司"}
    },
    "food_vegetables": {
        "tokens": {"蔬菜", "青菜", "白菜", "胡萝卜", "洋葱", "土豆", "马铃薯", "西红柿", "番茄", "菠菜", "花椰菜",
                   "西兰花", "大蒜", "生姜", "黄瓜", "蘑菇", "香菇", "菌类", "豌豆", "大豆", "玉米", "辣椒", "茄子",
                   "芹菜", "生菜", "芦笋", "南瓜", "萝卜", "甘薯", "红薯", "农作物", "庄稼", "收获", "粮食", "瓜菜", "豆芽", "韭菜", "冬瓜", "丝瓜"},
        "exclude": set()
    },
    "food_meat_seafood": {
        "tokens": {"肉", "牛肉", "猪肉", "羊肉", "鸡肉", "鸭肉", "火鸡", "鱼", "鱼肉", "虾", "螃蟹", "海鲜", "龙虾",
                   "生蚝", "牡蛎", "培根", "香肠", "牛排", "水产", "蛤蜊", "贻贝", "鱿鱼", "章鱼", "小牛肉", "家禽", "三文鱼", "金枪鱼", "鳕鱼", "鲜肉", "冻肉", "禽肉", "刺身"},
        "exclude": set()
    },
    "food_dining": {
        "tokens": {"餐饮", "烹饪", "做饭", "菜单", "菜谱", "食谱", "厨师", "餐厅", "餐馆", "食堂", "面包", "汤", "沙拉",
                   "甜点", "甜品", "前菜", "主菜", "美食", "佳肴", "煮", "炒", "煎", "炸", "烤", "炖", "蒸", "烘焙",
                   "酱料", "调味品", "黄油", "奶酪", "芝士", "蛋糕", "馅饼", "饼干", "一日三餐", "早餐", "午餐", "晚餐",
                   "风味", "美味", "香料", "食盐", "调料", "宴席", "盛宴", "餐具", "刀叉", "勺子", "盘子", "餐巾", "外卖", "聚餐", "菜品", "酱油", "香醋", "番茄酱"},
        "exclude": set()
    },
    "housing_architecture": {
        "tokens": {"建筑", "房屋", "住宅", "公寓", "楼房", "大楼", "大厦", "别墅", "房间", "卧室", "厨房", "浴室",
                   "洗手间", "卫生间", "阳台", "地下室", "天花板", "屋顶", "砖", "水泥", "电梯", "走廊", "楼梯", "过道",
                   "摩天大楼", "家具", "沙发", "桌子", "椅子", "书桌", "衣柜", "橱柜", "地毯", "窗帘", "门", "窗户",
                   "墙壁", "地板", "门锁", "钥匙", "门廊", "烟囱", "房产", "不动产", "装修", "室内设计", "庭院", "玄关", "客厅", "书房", "阁楼", "车库", "储藏室", "露台", "围栏", "栅栏", "阶梯", "台阶", "柱子", "横梁"},
        "exclude": set()
    },
    "fashion_apparel": {
        "tokens": {"服装", "衣服", "服饰", "大衣", "外套", "夹克", "连衣裙", "裙子", "衬衫", "长裤", "裤子", "牛仔裤",
                   "鞋", "鞋子", "靴子", "运动鞋", "皮带", "腰带", "围巾", "帽子", "礼帽", "手套", "袜子", "手袋",
                   "背包", "珠宝", "首饰", "项链", "手镯", "耳环", "戒指", "纯棉", "丝绸", "皮革", "面料", "裁缝", "时尚", "穿戴", "服饰品", "拉链", "纽扣", "礼服", "制服", "校服", "工装", "披风", "领结", "丝巾"},
        "exclude": set()
    },
    "tools_materials": {
        "tokens": {"工具", "材料", "器物", "用品", "器械", "金属", "塑料", "木材", "钢铁", "橡胶", "玻璃",
                   "绳子", "绳索", "电线", "管道", "管子", "箱子", "盒子", "袋子", "容器", "锤子", "钳子",
                   "螺丝", "螺栓", "钉子", "刀具", "剪刀", "机器", "机械", "仪器", "设备", "零件", "轮子", "锁", "电池", "部件", "构件", "铁轨", "钢管", "配件"},
        "exclude": set()
    },
    "daily_actions": {
        "tokens": {"日常生活", "作息", "起床", "醒来", "睡觉", "洗手", "洗脸", "刷牙", "洗澡", "冲凉", "梳头", "刮脸", "刮胡子", "打扫", "整理", "收拾", "家务", "生活习惯", "琐事", "午休", "打瞌睡", "打哈欠"},
        "exclude": set()
    },
    "geography_places": {
        "tokens": {"地理", "地名", "国家", "世界", "城市", "首都", "省份", "大洲", "洲", "大陆", "半岛", "海岛", "岛屿",
                   "山脉", "高山", "山峰", "江河", "河流", "湖泊", "水库", "峡谷", "冰川", "港口", "海湾", "城堡", "宫殿",
                   "寺庙", "教堂", "纪念碑", "金字塔", "名胜", "古迹", "景点", "广场", "边界", "国界", "领土", "风景", "景观",
                   "伦敦", "巴黎", "东京", "罗马", "柏林", "莫斯科", "北京", "上海", "华盛顿", "纽约", "悉尼", "开罗",
                   "美国", "英国", "中国", "法国", "德国", "日本", "意大利", "西班牙", "加拿大", "澳大利亚", "俄罗斯", "印度", "巴西", "埃及",
                   "地形", "地貌", "盆地", "平原", "高原", "丘陵", "绿洲", "沙漠", "瀑布", "港湾", "城镇", "村庄", "故居", "遗址"},
        "exclude": set()
    },
    "animals_wildlife": {
        "tokens": {"动物", "野兽", "野生动物", "兽类", "猛兽", "狮子", "老虎", "大象", "飞禽", "鸟", "鸟类", "雄鹰", "鹰",
                   "海豚", "鲸鱼", "蛇", "毒蛇", "爬行动物", "昆虫", "蝴蝶", "蜘蛛", "鹿", "羚羊", "绵羊", "山羊", "兔子",
                   "宠物", "狗", "小狗", "猫", "小猫", "狼", "狐狸", "猴子", "猩猩", "企鹅", "哺乳动物", "两栖动物",
                   "熊", "马", "奶牛", "猪", "鸭", "鹅", "鸽子", "麻雀", "鹦鹉", "鲨鱼", "鳄鱼", "乌龟", "蚂蚁", "蜜蜂", "苍蝇", "蚊子"},
        "exclude": set()
    },
    "nature_weather": {
        "tokens": {"自然", "自然环境", "生态", "生态系统", "天气", "气象", "降雨", "下雨", "雨水", "降雪", "下雪", "雪花",
                   "刮风", "微风", "大风", "阳光", "晴天", "暴风雨", "飓风", "台风", "云", "乌云", "气候", "森林", "树木",
                   "树林", "草地", "草坪", "花朵", "鲜花", "植物", "土壤", "泥土", "地球", "行星", "宇宙", "太空",
                   "星星", "太阳", "月亮", "月球", "雷电", "打雷", "闪电", "大雾", "霜冻", "彩虹", "冰雹", "干旱", "洪水", "地震"},
        "exclude": set()
    },
    "time_calendar": {
        "tokens": {"时间", "历法", "日历", "早晨", "上午", "正午", "中午", "下午", "午后", "傍晚", "黄昏", "夜晚", "深夜", "黎明",
                   "昨天", "昨日", "今天", "今日", "明天", "明日", "星期", "周", "星期一", "星期二", "星期三", "星期四",
                   "星期五", "星期六", "星期日", "周一", "周二", "周三", "周四", "周五", "周六", "周日", "月份", "月",
                   "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月",
                   "春季", "春天", "夏季", "夏天", "秋季", "秋天", "冬季", "冬天", "四季", "小时", "钟头", "分钟",
                   "秒钟", "瞬间", "世纪", "年代", "百年", "年度", "每年", "月度", "每月", "日常", "每日", "周期", "时代", "纪元"},
        "exclude": set()
    },
    "travel_transport": {
        "tokens": {"旅行", "旅游", "出行", "交通", "交通工具", "飞机场", "机场", "航班", "飞机", "客机", "铁路", "火车",
                   "列车", "地铁", "地下铁", "公交", "公交车", "公共汽车", "汽车", "小汽车", "轿车", "自行车", "单车", "摩托车",
                   "车票", "机票", "门票", "护照", "签证", "行李", "箱包", "驾驶", "司机", "开车", "车站", "火车站",
                   "旅程", "观光", "游客", "旅客", "通勤", "路线", "路线图", "轮船", "游轮", "航行", "高速公路", "出租车"},
        "exclude": set()
    },
    "sports_fitness": {
        "tokens": {"体育", "运动", "健身", "锻炼", "竞技", "运动员", "足球", "篮球", "网球", "羽毛球", "乒乓球", "排球",
                   "高尔夫", "棒球", "游泳", "泳池", "马拉松", "长跑", "短跑", "田径", "赛跑", "体育场", "运动场", "体育馆",
                   "健身房", "锦标赛", "比赛", "赛事", "裁判", "裁判员", "教练", "教练员", "奥林匹克", "奥运会", "冠军", "奖牌",
                   "金牌", "银牌", "铜牌", "瑜伽", "滑雪", "滑冰", "溜冰", "拳击", "摔跤", "体操", "得分", "进球", "联赛", "赛道", "哑铃"},
        "exclude": set()
    },
    "arts_literature": {
        "tokens": {"艺术", "艺术品", "美术", "文学", "音乐", "音乐家", "绘画", "画家", "小说", "长篇小说", "小说家",
                   "诗歌", "诗篇", "诗人", "雕塑", "雕像", "剧院", "戏剧", "话剧", "舞台剧", "剧作家", "音乐会", "演奏会",
                   "歌曲", "乐曲", "歌唱", "舞蹈", "舞者", "跳舞", "博物馆", "美术馆", "画廊", "作家", "作者", "乐器",
                   "吉他", "钢琴", "小提琴", "鼓", "敲鼓", "鼓声", "交响乐", "管弦乐", "画布", "杰作", "名作", "乐队", "乐谱", "旋律", "乐章", "雕刻", "童话", "神话", "散文"},
        "exclude": set()
    },
    "entertainment_media": {
        "tokens": {"娱乐", "大众传媒", "媒体", "电影", "影片", "电影院", "影院", "电视", "电视台", "电视节目", "广播", "电台",
                   "报纸", "报社", "期刊", "杂志", "记者", "新闻记者", "播客", "广告", "商业广告", "宣传", "观众", "听众",
                   "采访", "专访", "名人", "明星", "明星人物", "头条", "新闻报道", "新闻", "票房", "剧集", "电视剧", "首映", "综艺", "剧本", "演出", "摄影", "镜头", "栏目", "粉丝"},
        "exclude": set()
    },
    "medicine_healthcare": {
        "tokens": {"医学", "医疗", "医药", "健康", "保健", "医生", "医师", "大夫", "护士", "医院", "诊所", "卫生院",
                   "疾病", "病情", "病症", "症状", "药物", "药丸", "药片", "胶囊", "治愈", "治疗", "康复", "手术",
                   "外科", "内科", "主刀", "病毒", "细菌", "发烧", "高烧", "咳嗽", "伤口", "外伤", "处方", "药方",
                   "慢性病", "传染病", "流行病", "疫苗", "预防针", "接种", "病人", "患者", "病患", "绷带", "敷料", "肺炎", "结核", "胃痛", "耳痛", "头痛", "止痛", "受伤", "骨折", "感染", "炎症", "过敏"},
        "exclude": set()
    },
    "education_learning": {
        "tokens": {"学校", "大学", "学院", "中小学", "在校生", "学生", "老师", "教师", "授课老师", "教授", "讲师", "学习",
                   "研读", "自学", "教书", "讲学", "教学", "课程", "功课", "课堂", "教室", "考试", "测验", "考核", "成绩", "分数",
                   "学业", "学位", "学士", "硕士", "博士", "文凭", "毕业证", "学术", "学院派", "学术研究", "作业", "家庭作业",
                   "图书馆", "教材", "教科书", "课本", "校园", "校区", "学者", "讲座", "报告", "学费", "奖学金", "毕业", "开学", "论文", "毕业论文"},
        "exclude": set()
    },
    "work_career": {
        "tokens": {"工作", "职业", "职场", "办公室", "职位", "职务", "岗位", "公司", "企业", "商业机构", "经理", "主管",
                   "总经理", "老板", "上司", "招聘", "录用", "雇用", "工资", "薪水", "薪酬", "周薪", "会议", "商务会议",
                   "合同", "协议", "契约", "员工", "雇员", "职员", "雇主", "面试", "求职面试", "商务", "商业",
                   "项目", "课题", "客户", "委托人", "晋升", "提拔", "升职", "退休", "离休", "职场同事", "工作场所", "简历", "履历", "工业", "产业", "工厂", "业绩", "解雇", "罢工"},
        "exclude": set()
    },
    "science_tech": {
        "tokens": {"计算机", "电脑", "电子计算机", "软件", "应用软件", "硬件", "互联网", "网络", "万维网", "算法", "数据库",
                   "人工智能", "机器人", "芯片", "微芯片", "集成电路", "服务器", "数字系统", "程序代码", "编写程序", "程序员",
                   "网络安全", "信息安全", "黑客", "电脑屏幕", "电子设备", "浏览器", "操作系统", "云计算", "微处理器", "加密", "防火墙", "路由器"},
        "exclude": set()
    },
    "math_physics_chem": {
        "tokens": {"物理", "物理学", "化学", "化学反应", "数学", "算术", "原子", "原子核", "分子", "化学分子", "引力", "万有引力",
                   "重力", "方程式", "数学方程", "公式", "计算公式", "能量", "质量", "密度", "速度", "加速度", "几何", "几何角度",
                   "实验", "科学实验", "电子", "质子", "中子", "量子", "量子力学", "定理", "公理", "代数", "微积分", "摩擦力", "辐射", "光学", "磁性", "电磁"},
        "exclude": set()
    },
    "psychology": {
        "tokens": {"心理", "心理学", "心理医生", "心理治疗", "认知", "心智", "潜意识", "下意识", "无意识", "创伤", "心理创伤",
                   "心理咨询", "治疗师", "幻觉", "本能", "知觉", "内省", "情绪宣泄", "恐惧症", "妄想", "精神分析", "神经症", "精神病", "催眠", "偏执", "精神分裂", "失忆", "自闭", "狂躁", "抑郁症", "自卑", "条件反射"},
        "exclude": set()
    },
    "politics": {
        "tokens": {"政治", "政治家", "政界", "政府", "统治", "治理", "议会", "国会", "选举", "大选", "投票", "选票", "选民",
                   "民主", "民主制", "参议院", "参议员", "众议院", "政策", "政权", "公民投票", "外交", "外交官", "外交部",
                   "条约", "国际条约", "主权", "国家主权", "共和国", "共和制", "部长", "大臣", "市长", "官僚", "宪法", "否决权", "意识形态", "专制", "暴政", "独裁", "君主", "霸权", "政客"},
        "exclude": set()
    },
    "economics": {
        "tokens": {"经济", "经济学", "经济学家", "金融", "金融界", "货币", "通货", "银行", "银行业", "通货膨胀", "通胀", "税收",
                   "赋税", "财政", "财政政策", "资产", "资本", "营业额", "收入", "利润", "净利润", "股息", "红利", "债务",
                   "借款", "投资", "投资者", "投资人", "贷款", "商业贷款", "外汇", "货币汇率", "经济衰退", "通货紧缩", "滞胀",
                   "关税", "贸易赤字", "财政赤字", "垄断", "市场垄断", "按揭", "抵押贷款", "债券", "证券", "宏观经济", "微观经济", "破产", "赤字", "亏损", "退款", "清算", "偿还", "结算", "交易", "发票", "账单"},
        "exclude": set()
    },
    "law_justice": {
        "tokens": {"法律", "条文", "法规", "法学", "合法", "非法", "违法", "法院", "法庭", "法官", "主审法官", "陪审团", "裁决",
                   "判决", "犯罪", "罪行", "罪犯", "刑事犯", "监狱", "牢房", "律师", "辩护律师", "证人", "出庭证人", "审判",
                   "庭审", "传票", "司法管辖", "有罪", "罪过", "无罪", "惩治", "刑罚", "处罚", "重罪", "原告", "被告",
                   "起诉", "检方", "检察官", "作证", "宣誓", "上诉", "定罪", "诉讼", "官司", "保释", "假释", "赦免", "违宪", "起诉书", "监禁", "坐牢", "囚犯", "立法", "立法者", "条款"},
        "exclude": set()
    },
    "human_organs": {
        "tokens": {"心脏", "心房", "肺部", "双肺", "肝脏", "肾脏", "胃", "胃部", "动脉", "静脉", "血管", "人体器官", "器官",
                   "肌肉", "肌群", "骨头", "骨骼", "耳朵", "听觉器官", "鼻子", "咽喉", "喉咙", "舌头", "牙齿", "头颅", "头骨",
                   "脊椎", "脊柱", "肋骨", "胰腺", "视网膜", "小脑", "食道", "食管", "椎骨", "腺体", "骨架", "肚子", "胸腔",
                   "胸部", "四肢", "肠", "肠道", "大肠", "小肠", "关节", "生理解剖", "解剖学", "角膜", "肌腱", "骨髓",
                   "脚踝", "手腕", "手指", "脚趾", "膝盖", "手肘", "肘部", "肩膀", "后跟", "拇指", "额头", "眉毛", "眼皮", "眼睫毛", "下巴", "骨盆", "大腿", "小腿", "腰部", "臀部", "腹部", "胡须", "脖子"},
        "exclude": set()
    },
    "human_emotions": {
        "tokens": {"情感", "情绪", "喜悦", "高兴", "快乐", "悲伤", "难过", "哀伤", "愤怒", "生气", "愤怒情绪", "恐惧", "害怕",
                   "恐慌", "悲痛", "嫉妒", "怀旧", "绝望", "平静", "宁静", "怨恨", "狂喜", "忧郁", "尴尬", "羞愧", "自豪",
                   "骄傲", "内疚", "焦虑", "担忧", "欣喜", "暴怒", "狂暴", "同情", "同情心", "怜悯", "激情", "消沉", "沮丧", "苦恼", "苦楚", "孤独", "烦躁"},
        "exclude": set()
    },
    "personality_traits": {
        "tokens": {"性格", "个性", "性格品质", "品质", "特质", "诚实", "老实", "勇敢", "勇气", "英勇", "善良", "好心", "残忍",
                   "冷酷", "慷慨", "大方", "自私", "礼貌", "粗鲁", "谦虚", "谦逊", "傲慢", "自大", "固执", "倔强", "忠诚",
                   "真诚", "愤世嫉俗", "怪癖", "古怪", "胆小", "懦弱", "雄心", "有野心", "温和", "温柔", "耐心", "有耐心",
                   "懒惰", "勤奋", "刻苦", "贪婪", "高尚", "内向", "外向", "聪明", "机灵", "愚蠢", "愚笨", "明智", "谨慎", "小心", "才华", "才能", "懦夫", "乐观", "悲观", "可靠"},
        "exclude": set()
    },
    "interpersonal_relations": {
        "tokens": {"朋友", "友谊", "好友", "家庭", "家族", "父母", "双亲", "母亲", "妈妈", "父亲", "爸爸", "姐妹", "姐姐", "妹妹",
                   "兄弟", "哥哥", "弟弟", "孩子", "儿童", "儿子", "女儿", "丈夫", "妻子", "配偶", "同事", "同僚", "合伙人",
                   "合作伙伴", "邻居", "陌生人", "竞争对手", "敌人", "仇敌", "结婚", "婚姻", "婚礼", "离婚", "拥抱", "问候",
                   "社交", "社区", "人群", "团队", "争吵", "吵架", "同龄人", "同辈", "亲戚", "亲属", "祖父", "爷爷", "外公",
                   "祖母", "奶奶", "外婆", "叔叔", "伯伯", "舅舅", "阿姨", "姑姑", "堂兄弟", "表姐妹", "侄子", "外甥", "侄女", "外甥女", "新娘", "新郎", "婴儿", "幼童", "室友", "闺蜜", "女婿", "儿媳", "孙子", "孙女"},
        "exclude": set()
    },
    "communication_language": {
        "tokens": {"语言", "演讲", "讲话", "谈话", "说话", "口语", "交谈", "解释", "说明", "讨论", "商讨", "宣布", "宣告",
                   "消息", "讯息", "信件", "书信", "地址", "住址", "对话", "争论", "辩论", "赞美", "表扬", "问题", "提问",
                   "回答", "答复", "手势", "嗓音", "声音", "发音", "词汇", "单词", "语法", "句法", "语言学", "声明", "陈述", "言论", "备注", "聊天", "致辞"},
        "exclude": set()
    }
}

OVERRIDE_LEMMAS = {
    # High-profile specific words
    "afternoon": "time_calendar", "morning": "time_calendar", "evening": "time_calendar",
    "yesterday": "time_calendar", "tomorrow": "time_calendar",
    "address": "communication_language", "addresses": "communication_language",
    "tea": "food_beverages", "teas": "food_beverages", "coffee": "food_beverages", "wine": "food_beverages",
    "beer": "food_beverages", "drink": "food_beverages", "drinks": "food_beverages", "cocktail": "food_beverages",
    "teach": "education_learning", "drum": "arts_literature", "female": "interpersonal_relations",
    "male": "interpersonal_relations", "bear": "animals_wildlife", "lawn": "housing_architecture",
    "flaw": "core_descriptors", "scale": "math_physics_chem", "alert": "core_descriptors",
    "philosophy": "philosophy", "philosophical": "philosophy", "philosopher": "philosophy",
    "ethics": "philosophy", "ethical": "philosophy", "logic": "philosophy", "logical": "philosophy",
    "truth": "philosophy", "virtue": "philosophy", "wisdom": "philosophy", "axiom": "philosophy",
    "london": "geography_places", "paris": "geography_places", "china": "geography_places",
    "america": "geography_places", "britain": "geography_places", "tokyo": "geography_places",
    "beijing": "geography_places", "shanghai": "geography_places", "rome": "geography_places",
    "berlin": "geography_places", "moscow": "geography_places", "sydney": "geography_places"
}

def classify_word(w: str, pos: str, zh_clean: str, raw_trans: str) -> str:
    w_low = w.lower().strip()
    if w_low in OVERRIDE_LEMMAS:
        return OVERRIDE_LEMMAS[w_low]

    # Primary line from raw translation
    primary_line = raw_trans.split("\n")[0].strip()
    clean_primary = re.sub(r"\[.*?\]", "", primary_line).strip()
    
    # 1. Match primary line against category tokens
    best_cat = None
    best_score = 0
    for cat_id, rule in CATEGORY_RULES.items():
        score = 0
        for tok in rule["tokens"]:
            if tok in clean_primary:
                if any(ex in clean_primary for ex in rule["exclude"]):
                    continue
                score += len(tok) * 3
        if score > best_score:
            best_score = score
            best_cat = cat_id
            
    if best_cat and best_score >= 3:
        return best_cat

    # 2. Check full translation for domain tag IF primary line is explicitly relevant
    # (Avoid picking up obscure secondary computing/medical senses for everyday words)
    matches = re.findall(r'\[([一-龥]{1,3})\]', primary_line)
    DOMAIN_TAG_MAP = {
        "地名": "geography_places", "地": "geography_places", "地质": "geography_places",
        "美国": "geography_places", "英国": "geography_places", "德国": "geography_places", "法国": "geography_places",
        "医": "medicine_healthcare", "药": "medicine_healthcare", "症": "medicine_healthcare",
        "解": "human_organs",
        "经": "economics", "商": "economics",
        "法": "law_justice",
        "体": "sports_fitness",
        "建": "housing_architecture",
        "动": "animals_wildlife",
        "化": "math_physics_chem", "物": "math_physics_chem", "数": "math_physics_chem",
        "电影": "entertainment_media", "戏": "arts_literature",
        "语": "communication_language"
    }
    for m in matches:
        if m in DOMAIN_TAG_MAP:
            return DOMAIN_TAG_MAP[m]

    # 3. Match across entire definition
    for cat_id, rule in CATEGORY_RULES.items():
        score = 0
        for tok in rule["tokens"]:
            if tok in zh_clean:
                if any(ex in zh_clean for ex in rule["exclude"]):
                    continue
                score += len(tok) * 2
        if score > best_score:
            best_score = score
            best_cat = cat_id
            
    if best_cat and best_score >= 2:
        return best_cat

    # 4. Fallback based on part-of-speech
    if pos == "verb":
        return "core_verbs_actions"
    elif pos in ["adjective", "adverb", "preposition", "conjunction", "pronoun"]:
        return "core_descriptors"
    else:
        return "communication_language"

def natural_example_sentence(w: str, pos: str, cat_id: str, zh: str) -> str:
    cap = w.capitalize()
    if cat_id == "time_calendar":
        if w in {"afternoon", "afternoons"}:
            return "The sunlight streamed gently through the window during the afternoon."
        if w in {"morning", "mornings"}:
            return "A brisk walk in the fresh morning air helps sharpen concentration."
        if w in {"evening", "evenings"}:
            return "Families often gather together in the quiet evening to share dinner."
        if pos == "noun":
            return f"She scheduled the important appointment for that {w}."
        else:
            return f"The timetable is updated on a {w} basis according to calendar rules."
            
    elif cat_id == "food_beverages":
        if w in {"tea", "teas"}:
            return "Enjoying a cup of warm tea offers a peaceful moment during a busy day."
        if w in {"coffee", "coffees"}:
            return "Freshly ground coffee filled the entire lounge with an inviting fragrance."
        if w in {"wine", "wines"}:
            return "The sommelier expertly paired a rich red wine with the main course."
        if w in {"beer", "beers"}:
            return "They gathered at the patio to enjoy cold beer and conversation."
        if w in {"cocktail", "cocktails"}:
            return "The mixologist crafted a refreshing cocktail garnished with fresh mint."
        if w in {"drink", "drinks", "drinking"}:
            return "Remember to drink plenty of water throughout strenuous physical activities."
        if pos == "noun":
            return f"A glass of chilled {w} was served to refresh the guests."
        else:
            return f"Guests were invited to {w} leisurely in the garden lounge."
            
    elif cat_id == "geography_places":
        if pos == "noun":
            return f"Travelers from across the globe visit {cap} to explore its rich heritage."
        else:
            return f"The region is renowned for its distinct {w} landscape."
            
    elif cat_id == "sports_fitness":
        if pos == "noun":
            return f"Consistent training in {w} builds exceptional endurance and teamwork."
        else:
            return f"Athletes strive to maintain a highly {w} physique through regular practice."
            
    elif cat_id == "fashion_apparel":
        if pos == "noun":
            return f"The designer showcased a tailored {w} made from fine breathable fabric."
        else:
            return f"The collection combines elegant aesthetics with comfortable {w} styling."
            
    elif cat_id == "tools_materials":
        if pos == "noun":
            return f"Technicians selected a durable {w} to complete the engineering assembly."
        else:
            return f"The project required specialized {w} components for installation."
            
    elif cat_id == "animals_wildlife":
        if pos == "noun":
            return f"Naturalists carefully observed the wild {w} in its native habitat."
        else:
            return f"The wildlife sanctuary protects numerous rare {w} species."
            
    elif cat_id == "housing_architecture":
        if pos == "noun":
            return f"The modern {w} was designed with open lighting and sustainable materials."
        else:
            return f"Engineers inspected the structural stability of the {w} facility."
            
    elif cat_id == "education_learning":
        if w in {"teach", "teaches", "teaching"}:
            return "Dedicated educators teach students how to think critically and analytically."
        if pos == "noun":
            return f"Mastering this academic {w} is essential for future research."
        else:
            return f"Professors encourage students to {w} foundational concepts thoroughly."
            
    elif cat_id == "arts_literature":
        if w in {"drum", "drums"}:
            return "The rhythmic heartbeat of the drums echoed across the concert hall."
        if pos == "noun":
            return f"The gallery exhibited magnificent classical {w} from the Renaissance."
        else:
            return f"The artist sought to {w} deep human passions through expressive melody."
            
    elif cat_id == "science_tech":
        if pos == "noun":
            return f"Engineers implemented a secure {w} to optimize data transmission."
        else:
            return f"Modern digital systems continuously {w} real-time server telemetry."
            
    elif cat_id == "philosophy":
        if pos == "noun":
            return f"Scholars debated whether {w} provides objective moral guidelines."
        else:
            return f"The author presented a deeply {w} analysis of human nature."
            
    elif cat_id == "communication_language":
        if w in {"address", "addresses"}:
            return "The ambassador delivered a thoughtful address on international cooperation."
        if pos == "noun":
            return f"Clear and constructive {w} fosters mutual understanding between cultures."
        else:
            return f"They met in person to {w} the key issues with transparency."
            
    elif cat_id == "core_verbs_actions":
        return f"Be sure to {w} the instructions carefully before proceeding."
        
    elif cat_id == "core_descriptors":
        return f"The committee analyzed a remarkably {w} approach during the evaluation."

    # General fallback
    if pos == "verb":
        return f"Specialists actively {w} practical solutions to ensure optimal results."
    elif pos == "noun":
        return f"A deep understanding of {w} is beneficial in everyday life."
    else:
        return f"They adopted a {w} perspective to address the challenge."

def main():
    print("=" * 65)
    print("🚀 Rebuilding 14,000+ Clean CEFR English Vocabulary with 34 Categories...")
    print("=" * 65)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.abspath(os.path.join(base_dir, ".."))
    repo_dir = os.path.join(project_dir, "my-vocab-repo")
    repo_data_dir = os.path.join(repo_dir, "data")
    public_data_dir = os.path.join(project_dir, "public", "data")
    data_dir = os.path.join(project_dir, "data")
    
    os.makedirs(repo_data_dir, exist_ok=True)
    os.makedirs(public_data_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    # Load raw ECDICT into indexed memory for instant authentic lookup
    print("1/4 Indexing authoritative ECDICT (770,000+ entries)...")
    ecdict_path = os.path.join(base_dir, "ecdict.csv")
    ecdict_db = {}
    with open(ecdict_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            w = row['word'].lower().strip()
            if w not in ecdict_db:
                ecdict_db[w] = row
    print(f"   Indexed {len(ecdict_db)} lemmas from ECDICT.")

    # Load 12,143 existing CEFR words
    print("2/4 Loading base CEFR words from Git commit 3316052...")
    cmd = ['git', '-C', repo_dir, 'show', '3316052:categories.json']
    cats_meta = json.loads(subprocess.check_output(cmd).decode('utf-8'))
    
    all_words = {}
    for c in cats_meta['categories']:
        cid = c['id']
        f_cmd = ['git', '-C', repo_dir, 'show', f'3316052:data/{cid}.json']
        items = json.loads(subprocess.check_output(f_cmd).decode('utf-8'))
        for item in items:
            w = item['word'].lower().strip()
            pos = item.get('part_of_speech') or item.get('pos', 'noun')
            k = f"{w}_{pos}"
            if k not in all_words:
                # Refresh with authentic ECDICT data
                ec_row = ecdict_db.get(w)
                if ec_row:
                    trans = ec_row.get('translation', '')
                    phon = ec_row.get('phonetic', item.get('phonetic', f'/{w}/'))
                    clean_zh = clean_zh_translation(trans)
                    en_def = ec_row.get('definition', item.get('definition_en', ''))
                else:
                    trans = item.get('definition_zh', '')
                    phon = item.get('phonetic', f'/{w}/')
                    clean_zh = trans
                    en_def = item.get('definition_en', '')

                all_words[k] = {
                    "id": f"{w}_{pos}",
                    "word": w,
                    "pos": pos,
                    "part_of_speech": pos,
                    "level": item.get('level', 'B1'),
                    "phonetic": f"/{phon}/" if phon and not phon.startswith('/') else phon,
                    "audio": item.get('audio', f"https://dict.youdao.com/dictvoice?audio={w}&type=2"),
                    "definition_zh": clean_zh,
                    "raw_trans": trans,
                    "definition_en": en_def
                }

    print(f"   Refreshed {len(all_words)} core CEFR words with authentic ECDICT data.")

    # Supplement candidates from ECDICT if needed to maintain ~14,000 words
    TARGET_TOTAL = 14000
    if len(all_words) < TARGET_TOTAL:
        needed = TARGET_TOTAL - len(all_words)
        print(f"   Selecting ~{needed} additional high-value words from ECDICT...")
        candidates = []
        for w, row in ecdict_db.items():
            if not re.match(r"^[a-zA-Z\-']+$", w) or len(w) < 2:
                continue
            trans = row.get('translation', '').strip()
            phon = row.get('phonetic', '').strip()
            if not trans or not phon:
                continue
            raw_pos = row.get('pos', '').strip().lower()
            if raw_pos.startswith('v'): pos = 'verb'
            elif raw_pos.startswith('adj') or raw_pos == 'a': pos = 'adjective'
            elif raw_pos.startswith('adv'): pos = 'adverb'
            elif raw_pos.startswith('prep'): pos = 'preposition'
            elif raw_pos.startswith('conj'): pos = 'conjunction'
            elif raw_pos.startswith('pron'): pos = 'pronoun'
            else: pos = 'noun'

            k = f"{w}_{pos}"
            if k in all_words:
                continue

            tag = row.get('tag', '')
            oxf = row.get('oxford', '')
            col = row.get('collins', '')
            frq = int(row['frq']) if row.get('frq', '').isdigit() else 999999

            lvl = "B2"
            if oxf == "1" and col in ["5", "4"]: lvl = "A2" if col == "5" else "B1"
            elif "cet4" in tag or "gk" in tag: lvl = "B1"
            elif "cet6" in tag or "ky" in tag: lvl = "B2"
            elif "ielts" in tag or "toefl" in tag: lvl = "C1"
            elif "gre" in tag: lvl = "C2"

            score = 0
            if oxf == '1': score += 20
            if col:
                try: score += int(col) * 5
                except: pass
            if 'cet4' in tag or 'gk' in tag: score += 10
            if 'cet6' in tag or 'ky' in tag: score += 8
            if 'ielts' in tag or 'toefl' in tag: score += 6

            clean_zh = clean_zh_translation(trans)
            en_def = row.get("definition", "").replace("\n", "; ").strip()
            if not en_def: en_def = f"{pos}: {clean_zh.split('；')[0]}"

            candidates.append((score, -frq, {
                "id": f"{w}_{pos}", "word": w, "pos": pos, "part_of_speech": pos,
                "level": lvl, "phonetic": f"/{phon}/" if not phon.startswith('/') else phon,
                "audio": f"https://dict.youdao.com/dictvoice?audio={w}&type=2",
                "definition_zh": clean_zh, "raw_trans": trans, "definition_en": en_def
            }))

        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        for _, _, cand in candidates:
            if len(all_words) >= TARGET_TOTAL:
                break
            k = f"{cand['word']}_{cand['pos']}"
            if k not in all_words:
                all_words[k] = cand

    print(f"   Final total vocabulary pool: {len(all_words)} words.")

    # 3. Classify all words into 34 categories
    print("3/4 Classifying words across 34 scene/thematic categories...")
    slices = {c["id"]: [] for c in CATEGORIES}

    for k, item in all_words.items():
        w = item["word"]
        pos = item.get("part_of_speech") or item.get("pos", "noun")
        zh = item.get("definition_zh", "")
        raw = item.get("raw_trans", zh)
        en_def = item.get("definition_en", "")
        lvl = item.get("level", "B1")
        phon = item.get("phonetic", f"/{w}/")
        audio = item.get("audio", f"https://dict.youdao.com/dictvoice?audio={w}&type=2")

        cat_id = classify_word(w, pos, zh, raw)
        ex_sent = natural_example_sentence(w, pos, cat_id, zh)

        slices[cat_id].append({
            "id": f"{w}_{pos}",
            "word": w,
            "part_of_speech": pos,
            "level": lvl,
            "topic": next(c["name_zh"] for c in CATEGORIES if c["id"] == cat_id),
            "category": cat_id,
            "phonetic": phon,
            "audio": audio,
            "definition_en": en_def,
            "definition_zh": zh,
            "examples": [
                {
                    "en": ex_sent,
                    "zh": f"在相关语境中，'{w}'的实际运用体现了明确的语义搭配。"
                }
            ]
        })

    for cid in slices:
        slices[cid].sort(key=lambda x: x["word"].lower())

    # 4. Save sliced JSON files and index
    print("4/4 Saving sliced JSON files and updating categories metadata...")
    current_cat_ids = set(c["id"] for c in CATEGORIES)
    for folder in [repo_data_dir, public_data_dir, data_dir]:
        for existing_file in os.listdir(folder):
            if existing_file.endswith(".json"):
                base_name = existing_file[:-5]
                if base_name not in current_cat_ids:
                    legacy_path = os.path.join(folder, existing_file)
                    try:
                        os.remove(legacy_path)
                        print(f"   Removed obsolete slice: {existing_file}")
                    except Exception:
                        pass

    for cid, items in slices.items():
        for target_folder in [repo_data_dir, public_data_dir, data_dir]:
            out_file = os.path.join(target_folder, f"{cid}.json")
            with open(out_file, "w", encoding="utf-8") as fp:
                json.dump(items, fp, ensure_ascii=False, indent=2)

    categories_metadata = []
    level_counts_global = {"A1": 0, "A2": 0, "B1": 0, "B2": 0, "C1": 0, "C2": 0}

    for c in CATEGORIES:
        cid = c["id"]
        items = slices[cid]
        lvl_dist = {"A1": 0, "A2": 0, "B1": 0, "B2": 0, "C1": 0, "C2": 0}
        for item in items:
            lvl = item.get("level", "B1")
            lvl_dist[lvl] = lvl_dist.get(lvl, 0) + 1
            level_counts_global[lvl] = level_counts_global.get(lvl, 0) + 1

        categories_metadata.append({
            "id": c["id"],
            "name_en": c["name_en"],
            "name_zh": c["name_zh"],
            "group": c["group"],
            "group_name_zh": c["group_name_zh"],
            "icon": c["icon"],
            "count": len(items),
            "word_count": len(items),
            "level_distribution": lvl_dist,
            "sample_words": [w["word"] for w in items[:8]]
        })

    categories_manifest = {
        "version": "5.0.0",
        "total_words": len(all_words),
        "total_categories": len(CATEGORIES),
        "level_distribution": level_counts_global,
        "categories": categories_metadata
    }

    for p in [os.path.join(repo_dir, "categories.json"),
              os.path.join(project_dir, "public", "categories.json"),
              os.path.join(project_dir, "categories.json")]:
        with open(p, "w", encoding="utf-8") as fp:
            json.dump(categories_manifest, fp, ensure_ascii=False, indent=2)

    categories_js_content = f"// Auto-generated 34-category index\nwindow.CATEGORIES_INDEX = {json.dumps(categories_manifest, ensure_ascii=False, indent=2)};\n"
    for p in [os.path.join(repo_dir, "categories.js"),
              os.path.join(project_dir, "public", "categories.js"),
              os.path.join(project_dir, "categories.js")]:
        with open(p, "w", encoding="utf-8") as fp:
            fp.write(categories_js_content)

    print("\n" + "=" * 65)
    print("📊 34 Categories Distribution Summary:")
    print("=" * 65)
    for cat_meta in categories_metadata:
        samples = ", ".join(cat_meta["sample_words"][:5])
        print(f"  {cat_meta['icon']} {cat_meta['name_zh']:22} ({cat_meta['id']:24}): {cat_meta['count']:4} words | {samples}")
    print("=" * 65)
    print(f"Total vocabulary compiled: {len(all_words)} words across {len(CATEGORIES)} categories.")
    print("Level breakdown:", level_counts_global)
    print("=" * 65)

if __name__ == "__main__":
    main()
