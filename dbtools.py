"""
用户JSON数据库管理模块（协程安全版本）
支持无缝切换 json 和 ujson 库
"""

"""
import asyncio
from pathlib import Path
from asyncio import Lock
from uuid import uuid4
from datetime import datetime

from os import makedirs as os_makedirs
from os.path import exists as path_exists, join as path_join
from json import load as json_load, dump as json_dump
from random import shuffle
import asyncio
"""

import asyncio
from asyncio import Lock
from datetime import datetime
from os import makedirs
from os.path import exists as path_exists, join as path_join
from json import load as json_load, dump as json_dump
from pathlib import Path


# 新增专用锁，防止并发读写缓存
random_names_lock = asyncio.Lock()

# 缓存文件路径
RANDOM_CACHE_DIR = "temp"
RANDOM_CACHE_FILE = path_join(RANDOM_CACHE_DIR, "random_names.json")


def read_random_cache() -> dict:
    """读取随机名字缓存，返回 {班级名: [已抽姓名列表]} 的字典，若文件不存在则返回空字典"""
    if not path_exists(RANDOM_CACHE_FILE):
        return {}
    try:
        with open(RANDOM_CACHE_FILE, "r", encoding="utf-8") as f:
            return json_load(f)
    except Exception:
        return {}

def write_random_cache(cache: dict):
    """将缓存字典写入文件，若目录不存在则自动创建"""
    makedirs(RANDOM_CACHE_DIR, exist_ok=True)
    with open(RANDOM_CACHE_FILE, "w", encoding="utf-8") as f:
        json_dump(cache, f, ensure_ascii=False, indent=4)

def get_all_class_students() -> dict:
    """
    读取所有班级的学生姓名，返回 {班级名: [所有姓名列表]} 的字典。
    通过 Group.json 中的群文件字段去重，再到 class 目录下加载对应 JSON。
    """
    # 读取 Group.json
    group_path = "class/Group.json"
    if not path_exists(group_path):
        return {}
    with open(group_path, "r", encoding="utf-8") as f:
        groups = json_load(f)

    # 收集所有唯一的班级文件名（不带 .json）
    class_files = set()
    for gid, ginfo in groups.items():
        if "群文件" in ginfo:
            class_files.add(ginfo["群文件"])

    all_students = {}
    for cf in class_files:
        json_file = f"class/{cf}.json"
        if not path_exists(json_file):
            continue
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                students = json_load(f)
        except Exception:
            continue
        # 提取姓名列表
        names = [info["姓名"] for info in students.values() if "姓名" in info]
        all_students[cf] = names
    return all_students

def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

_raw_print = print
def print(*args, **kwargs):
    _raw_print(f"[{get_time()}]", *args, **kwargs)

# 尝试导入 ujson，如果没有则回退到 json
try:
    import ujson as json
    print("使用 ujson 库（高性能）")
except ImportError:
    import json as json
    print("使用标准 json 库")

class Config_DB:
    def __init__(self, db_path: str = "config.json"):
        self.db_path = Path(db_path)
        self._lock = Lock()
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """确保数据库文件存在"""
        if not self.db_path.exists():
            self.db_path.write_text("{}", encoding='utf-8')

    async def _read_db(self) -> dict:
        """异步读取数据库"""
        async with self._lock:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                    None,
                    self.db_path.read_text,
                    "utf-8"
                    )

            return json.loads(content)

    async def _writr_db(self, data: dict):
        """异步写入数据库"""
        async with self._lock:
            loop = asyncio.get_event_loop()
            # 格式化JSON
            if hasattr(json, '__name__') and 'ujson' in json.__name__:
                content = json.dumps(data, ensure_ascii=False, indent=4)
            else:
                content = json.dumps(data, ensure_ascii=False, indent=4)
            # 在线程池中执行IO操作
            await loop.run_in_executor(
                None,
                self.db_path.write_text,
                content,
                "utf-8"
            )

    async def show(self):
        return await self._read_db()

    async def admin_add(self, data:str) -> None:
        """添加超级管理员权限"""
        db = await self._read_db()

        if data in db["超级管理员"]:
            return True

        db['超级管理员'].append(data)
        await self._writr_db(db)

    async def admin_del(self, data:str) -> None:
        """删除超级管理员权限"""
        db = await self._read_db()
        db["超级管理员"] = [item for item in db["超级管理员"] if item != data]
        await self._writr_db(db)

    async def get_super_admin_passwd(self) -> str:
        """获得超级管理员密钥"""
        db = await self._read_db()
        return db["超级管理员密钥"]

    async def verify_admin(self, data) -> bool:
        """验证是否是超级管理员"""
        db = await self._read_db()
        if data in db["超级管理员"]:
            return True
        return False

    async def newtask(self, taskname:str, precision:float|bool, remark:str=None) -> int:
        """新建任务"""
        if not isinstance(precision, (float, bool)):
            raise TypeError(f"参数 precision 必须是flat或bool类型, 但收到了 {type(precision)}")

        if not remark:
            remark = ""

        db = await self._read_db()
        ID = 1
        while True:
            if not str(ID) in db["任务"]:
                break

            ID += 1

        db["任务"][str(ID)] = {
                "名称": taskname,
                "精度": precision,
                "时间": get_time(),
                "备注": remark
                }

        await self._writr_db(db)
        return ID

    async def changing_matching_degree(self, task_id, precision) -> None:
        db = await self._read_db()
        if precision == "False" or precision == "0" or precision == "false":
            print("ConfigDB 转化为bool")
            precision = False 
        else:
            print("ConfigDB 转化为float")
            precision =  float(precision)

        db['任务'][task_id]['精度'] = precision
        await self._writr_db(db)

    async def task_info(self) -> dict:
        """查看任务ID任务"""
        db = await self._read_db()
        return db["任务"]

    async def task_del(self, data) -> None:
        """删除任务ID任务"""
        db = await self._read_db()
        del db["任务"][data]
        await self._writr_db(db)

    async def task_del_all(self) -> None:
        """删除所有任务"""
        db = await self._read_db()
        db["任务"] = {}
        await self._writr_db(db)

    async def taskid_search(self, taskid:str) -> None:
        """根据任务ID查询任务"""
        db = await self._read_db()
        db = await self._read_db()
        return db["任务"][taskid]

    async def get_Argentina(self) -> str:
        """返回设置文件中的Argentina"""
        db = await self._read_db()
        return db["Argentina"]

    async def get_secret(self) -> str:
        """返回设置文件中的secret"""
        db = await self._read_db()
        return db["secret"]

    async def get_task_all(self) -> dict:
        """返回当前学院所有任务"""
        db = await self._read_db()
        return db["任务"]

class Group_DB:
    def __init__(self, db_path: str="Group"):
        self.db_path = Path(f'class/{db_path}.json')
        self._lock = Lock()
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """确保数据库文件存在"""
        if not self.db_path.exists():
            self.db_path.write_text("{}", encoding='utf-8')

    async def _read_db(self) -> dict:
        """异步读取数据库"""
        async with self._lock:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                    None,
                    self.db_path.read_text,
                    "utf-8"
                    )

            return json.loads(content)

    async def _writr_db(self, data: dict):
        """异步写入数据库"""
        async with self._lock:
            loop = asyncio.get_event_loop()
            # 格式化JSON
            if hasattr(json, '__name__') and 'ujson' in json.__name__:
                content = json.dumps(data, ensure_ascii=False, indent=4)
            else:
                content = json.dumps(data, ensure_ascii=False, indent=4)
            # 在线程池中执行IO操作
            await loop.run_in_executor(
                None,
                self.db_path.write_text,
                content,
                "utf-8"
            )

    async def show(self):
        return await self._read_db()

    async def group_add(self, data:str, class_name:str, file_path:str, password:str="xuanqing") -> None:
        """创建一个群"""
        db = await self._read_db()
        db[data] = {
                "群名称": class_name,
                "管理员": [],
                "管理员密码": password,
                "群文件": file_path,
                "任务":{
                    },
                "创建时间": get_time()
                }
        await self._writr_db(db)

    async def group_del(self, data:str) -> None:
        """删除一个群"""
        db = await self._read_db()
        del db[data]
        await self._writr_db(db)

    async def group_admin_add(self, data:str, QID:str) -> None:
        """新增一个管理员"""
        db = await self._read_db()
        db[data]["管理员"].append(QID)
        await self._writr_db(db)

    async def set_group_admin_passwd(self, data:str, password:str) -> None:
        """设置当前群管理员密码"""
        db = await self._read_db()
        db[data]["管理员密码"] = password
        await self._writr_db(db)

    async def verify_group_admin(self, data:str, QID:str) -> bool:
        """验证当前用户是否是群管理员"""
        db = await self._read_db()
        if QID in db[data]["管理员"]:
            return True
        return False

    async def group_admin_del(self, data:str, QID:str) -> None:
        """删除一个群管理员"""
        db = await self._read_db()
        db[data]["管理员"] = [item for item in db[data]["管理员"] if item != QID]
        await self._writr_db(db)

    async def get_group_admin_password(self, data:str) -> str:
        """获得当前群管理员密码"""
        db = await self._read_db()
        return db[data]["管理员密码"]

    async def get_group_admin_all(self, data:str) -> list:
        """获得当前群所有管理员QID"""
        db = await self._read_db()
        return db[data]["管理员"]

    async def get_group_admin_count(self, data:str) -> int:
        """统计当前群所有管理员"""
        db = await self._read_db()
        return len(db[data]["管理员"])

    async def get_all_group(self) -> dict:
        """获得所有数据"""
        return await self._read_db()

    async def get_all_group_QID(self) -> dict:
        """获得所有群QID"""
        db =  await self._read_db()
        return db.keys()

    async def get_group_info(self, data:str) -> dict:
        """获得本群信息"""
        db =  await self._read_db()
        return db[data]

    async def get_group_task(self, data:str) -> dict:
        """获得本群当前任务"""
        db =  await self._read_db()
        return db[data]['任务']

    async def changing_matching_degree(self, group_openid, task_id, precision) -> None:
        """修改一个任务的匹配精度"""
        db =  await self._read_db()
        if precision == "False" or precision == "0" or precision == "false":
            print("GroupDB 转化为bool")
            precision = False 
        else:
            print("GroupDB 转化为float")
            precision =  float(precision)

        db[group_openid]['任务'][task_id]['精度'] = precision
        await self._writr_db(db)

    async def newtask(self, group_openid:str, taskname:str, precision:float|bool, remark:str=None) -> int:
        """新建任务"""
        db =  await self._read_db()

        if not isinstance(precision, (float, bool)):
            raise TypeError(f"参数 precision 必须是flat或bool类型, 但收到了 {type(precision)}")

        if not remark:
            remark = ""

        group_info = await self.get_group_info(group_openid)

        ID = 1
        while True:
            if not str(ID) in group_info["任务"]:
                break
            ID += 1

        db[group_openid]["任务"][str(ID)] = {
                '名称': taskname,
                '精度': precision,
                '时间': get_time(),
                '备注': remark
                }

        await self._writr_db(db)
        return ID

    async def task_del(self, data, _id) -> None:
        """删除一个群任务"""
        db =  await self._read_db()
        del db[data]['任务'][_id]

        await self._writr_db(db)


class Class_DB:
    def __init__(self, db_path: str):
        self.db_path = Path(f'class/{db_path}.json')
        self._lock = Lock()
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """确保数据库文件存在"""
        if not self.db_path.exists():
            self.db_path.write_text("{}", encoding='utf-8')

    async def _read_db(self) -> dict:
        """异步读取数据库"""
        async with self._lock:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                    None,
                    self.db_path.read_text,
                    "utf-8"
                    )

            return json.loads(content)

    async def _writr_db(self, data: dict):
        """异步写入数据库"""
        async with self._lock:
            loop = asyncio.get_event_loop()
            # 格式化JSON
            if hasattr(json, '__name__') and 'ujson' in json.__name__:
                content = json.dumps(data, ensure_ascii=False, indent=4)
            else:
                content = json.dumps(data, ensure_ascii=False, indent=4)
            # 在线程池中执行IO操作
            await loop.run_in_executor(
                None,
                self.db_path.write_text,
                content,
                "utf-8"
            )

    async def show(self):
        return await self._read_db()

    async def count_student(self) -> int:
        """统计班级人数"""
        db = await self._read_db()
        return len(db)

    async def count_student_xuehao(self) -> list:
        """返回当前班级所有学生学号"""
        db = await self._read_db()
        _id = db.keys()
        all_id = []
        for i in _id:
            all_id.append(db[i]["学号"])

        return all_id 

    async def get_student_all_name(self) -> list:
        """返回当前班级所有名字"""
        db = await self._read_db()
        name = db.keys()
        all_name = []
        for i in name:
            all_name.append(db[i]["姓名"])

        return all_name

    async def get_student_info(self, data:str) -> dict:
        """查看当前学号学生信息"""
        db = await self._read_db()
        return db[data]

    async def set_student_passwd(self, data:str, passwd:str) -> None:
        """修改对应学生密码"""
        db = await self._read_db()
        db[data]["密码"] = passwd
        await self._writr_db(db)

    async def set_student_QID(self, data:str, xuehao:str) -> None:
        """绑定ID(腾讯分配的)"""
        db = await self._read_db()
        db[xuehao]["QID"] = data
        await self._writr_db(db)

    async def search_QID_info(self, QID:str) -> dict:
        """根据QID 搜索班级对应学生信息"""
        db = await self._read_db()
        for i in db.keys():
            if QID == db[i]['QID']:
                return db[i]
        return False

    async def search_xuehao_info(self, data:str) -> dict:
        db = await self._read_db()
        return db[data]


# === 使用示例 ===
async def main():
    db = Group_DB()
    QID = "BB3996E091ADBAF42904F14DCCFB5414"
# 运行异步主函数
if __name__ == "__main__":
    asyncio.run(main())
