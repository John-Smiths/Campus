# 以下为注册命令所用模块
import botpy
from botpy.types.message import Message
from botpy.types.message import Reference   # 该模块为引用回复暂时没用
from botpy.message import C2CMessage
from botpy.types.message import MarkdownPayload, MessageMarkdownParams
from botpy import logging, BotAPI
from botpy.ext.command_util import Commands

# 以下为机器人功能所需模块
from py.packzip import *
from py.writename import *
from py.repid_image_detection import *
from py.systeminfo import *
from py.tools import *
from py.phash import get_image_block_hashes_optimized,  calculate_match_degree
import py.ai
import dbtools
import py.filecontrol
import py.download_image
import py.readname

# 以下为系统模块
from datetime import datetime
from base64 import b64encode # 暂未使用因为不需要发送附带图片的消息 需要修改腾讯的源代码 ----2024.11.30
from json import loads, dump, load
from os import makedirs, system, getcwd
from time import sleep, time
from asyncio import Lock

# 以下为第三方模块
from cv2 import imread, cvtColor, COLOR_BGR2GRAY
from PIL import Image
from markdown import markdown
from numpy import array
from collections import defaultdict
from shutil import rmtree
import re
from random import shuffle
# 最后一次开发 ----2026.5.5 主要更新添加随机名字命令

# 声明管理等级
_group = '群'
_class = '学院'

# 协程锁 主要用于控制图片缓存
lock = Lock()

# 以下为数据库管理对象注册
config = dbtools.Config_DB() 
group_db = dbtools.Group_DB()
# ------------------------



@Commands("随机名字")
async def random_names(api: BotAPI, message: Message, params=None):
    """
    命令格式：随机名字 [数量]
    默认抽取60人，所有班级尽量平均抽取，已抽过的不会再抽，全部抽完自动重置。
    仅超级管理员可用。
    """
    raw_msg = message
    member_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid   # 可用于日志，但不影响功能

    # 权限校验
    if not await config.verify_admin(member_openid):
        await message.reply(content="\n您不是超级管理员，无权使用此命令。")
        return

    # 解析数量参数
    msg = raw_msg.content.strip()
    parts = msg.split("随机名字")[1].strip().split()
    if parts:
        try:
            count = int(parts[0])
            if count <= 0:
                await message.reply(content="\n数量必须为正整数。")
                return
        except ValueError:
            await message.reply(content="\n参数必须为整数，例如：随机名字 12")
            return
    else:
        count = 60  # 默认值

    # 加锁，防止并发修改缓存
    async with dbtools.random_names_lock:
        # 1. 读取缓存
        cache = dbtools.read_random_cache()

        # 2. 获取所有班级的完整学生名单
        all_students_master = dbtools.get_all_class_students()
        if not all_students_master:
            await message.reply(content="\n没有找到任何班级信息。")
            return

        # 3. 过滤已抽取的学生，得到每个班级可用名单
        available = {}
        total_available = 0
        for class_name, all_names in all_students_master.items():
            already = set(cache.get(class_name, []))
            available_names = [n for n in all_names if n not in already]
            available[class_name] = available_names
            total_available += len(available_names)

        # 4. 如果所有可用人数为0，则重置缓存
        if total_available == 0:
            cache.clear()
            # 重新构建可用名单（此时全部可用）
            for class_name in all_students_master:
                available[class_name] = list(all_students_master[class_name])
            total_available = sum(len(v) for v in available.values())

        # 限制抽取数量不超过总人数
        if count > total_available:
            count = total_available
            if count == 0:
                await message.reply(content="\n所有班级没有学生，无法抽取。")
                return

        # 5. 采用轮流从各班抽取的策略，以保证班级间平均
        # 打乱每个班级的内部顺序，并打乱班级顺序（让抽取更随机）
        pool_classes = list(available.keys())
        shuffle(pool_classes)
        for c in pool_classes:
            shuffle(available[c])

        # 使用索引轮流取
        selected = []          # 存放 (班级名, 姓名)
        idx = 0                # 当前班级索引
        while len(selected) < count:
            class_name = pool_classes[idx % len(pool_classes)]
            if available[class_name]:
                name = available[class_name].pop()
                selected.append((class_name, name))
            idx += 1
            # 如果连续遍历所有班级一圈都没取到人，说明所有班级已空
            if idx >= len(pool_classes) * 1000:   # 安全退出，实际不会这么多次
                # 检查是否还有任何班级有剩余，没有则退出
                if all(len(available[c]) == 0 for c in pool_classes):
                    break
                idx = 0   # 重置尝试

        # 实际可能取不够 count（总人数不足），已做限制，这里应该能取够

        # 6. 更新缓存
        for class_name, name in selected:
            cache.setdefault(class_name, []).append(name)
        dbtools.write_random_cache(cache)

        # 7. 组织回复消息
        # 按班级分组统计
        class_result = {}
        for cn, nm in selected:
            class_result.setdefault(cn, []).append(nm)

        reply_lines = [f"✅ 已随机抽取 {len(selected)} 人："]
        for cn, names in class_result.items():
            reply_lines.append(f"\n【{cn}】{len(names)}人：{'、'.join(names)}")
        reply_lines.append(f"\n━━━━━━━━━━━━━━━━━━━━")
        reply_lines.append(f"剩余可抽总人数：{total_available - len(selected)}")
        reply_lines.append(f"缓存位置：{dbtools.RANDOM_CACHE_FILE}")

        await message.reply(content="\n" + "\n".join(reply_lines))
# ------------------------------------------------------------------------
# 定义一个多层 defaultdict
def nested_dict():
    return defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

# 这是收集的数据, 防止经常打开读写占用IO以及延长匹配速度.
image_data = nested_dict() # 多层字典

def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

_raw_print = print
def print(*args, **kwargs):
    _raw_print(f"[{get_time()}]", *args, **kwargs)

async def verify_image(task_info, task_id, student, group, group_openid, image_path, grade:str) -> dict:
    global image_data
    _group = grade
    image_hash = get_image_block_hashes_optimized(image_path)
    if not image_hash:
        status = {
                "状态": False,
                '详情': '图片损坏请重新提交',
                '错误代码': 0
                }
        return status
    else:

        try:
            async with lock:
                task_all_student_id = image_data[_group][group_openid][task_id].keys()
        except KeyError: # 说明该任务ID的序列找不到, 可能是第一次进行提交, 所以进行创建
            async with lock:
                image_data[_group][task_id] = {}

        if not len(task_all_student_id):
            async with lock:
                image_data[_group][group_openid][task_id][student['学号']] = { # 之所以用群名称是为了更好的适配版本更迭
                        '姓名': student['姓名'],
                        '群': group['群名称'],
                        'Data': image_hash
                        }

            status = {
                    "状态": True,
                    "详情": "这是第一个提交者无需进行匹配",
                    "错误代码": 1
                    }

            return status
        else:
            for i in task_all_student_id:
                data = image_data[_group][group_openid][task_id][i]['Data']
                matched_degree = calculate_match_degree(image_hash, data) # 匹配度
                #  if matched_degree >= task_info["精度"]: # 检测结果大于等于设定的阈值, 判定为复制他人截图, 检查完毕直接跳出循环
                if matched_degree >= task_info["精度"] and i != student['学号']: # 检测结果大于等于设定的阈值, 判定为复制他人截图, 检查完毕直接跳出循环
                    status = {
                            "状态": False,
                            "详情": "这是一个他人截图",
                            "错误代码": -1,
                            "盗用者学号": student["学号"],
                            "盗用者姓名": student["姓名"],
                            "被盗用者学号": i,
                            "被盗用者姓名": image_data[_group][group_openid][task_id][i]['姓名'],
                            "群": group['群名称'],
                            "匹配度": matched_degree
                            }
                    return status

                status = {
                        "状态": True,
                        "详情": "这是自己的截图",
                        "错误代码": 1,
                        }
                return status

@Commands("删除任务")
async def task_del(api: BotAPI, message: Message, params=None):
    global image_task

    raw_msg = message
    msg = raw_msg.content.strip()

    member_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid
    command = msg.split("删除任务")[1].strip().split()

    try:
        task_id = command[0]
    except IndexError:
        task_id = False

    if await config.verify_admin(member_openid): # 超级管理员 更改匹配度, 通常需要 config 对象
        """
        command [0]: 任务ID
        """

        try:
            group_all_task = await config.get_task_all()
        except KeyError:
            await message.reply(content='\n' + 'QID群的数据库存在问题, 请联系超级管理员或开发者')
            return

        if len(group_all_task) == 0:
            await message.reply(content='\n' + 'QID群当前没有任务')
            return
        if len(group_all_task) == 1 and not task_id:
            base_task_id = next(iter(group_all_task)) # 当用户没有指定任务ID 同时 只存在一个任务 时 会默认指向唯一一个任务的任务ID
        else:
            base_task_id = task_id

        if not base_task_id:
            await message.reply(content='\n' + '您第一个参数没有指定任务ID')
            return

        try:
            await config.task_del(command[0])
            rmtree(f'db/学院/{group_all_task[base_task_id]["名称"]}-{task_id}')
        except KeyError:
            await message.reply(content='\n' + f'任务ID:{base_task_id}\n状态:删除失败, 任务可能不存在\n时间:{get_time()}')
            return

        try:
            async with lock:
                del image_data[_class][group_openid][base_task_id]
        except KeyError:
                print("[群] 删除图像缓存失败, 可能并没有一次提交, 所以无法进行删除")

        await message.reply(content='\n' + f'任务:{group_all_task[base_task_id]["名称"]}\n任务ID:{base_task_id}\n状态:已删除\n时间:{get_time()}')

    elif await group_db.verify_group_admin(group_openid, member_openid): # 管理员统计任务 通常需要 group_db 对象
        """
        command [0]: 任务ID
        """

        try:
            group_info = await group_db.get_group_info(group_openid)
        except KeyError:
            await message.reply(content='\n' + '本群尚未绑定, 请联系管理员')
            return
        try:
            group_all_task = await group_db.get_group_task(group_openid)
        except KeyError:
            await message.reply(content='\n' + '本群的数据库存在问题, 请联系超级管理员或开发者')
            return

        class_group_file_path = group_info["群文件"] # 获得对应群的.json文件名
        if len(group_all_task) == 0:
            await message.reply(content='\n' + '本群当前没有任务')
            return
        if len(group_all_task) == 1 and not task_id:
            base_task_id = next(iter(group_all_task)) # 当用户没有指定任务ID 同时 只存在一个任务 时 会默认指向唯一一个任务的任务ID
        else:
            base_task_id = task_id

        if not base_task_id:
            await message.reply(content='\n' + '您第一个参数没有指定任务ID')
            return

        class_db = dbtools.Class_DB(class_group_file_path)
        my_info = await class_db.search_QID_info(member_openid)

        # {}

        if my_info:
            try:
                await group_db.task_del(group_openid, base_task_id)
                rmtree(f'db/群/{group_info["群名称"]}-{group_openid}/{group_all_task[base_task_id]["名称"]}-{task_id}')
            except KeyError:
                await message.reply(content='\n' + f'任务ID:{base_task_id}\n状态:删除失败, 任务可能不存在\n时间:{get_time()}')
                return

            try:
                async with lock:
                    del image_data[_group][group_openid][base_task_id]
            except KeyError:
                print("[群] 删除图像缓存失败, 可能并没有一次提交, 所以无法进行删除")

            await message.reply(content='\n' + f'任务:{group_all_task[base_task_id]["名称"]}\n任务ID:{base_task_id}\n状态:已删除\n时间:{get_time()}')
        else:
            await message.reply(content='\n' + '本群并没有绑定您的信息, 请先将您的信息与本群绑定后再次尝试')
    else:
        await message.reply(content='\n' + '你并非管理员或超级管理员无法进行统计任务')



@Commands("更改匹配度")
async def changing_matching_degree(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()

    member_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid
    command = msg.split("更改匹配度")[1].strip().split()

    try:
        task_id = command[0]
    except IndexError:
        task_id = False

    if await config.verify_admin(member_openid): # 超级管理员 更改匹配度, 通常需要 config 对象
        """
        command [0]: 任务ID
        command [1]: 任务匹配度
        """

        try:
            group_all_task = await config.get_task_all()
        except KeyError:
            await message.reply(content='\n' + 'QID群的数据库存在问题, 请联系超级管理员或开发者')
            return

        if len(group_all_task) == 0:
            await message.reply(content='\n' + 'QID群当前没有任务')
            return
        if len(group_all_task) == 1 and not task_id:
            base_task_id = next(iter(group_all_task)) # 当用户没有指定任务ID 同时 只存在一个任务 时 会默认指向唯一一个任务的任务ID
        else:
            base_task_id = task_id

        if not base_task_id:
            await message.reply(content='\n' + '您第一个参数没有指定任务ID')
            return

        try:
            precision = command[1]
        except IndexError:
            await message.reply(content='\n' + f'您没有提交第二个参数也就是精度的具体值, 通常可以更改为小数或False')
            return

        await config.changing_matching_degree(base_task_id, command[1])
        group_all_task = await config.get_task_all()
        await message.reply(content='\n' + f'任务:{group_all_task[base_task_id]["名称"]}\n任务ID:{base_task_id}\n精度:{command[1]}\n状态:更改成功\n时间:{get_time()}')

    elif await group_db.verify_group_admin(group_openid, member_openid): # 管理员统计任务 通常需要 group_db 对象
        """
        command [0]: 任务ID
        command [1]: 任务匹配度
        """

        try:
            group_info = await group_db.get_group_info(group_openid)
        except KeyError:
            await message.reply(content='\n' + '本群尚未绑定, 请联系管理员')
            return
        try:
            group_all_task = await group_db.get_group_task(group_openid)
        except KeyError:
            await message.reply(content='\n' + '本群的数据库存在问题, 请联系超级管理员或开发者')
            return

        class_group_file_path = group_info["群文件"] # 获得对应群的.json文件名
        if len(group_all_task) == 0:
            await message.reply(content='\n' + '本群当前没有任务')
            return
        if len(group_all_task) == 1 and not task_id:
            base_task_id = next(iter(group_all_task)) # 当用户没有指定任务ID 同时 只存在一个任务 时 会默认指向唯一一个任务的任务ID
        else:
            base_task_id = task_id

        if not base_task_id:
            await message.reply(content='\n' + '您第一个参数没有指定任务ID')
            return

        class_db = dbtools.Class_DB(class_group_file_path)
        my_info = await class_db.search_QID_info(member_openid)

        # {}

        if my_info:
            try:
                precision = command[1]
            except IndexError:
                await message.reply(content='\n' + f'您没有提交第二个参数也就是精度的具体值, 通常可以更改为小数或False')
                return

            await group_db.changing_matching_degree(group_openid, base_task_id, command[1])
            group_all_task = await group_db.get_group_task(group_openid)
            await message.reply(content='\n' + f'任务:{group_all_task[base_task_id]["名称"]}\n任务ID:{base_task_id}\n精度:{command[1]}\n状态:更改成功\n时间:{get_time()}')
        else:
            await message.reply(content='\n' + '本群并没有绑定您的信息, 请先将您的信息与本群绑定后再次尝试')
    else:
        await message.reply(content='\n' + '你并非管理员或超级管理员无法进行统计任务')


@Commands("统计任务")
async def count(api: BotAPI, message: Message, params=None):
    """
    command [0] 任务ID
    command [1] QID
    """
    raw_msg = message
    msg = raw_msg.content.strip()

    member_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid
    command = msg.split("统计任务")[1].strip().split()

    try:
        task_id = command[0]
    except IndexError:
        task_id = False

    # if await config.verify_admin(member_openid): # 超级管理员统计任务
    if await group_db.verify_group_admin(group_openid, member_openid) or await config.verify_admin(member_openid): # 管理员统计任务
        try:
            group_openid = command[1]
        except IndexError:
            await message.reply(content='\n' + '没有传入QID')
            return

        try:
            group_info = await group_db.get_group_info(group_openid)
        except KeyError:
            await message.reply(content='\n' + '本群尚未绑定, 请联系管理员')
            return

        try:
            group_all_task = await config.get_task_all()
        except KeyError:
            await message.reply(content='\n' + '本群的数据库存在问题, 请联系超级管理员或开发者')
            return

        class_group_file_path = group_info["群文件"] # 获得对应群的.json文件名
        if len(group_all_task) == 0:
            await message.reply(content='\n' + '本群当前没有任务')
            return
        if len(group_all_task) == 1 and not task_id:
            base_task_id = next(iter(group_all_task)) # 当用户没有指定任务ID 同时 只存在一个任务 时 会默认指向唯一一个任务的任务ID
        else:
            base_task_id = task_id

        if not base_task_id:
            await message.reply(content='\n' + '您第一个参数没有指定任务ID')
            return

        class_db = dbtools.Class_DB(class_group_file_path)
        my_info = await class_db.search_QID_info(member_openid)

        _path = f'db/学院/{group_all_task[base_task_id]["名称"]}-{base_task_id}/{class_group_file_path}-{group_openid}/' # 对象所在目录
        all_file = py.readname.read_filename(_path)
        _id = []
        for i in all_file:
            _id.append(i.split("-")[0])

        # _id 任务统计已经交了的同学

        if len(_id) == 0:
            await message.reply(content='\n' + f'任务:{group_all_task[base_task_id]["名称"]}\n任务ID:{base_task_id}\n当前无一人提交\n时间:{get_time()}')
            return
        all_student_id = await class_db.count_student_xuehao()

        result = list(set(all_student_id) - set(_id)) # 未交的 学生学号id
        result_name = []
        all_student_info = await class_db._read_db()
        if len(result) == all_student_info:
            await message.reply(content='\n' + f'任务:{group_all_task[base_task_id]["名称"]}\n任务ID:{base_task_id}\n已全部收齐\n时间:{get_time()}')
            return

        for i in result:
            result_name.append(all_student_info[i]["姓名"])

        formar_names = py.readname.formar_names(result_name, 3)
        await message.reply(content='\n' + f'任务:{group_all_task[base_task_id]["名称"]}\n任务ID:{base_task_id}\n已交:{len(_id)}人\n未交:\n{formar_names}\n共计:{len(result)}人\n时间:{get_time()}')
    # elif await group_db.verify_group_admin(group_openid, member_openid): # 管理员统计任务
    else:
        try:
            group_info = await group_db.get_group_info(group_openid)
        except KeyError:
            await message.reply(content='\n' + '本群尚未绑定, 请联系管理员')
            return
        try:
            group_all_task = await group_db.get_group_task(group_openid)
        except KeyError:
            await message.reply(content='\n' + '本群的数据库存在问题, 请联系超级管理员或开发者')
            return

        class_group_file_path = group_info["群文件"] # 获得对应群的.json文件名
        if len(group_all_task) == 0:
            await message.reply(content='\n' + '本群当前没有任务')
            return
        if len(group_all_task) == 1 and not task_id:
            base_task_id = next(iter(group_all_task)) # 当用户没有指定任务ID 同时 只存在一个任务 时 会默认指向唯一一个任务的任务ID
        else:
            base_task_id = task_id

        if not base_task_id:
            await message.reply(content='\n' + '您第一个参数没有指定任务ID')
            return

        class_db = dbtools.Class_DB(class_group_file_path)
        my_info = await class_db.search_QID_info(member_openid)

        if my_info:
                # _path = f'db/群/{group_all_task[base_task_id]["名称"]}-{base_task_id}/{class_group_file_path}-{group_openid}/' # 对象所在目录
                _path = f'db/群/{group_info["群名称"]}-{group_openid}/{group_all_task[base_task_id]["名称"]}-{base_task_id}/{class_group_file_path}-{group_openid}/' # 对象所在目录
                all_file = py.readname.read_filename(_path)
                _id = []
                for i in all_file:
                    _id.append(i.split("-")[0])

                # _id 任务统计已经交了的同学

                if len(_id) == 0:
                    await message.reply(content='\n' + f'任务:{group_all_task[base_task_id]["名称"]}\n任务ID:{base_task_id}\n当前无一人提交\n时间:{get_time()}')
                    return
                all_student_id = await class_db.count_student_xuehao()

                result = list(set(all_student_id) - set(_id)) # 未交的 学生学号id
                result_name = []
                all_student_info = await class_db._read_db()
                if len(result) == all_student_info:
                    await message.reply(content='\n' + f'任务:{group_all_task[base_task_id]["名称"]}\n任务ID:{base_task_id}\n已全部收齐\n时间:{get_time()}')
                    return

                for i in result:
                    result_name.append(all_student_info[i]["姓名"])

                formar_names = py.readname.formar_names(result_name, 3)
                await message.reply(content='\n' + f'任务:{group_all_task[base_task_id]["名称"]}\n任务ID:{base_task_id}\n已交:{len(_id)}人\n未交:\n{formar_names}\n共计:{len(result)}人\n时间:{get_time()}')
        else:
            await message.reply(content='\n' + '本群并没有绑定您的信息, 请先将您的信息与本群绑定后再次尝试')

    """
    else:
        await message.reply(content='\n' + '你并非管理员或超级管理员无法进行统计任务')
    """

@Commands("sub")
async def sub(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()

    if 'submit' in msg:
        return

    member_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid
    command = msg.split("sub")[1].strip().split()

    try:
        task_id = command[0]
    except IndexError:
        task_id = False

    try:
        group_info = await group_db.get_group_info(group_openid)
    except KeyError:
        await message.reply(content='\n' + '本群尚未绑定, 请联系管理员')
        return
    try:
        # group_all_task = await group_db.get_group_task(group_openid)
        group_all_task = await config.get_task_all()
    except KeyError:
        await message.reply(content='\n' + '本群的数据库存在问题, 请联系超级管理员或开发者')
        return

    class_group_file_path = group_info["群文件"] # 获得对应群的.json文件名
    if len(group_all_task) == 0:
        await message.reply(content='\n' + '本群当前没有任务')
        return
    if len(group_all_task) == 1 and not task_id:
        base_task_id = next(iter(group_all_task)) # 当用户没有指定任务ID 同时 只存在一个任务 时 会默认指向唯一一个任务的任务ID
    else:
        base_task_id = task_id

    if not base_task_id:
        await message.reply(content='\n' + '您第一个参数没有指定任务ID')
        return

    class_db = dbtools.Class_DB(class_group_file_path)
    my_info = await class_db.search_QID_info(member_openid)

    if my_info:
        try:
            img_url = raw_msg.attachments[0].url
        except IndexError:
            await message.reply(content='\n' + '在您提交的命令中未提交截图, 请附加截图后再次使用此命令进行提交')
            return

        try:
            _path = f'db/学院/{group_all_task[base_task_id]["名称"]}-{base_task_id}/{class_group_file_path}-{group_openid}/' # 对象所在目录
            downloader = py.download_image.ImageDownloader(_path)
            _save_name = f"{my_info['学号']}-{my_info['姓名']}-{group_info['群文件']}" # 文件保存名 对象默认为jpg
            if await downloader.download(img_url, _save_name):
                if group_all_task[base_task_id]["精度"]:
                    verify = await verify_image(group_all_task[base_task_id], base_task_id, my_info, group_info, group_openid, _path+_save_name+'.jpg', _group)
                    if verify['状态']:
                        await message.reply(content='\n' + f'姓名:{my_info["姓名"]}\n绑群:{group_info["群名称"]}\n学号:{my_info["学号"]}\n时间:{get_time()}\n任务:{group_all_task[base_task_id]["名称"]}\nID:{base_task_id}\n状态:已完成')
                    else:
                        if verify['错误代码'] == -1:
                            await message.reply(content='\n' + f"⚠您的截图是盗用的⚠\n\n盗用者姓名:{verify['盗用者姓名']}\n盗用者学号:{verify['盗用者学号']}\n\n被盗用者姓名:{verify['被盗用者姓名']}\n被盗用者学号:{verify['被盗用者学号']}\n\n群:{verify['群']}\n\n时间:{get_time()}\n相似度:{str(int(verify['匹配度']*100))}%")
                else:
                    await message.reply(content='\n' + f'姓名:{my_info["姓名"]}\n绑群:{group_info["群名称"]}\n学号:{my_info["学号"]}\n时间:{get_time()}\n任务:{group_all_task[base_task_id]["名称"]}\nID:{base_task_id}\n状态:已完成')
            else:
                await message.reply(content='\n' + '提交失败未知原因, 请再次提交后如果仍然失败联系管理员或超级管理员')
        except KeyError:
          await message.reply(content='\n' + '不存在该任务ID, 请使用[查看任务]命令来进行查看任务ID')
    else:
        await message.reply(content='\n' + '本群并没有绑定您的信息, 请先将您的信息与本群绑定后再次尝试')


@Commands("submit")
async def submit(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()
    member_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid
    command = msg.split("submit")[1].strip().split()

    try:
        task_id = command[0]
    except IndexError:
        task_id = False

    try:
        group_info = await group_db.get_group_info(group_openid)
    except KeyError:
        await message.reply(content='\n' + '本群尚未绑定, 请联系管理员')
        return
    try:
        # group_all_task = await config.get_task_all()
        group_all_task = await group_db.get_group_task(group_openid)
    except KeyError:
        await message.reply(content='\n' + '本群的数据库存在问题, 请联系超级管理员或开发者')
        return

    class_group_file_path = group_info["群文件"] # 获得对应群的.json文件名

    if len(group_all_task) == 0:
        await message.reply(content='\n' + '群当前没有任务')
        return
    if len(group_all_task) == 1 and not task_id:
        base_task_id = next(iter(group_all_task)) # 当用户没有指定任务ID 同时 只存在一个任务 时 会默认指向唯一一个任务的任务ID
    else:
        base_task_id = task_id

    if not base_task_id:
        await message.reply(content='\n' + '您第一个参数没有指定任务ID')
        return

    class_db = dbtools.Class_DB(class_group_file_path)
    my_info = await class_db.search_QID_info(member_openid)

    if my_info:
        try:
            img_url = raw_msg.attachments[0].url
        except IndexError:
            await message.reply(content='\n' + '在您提交的命令中未提交截图, 请附加截图后再次使用此命令进行提交')
            return

        try:
            '''
            downloader = py.download_image.ImageDownloader(f'db/学院/{group_all_task[base_task_id]["名称"]}-{base_task_id}/{class_group_file_path}-{group_openid}/')
            if await downloader.download(img_url, f"{my_info['学号']}-{my_info['姓名']}-{group_info['群文件']}"):
                await message.reply(content='\n' + f'姓名:{my_info["姓名"]}\n绑群:{group_info["群名称"]}\n学号:{my_info["学号"]}\n时间:{get_time()}\n任务:{group_all_task[base_task_id]["名称"]}\nID:{base_task_id}\n状态:已完成')
            else:
                await message.reply(content='\n' + '提交失败未知原因, 请再次提交后如果仍然失败联系管理员或超级管理员')
            '''
            _path = f'db/群/{group_info["群名称"]}-{group_openid}/{group_all_task[base_task_id]["名称"]}-{base_task_id}/{class_group_file_path}-{group_openid}/' # 对象所在目录
            downloader = py.download_image.ImageDownloader(_path)
            _save_name = f"{my_info['学号']}-{my_info['姓名']}-{group_info['群文件']}" # 文件保存名 对象默认为jpg
            if await downloader.download(img_url, _save_name):
                if group_all_task[base_task_id]["精度"]:
                    verify = await verify_image(group_all_task[base_task_id], base_task_id, my_info, group_info, group_openid, _path+_save_name+'.jpg', _class)
                    if verify['状态']:
                        await message.reply(content='\n' + f'姓名:{my_info["姓名"]}\n绑群:{group_info["群名称"]}\n学号:{my_info["学号"]}\n时间:{get_time()}\n任务:{group_all_task[base_task_id]["名称"]}\nID:{base_task_id}\n状态:已完成')
                    else:
                        if verify['错误代码'] == -1:
                            await message.reply(content='\n' + f"⚠您的截图是盗用的⚠\n\n盗用者姓名:{verify['盗用者姓名']}\n盗用者学号:{verify['盗用者学号']}\n\n被盗用者姓名:{verify['被盗用者姓名']}\n被盗用者学号:{verify['被盗用者学号']}\n\n群:{verify['群']}\n\n时间:{get_time()}\n相似度:{str(int(verify['匹配度']*100))}%")
                else:
                    await message.reply(content='\n' + f'姓名:{my_info["姓名"]}\n绑群:{group_info["群名称"]}\n学号:{my_info["学号"]}\n时间:{get_time()}\n任务:{group_all_task[base_task_id]["名称"]}\nID:{base_task_id}\n状态:已完成')
            else:
                await message.reply(content='\n' + '提交失败未知原因, 请再次提交后如果仍然失败联系管理员或超级管理员')

        except KeyError:
            await message.reply(content='\n' + '不存在该任务ID, 请使用[查看任务]命令来进行查看任务ID')
            return
    else:
        await message.reply(content='\n' + '本群并没有绑定您的信息, 请先将您的信息与本群绑定后再次尝试')


@Commands("查看任务")
async def task_show(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()
    member_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid

    group_info = await group_db.get_group_info(group_openid)
    command = msg.split("查看任务")[1].strip().split()

    class_task_msg = ""
    try:
        class_task = await group_db.get_group_task(group_openid) # 班级所有任务
        if len(class_task) == 0:
            class_task_msg = '没有任务\n'
        else:
            for i in class_task.keys():
                task_name = class_task[i]["名称"]
                task_precision = class_task[i]['精度']
                task_remark = class_task[i]['备注']
                class_task_msg += '任务ID:' + i + '\n'
                class_task_msg += '任务:' + task_name + '\n'
                class_task_msg += '备注:' + task_remark + '\n'
                if await config.verify_admin(member_openid) or await group_db.verify_group_admin(group_openid, member_openid):
                    class_task_msg += '任务精度:' + str(class_task[i]['精度']) + '\n'
    except KeyError:
        await message.reply(content='\n' + '由于本群未绑定, 所以无法查看任务')
        return

    xy_task = await config.get_task_all() # 学院所有任务
    xy_task_msg = ""
    if len(xy_task) == 0:
        xy_task_msg = "没有任务\n"
    else:
        for i in xy_task.keys():
            task_name = xy_task[i]['名称']
            task_precision = xy_task[i]['精度']
            task_remark = xy_task[i]['备注']

            xy_task_msg += '任务ID:' + i + '\n'
            xy_task_msg += '任务:' + task_name + '\n'
            xy_task_msg += '备注:' + task_remark + '\n'
            if await config.verify_admin(member_openid):
                xy_task_msg += '任务精度:' + str(xy_task[i]['精度']) + '\n'

    await message.reply(content="\n"+"学院任务:\n" + xy_task_msg[:-1] + '\n\n' + '班级任务:\n' + class_task_msg[:-1])

@Commands("绑定用户")
async def group_bind_student(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()
    member_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid

    group_info = await group_db.get_group_info(group_openid)
    class_group_file_path = group_info["群文件"] # 获得对应群的.json文件名
    class_db = dbtools.Class_DB(class_group_file_path)
    command = msg.split("绑定用户")[1].strip().split() # 第一个参数学号 第二个参数密码

    try:
        student_info = await class_db.search_xuehao_info(command[0])
    except KeyError:
        await message.reply(content="\n" + "本群不存在您的学号, 请您联系管理员或超级管理员或加群寻找管理员解决此问题(1063473613)")
        return
    if command[1] == student_info["密码"]:
        try:
            my_info = await class_db.set_student_QID(member_openid, command[0])
            await message.reply(content="\n"+"姓名:"+student_info["姓名"]+'\n'+'学号:'+student_info["学号"]+'\n'+"QID:"+member_openid+'\n'+"绑定本群成功")
        except KeyError:
            await message.reply(content="\n" + "本群不存在您的学号, 请您联系管理员或超级管理员或加群寻找管理员解决此问题(1063473613)")
    else:
        await message.reply(content="\n"+"您输入的密码不正确, 请尝试在机器人私聊中重置密码或寻找超级管理员或管理员解决(群:1063473613)")

@Commands("修改群密码")
async def group_add(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()
    command = msg.split("修改群密码")[1].strip().split()
    group_openid = raw_msg.group_openid
    member_openid = raw_msg.author.member_openid

@Commands("绑定群")
async def group_add(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()
    command = msg.split("绑定群")[1].strip().split()
    group_openid = raw_msg.group_openid
    member_openid = raw_msg.author.member_openid
    all_group_QID = await group_db.get_all_group_QID()

    try:
        if await group_db.get_group_admin_count(group_openid) != 0 and not await group_db.verify_group_admin(group_openid, member_openid):
            print("群QID:", group_openid, "一个拥有管理员的群尝试绑定新的群")
            await message.reply(content="\n"+"绑定群:" + '\n' + "QID:" + group_openid + '\n' + "本群已存在管理员, 如需重新绑定请联系超级管理员删除本群QID(您不是管理员)")
            return
        if await group_db.get_group_admin_count(group_openid) != 0 and await group_db.verify_group_admin(group_openid, member_openid):
            print("群QID:", group_openid, "一个拥有管理员的群尝试绑定新的群")
            await message.reply(content="\n"+"绑定群:" + '\n' + "QID:" + group_openid + '\n' + "本群已存在管理员, 如需重新绑定请联系超级管理员删除本群QID")
            return
        if group_openid in all_group_QID:
            print("绑定群:" + command[0],  "QID:", group_openid, "群绑定已存在")
            await message.reply(content="\n"+"绑定群:" + command[0] + '\n' + "QID:" + group_openid + '\n' + "群绑定已存在请联系超级管理员删除")
    except KeyError:
        try:
            print("绑定群:", command[0], "QID:", group_openid, "文件路径:", command[1], "密码:", command[2])
            await group_db.group_add(group_openid, command[0], command[1], command[2])
            await message.reply(content="\n"+"绑定群:" + command[0] + '\n' + "QID:" + group_openid + '\n' + "文件路径:"+ command[1] + '\n' + "密码:" + command[2])
        except:
            await message.reply(content="\n"+"您输入的命令有误" + '\n' + '绑定群 群名称 群文件 群密码')

@Commands("删除群")
async def group_del(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()
    member_openid = raw_msg.author.member_openid

    if await config.verify_admin(member_openid):
        command = msg.split("删除群")[1].strip().split()
        try:
            group_info = await group_db.get_group_info(command[0])
            await group_db.group_del(command[0])
            await message.reply(content="\n" + "QID:" + command[0] + '\n' + "群名称:" + group_info["群名称"] + '\n' + "创建时间:" + group_info["创建时间"] + '\n' + "删除成功")
        except KeyError:
            await message.reply(content="\n"+"不存在此群的QID(已删除或不存在)")
    else:
        print("一个非超级管理员用户使用超级管理员命令", "QID:", member_openid)
        await message.reply(content="\n"+"您并非超级管理员, 如需使用此命令请您联系超级管理员")

@Commands("设置群密码")
async def group_class_password_set(api: BotAPI, message: Message, params=None):
    """仅用于私聊, 修改班级密码"""
    raw_msg = message
    msg = raw_msg.content.strip()
    user_openid = raw_msg.author.user_openid
    command = msg.split("设置群密码")[1].strip().split() # 第一个参数接收 群QID 第二个参数 密码
    if await config.verify_admin(user_openid) or await group_db.verify_group_admin(command[0], user_openid):
        try:
            await group_db.set_group_admin_passwd(command[0], command[1])
            await message.reply(content="密码修改成功")
        except IndexError:
            await message.reply(content="您的参数不正确, 缺少群QID 或 设置的新的密码")
    else:
        print("非超级管理员或管理员用户用户使用管理员命令", "QID:", member_openid)
        await message.reply(content="您并非超级管理员或管理员, 如需使用此命令请您联系超级管理员或管理员")

@Commands("设置用户密码")
async def group_class_student_password_set(api: BotAPI, message: Message, params=None):
    """仅用于私聊, 管理员修改班级用户密码"""
    raw_msg = message
    msg = raw_msg.content.strip()
    user_openid = raw_msg.author.user_openid
    command = msg.split("设置用户密码")[1].strip().split() # 第一个参数接收 群QID 第二个参数 学号 第三个参数 密码 
    if await config.verify_admin(user_openid) or await group_db.verify_group_admin(command[0], user_openid):
        if len(command[2]) > 32 or len(command[2]) < 8:
            await message.reply(content="密码长度太长或太短应当小于32位大于8位")
        else:
            try:
                group_info = await group_db.get_group_info(command[0])
                class_db = dbtools.Class_DB(group_info["群文件"])
                await class_db.set_student_passwd(command[1], command[2])
                await message.reply(content="密码修改成功")
            except IndexError:
                await message.reply(content="您的参数不正确, 缺少群QID 或 设置的新的密码 或 缺少学号")
    else:
        print("非超级管理员或管理员用户用户使用管理员命令", "QID:", member_openid)
        await message.reply(content="您并非超级管理员或管理员, 如需使用此命令请您联系超级管理员或管理员")

@Commands("我的信息")
async def class_group_student(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()
    member_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid

    group_info = await group_db.get_group_info(group_openid)
    class_group_file_path = group_info["群文件"] # 获得对应群的.json文件名
    class_db = dbtools.Class_DB(class_group_file_path)
    my_info = await class_db.search_QID_info(member_openid)

    # """
    data = ""
    if await config.verify_admin(member_openid):
        data += "超级管理员状态:启动\n"
    if await group_db.verify_group_admin(group_openid, member_openid):
        data += "管理员状态:启动"
    # """

    if my_info:
        await message.reply(content="\n" + "姓名:" + my_info["姓名"] + '\n' + '学号:' + my_info["学号"] + '\n' + data + '\n' + '班级:' + group_info['群名称'] + '\n'+ "QID:" + my_info["QID"])
    else:
        await message.reply(content="\n" + '未找到您的信息, 请先绑定信息')


@Commands("删除本群")
async def group_del_ben(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()
    member_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid

    if await config.verify_admin(member_openid) or await group_db.verify_group_admin(group_openid, member_openid):
        try:
            group_info = await group_db.get_group_info(group_openid)
            await group_db.group_del(group_openid)
            print("超级管理员:", member_openid, "删除群:", group_openid, "群名称:", group_info["群名称"])
            await message.reply(content="\n" + "QID:" + group_openid + '\n' + "群名称:" + group_info["群名称"] + '\n' + "创建时间:" + group_info["创建时间"] + '\n' + "删除成功")
        except KeyError:
            await message.reply(content="\n"+"不存在此群的QID(已删除或不存在)")
    else:
        print("一个非超级管理员用户使用超级管理员命令", "QID:", member_openid)
        await message.reply(content="\n"+"您并非超级管理员, 如需使用此命令请您联系超级管理员")

@Commands("绑定管理员")
async def group_admin_add(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()
    member_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid
    command = msg.split("绑定管理员")[1].strip().split()
    try:
        password = await group_db.get_group_admin_password(group_openid) 
    except KeyError:
        await message.reply(content="\n"+ "请先绑定本群")
        return
    if password == command[0]:
        print("群ID:", group_openid, "绑定管理员", member_openid, "绑定成功")
        await group_db.group_admin_add(group_openid, member_openid)
        await message.reply(content="\n"+"QID:" + member_openid + '\n' + "绑定成功")
    else:
        print("群ID:", group_openid, "绑定管理员", member_openid, "绑定失败")
        await message.reply(content="\n"+"您输入的密码不正确")

@Commands("本群信息")
async def group_get_info(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()
    member_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid
    try:
        if await group_db.verify_group_admin(group_openid, member_openid) or await config.verify_admin(member_openid):
            group_info = await group_db.get_group_info(group_openid)
            await message.reply(content="\n"+"群名称:" + group_info["群名称"] + '\n' + "群文件:" + group_info["群文件"] + '\n' + '群QID:' + group_openid)
        else:
            await message.reply(content="\n"+"您并非超级管理员或管理员, 无法使用此命令")
    except KeyError:
            await message.reply(content="\n"+"数据库中不存在本群信息, 可能因为未绑定")

@Commands("登录超级管理员")
async def bind_super_admin(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()

    input_password = msg.split("登录超级管理员")[1].strip()
    member_openid = raw_msg.author.member_openid
    password = await config.get_super_admin_passwd()
    print("正在添加超级管理员", "当前超级管理员权限密码:", password, "用户输入密码:", input_password)
    if not await config.verify_admin(member_openid):
        if input_password == password:
            await config.admin_add(member_openid)
            await message.reply(content="\n"+"登录超级管理员身份成功")
        else:
            await message.reply(content="\n"+"登陆超级管理员身份失败\n密码错误")
    else:
        await message.reply(content="\n"+"您已是超级管理员身份")

@Commands("退出超级管理员")
async def del_bind_super_admin(api: BotAPI, message: Message, params=None):
    raw_msg = message
    msg = raw_msg.content.strip()
    member_openid = raw_msg.author.member_openid
    if not await config.verify_admin(member_openid):
        print("一个没有超级管理员身份的用户尝试退出超级管理员:", member_openid)
        await message.reply(content="\n"+"你没有超级管理员身份")
    else:
        await config.admin_del(member_openid)
        print("超级管理员:", member_openid, "退出")
        await message.reply(content="\n"+"超级管理员身份已退出")
  
@Commands("top")
async def top(api: BotAPI, message: Message, params=None):
    # 如果使用 self.api 则会无法判断是群还是私聊
    msg = message
    await message.reply(content=f"\n当前服务器负载:\n{systeminfo()}")
    return True # 如果没有返回则会触发去重 msg_seq

@Commands("新建任务")
async def newtask(api: BotAPI, message: Message, params=None):
    global image_data
    raw_msg = message
    msg = raw_msg.content.strip()
    user_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid
    command = msg.split("新建任务")[1].strip().split() # 第一个参数接收 是学院还是群 第二个参数接收 任务名字 第三个参数接收 匹配精度 第四个参数接收 任务备注

    try:
        if command[0] == "学院":
            try:
                task_remark = command[3]
            except IndexError:
                task_remark = "无"

            if await config.verify_admin(user_openid):
                if command[2] == "False":
                    base = False
                else:
                    try:
                        base = float(command[2])
                    except ValueError:
                        await message.reply(content='\n' + "您基于的精度并非小数也并非False")
                        return
                task_id = await config.newtask(command[1], base, task_remark)
                makedirs(f'db/学院/{command[1]}-{task_id}', exist_ok=True)
                async with lock:
                    image_data[_group][task_id] = {} # 新建一个缓存任务, 关闭程序则自动退出
                await message.reply(content='\n' + "新建学院任务成功"+ '\n' + '任务:' + command[1] + '\n' + '精度:' + command[2] + '\n' + '任务ID:' + str(task_id) + '\n' + '备注:' + task_remark)
            else:
                await message.reply(content='\n' + "您并非超级管理员无法使用此命令")
                return
        elif command[0] == "群":
            try:
                task_remark = command[3]
            except IndexError:
                task_remark = "无"

            try:
                if await group_db.verify_group_admin(group_openid, user_openid) or await config.verify_admin(user_openid):
                    if command[2] == "False":
                        base = False
                    else:
                        try:
                            base = float(command[2])
                        except ValueError:
                            await message.reply(content='\n' + "您基于的精度并非小数也并非False")
                            return

                    try:
                        group_info = await group_db.get_group_info(group_openid)
                    except KeyError:
                        await message.reply(content='\n' + "本群未进行绑定, 请联系管理员或超级管理员进行绑定本群再次操作")
                        return

                    task_id = await group_db.newtask(group_openid, command[1], base, task_remark)
                    makedirs(f'db/群/{group_info["群名称"]}-{group_openid}/{command[1]}-{task_id}', exist_ok=True)
                    async with lock:
                        image_data[_class][task_id] = {} # 新建一个缓存任务, 关闭程序则自动退出
                    await message.reply(content='\n' + "新建群任务成功"+ '\n' '群:' + group_info['群名称'] + '\n' + '任务:' + command[1] + '\n' + '精度:' + command[2] + '\n' + '任务:ID:' + str(task_id) + '\n' + '备注:' + task_remark)

                else:
                    await message.reply(content='\n' + "您并非管理员或超级管理员无法使用此命令")
                    return
            except KeyError:
                await message.reply(content='\n' + "本群尚未绑定群, 请先联系管理员绑定")
        else:
            await message.reply(content='\n' + "新建的任务不属于学院也不属于群")
            return
    except IndexError:
        await message.reply(content='\n' + "任务参数缺少或传输错误某项 [0]")


"""

@Commands("新建任务")
async def newtask(api: BotAPI, message: Message, params=None):
    global image_data
    raw_msg = message
    msg = raw_msg.content.strip()
    user_openid = raw_msg.author.member_openid
    group_openid = raw_msg.group_openid
    command = msg.split("新建任务")[1].strip().split() # 第一个参数接收 是学院还是群 第二个参数接收 任务名字 第三个参数接收 匹配精度 第四个参数接收 任务备注

    try:
        if command[0] == "学院":
            try:
                task_remark = command[3]
            except IndexError:
                task_remark = "无"

            if await config.verify_admin(user_openid):
                if command[2] == "False":
                    base = False
                else:
                    try:
                        base = float(command[2])
                    except ValueError:
                        await message.reply(content='\n' + "您基于的精度并非小数也并非False")
                        return
                task_id = await config.newtask(command[1], base, task_remark)
                makedirs(f'db/学院/{command[1]}-{task_id}', exist_ok=True)
                async with lock:
                    image_data[_group][task_id] = {} # 新建一个缓存任务, 关闭程序则自动退出
                await message.reply(content='\n' + "新建学院任务成功"+ '\n' + '任务:' + command[1] + '\n' + '精度:' + command[2] + '\n' + '任务ID:' + str(task_id) + '\n' + '备注:' + task_remark)
            else:
                await message.reply(content='\n' + "您并非超级管理员无法使用此命令")
                return
        elif command[0] == "群":
            try:
                task_remark = command[3]
            except IndexError:
                task_remark = "无"

            try:
                if await group_db.verify_group_admin(group_openid, user_openid) or await config.verify_admin(user_openid):
                    if command[2] == "False":
                        base = False 
                    else:
                        try:
                            base = float(command[2])
                        except ValueError:
                            await message.reply(content='\n' + "您基于的精度并非小数也并非False")
                            return

                    try:
                        group_info = await group_db.get_group_info(group_openid)
                    except KeyError:
                        await message.reply(content='\n' + "本群未进行绑定, 请联系管理员或超级管理员进行绑定本群再次操作")
                        return

                    task_id = await group_db.newtask(group_openid, command[1], base, task_remark)
                    makedirs(f'db/群/{command[1]}-{task_id}', exist_ok=True)
                    async with lock:
                        image_data[_class][task_id] = {} # 新建一个缓存任务, 关闭程序则自动退出
                    await message.reply(content='\n' + "新建群任务成功"+ '\n' '群:' + group_info['群名称'] + '\n' + '任务:' + command[1] + '\n' + '精度:' + command[2] + '\n' + '任务:ID:' + str(task_id) + '\n' + '备注:' + task_remark)

                else:
                    await message.reply(content='\n' + "您并非管理员或超级管理员无法使用此命令")
                    return
            except KeyError:
                await message.reply(content='\n' + "本群尚未绑定群, 请先联系管理员绑定")
        else:
            await message.reply(content='\n' + "新建的任务不属于学院也不属于群")
            return
    except IndexError:
        await message.reply(content='\n' + "任务参数缺少或传输错误某项 [0]")

"""
@Commands("_submit")
async def subsssssss(api: BotAPI, message: Message, params=None):
    global global_task
    # 如果使用 self.api 则会无法判断是群还是私聊
    msg = message
    raw_message = msg.content.strip().split()

    with open("task.json", "r", encoding="utf-8") as fp:
        task_dict = loads(fp.read())
        task_list = list(task_dict.keys())
        if raw_message[-1] != "submit" and raw_message[-1] != "/submit":
            task = raw_message[1]
        else:
            task = task_dict[task_list[0]]
    try:
        _id = msg.author.member_openid
    except:
        _id = msg.author.user_openid

    name = usertools.user_search(_id)
    try:
        raw_message[1] = name
    except IndexError:
        raw_message.append(name)
    try:
        task = int(task)
        task = search_task(task_dict, task)
    except ValueError:
        pass

    if task:
        if istrue(task_list, task) :

            try:
                name_list = readname(f"name/{classroom}.txt")
                if istrue(name_list, name):
                    #xuehao = msg.content.strip().split()[-1]
                    img_url = msg.attachments[0].url
                    #download(url=img_url, name=f"{task}/{name}-{xuehao}")
                    download(url=img_url, name=f"{task}/{name}")
                    img_data = array(Image.open(rf"db/{task}/{name}.jpg").convert('L')) # 转化为 灰度
                    if not name in global_task[task]['name']:
                        global_task[task]['name'].append(name)

                    n = 0
                    for i in global_task[task]['img_data']:
                        similarity = image_detection(img_data, i)
                        print("相似度:", similarity)
                        if similarity > 0.9 and name != global_task[task]['name'][n]:
                            await message.reply(content=f"\n{name}同志,禁止复制{global_task[task]['name'][n]}同志\n相似度达到{round(similarity, 2) * 100}%")
                            delete_file(rf"db/{task}/{name}.jpg")
                            global_task[task]['name'].remove(name)
                            return True
                        n += 1

                    # if not name in global_task[task]['name']:
                    #     global_task[task]['img_data'].append(img_data)

                    try:
                        global_task[task]['img_data'][global_task[task]['name'].index(name)] = img_data
                    except:
                        global_task[task]['img_data'].append(img_data)
                    result_name_list = set(readname(f"name/{classroom}.txt")) - set(read_filename(f"db/{task}/"))
                    result = {item for item in result_name_list if item != ''}
                    result_name = formar_names(result, 3)
                    get_number = get_len_number(f"db/{task}")
                    not_submit = len(result_name_list)  -1
                    if not_submit <= 10 and result_name:
                        await message.reply(content=f"\n你的名字:{name}\n提交时间:\n{str(datetime.now()).split('.')[0]}\n已录入\n剩余未交:{not_submit}人\n以下同志未交:\n{result_name}")
                    elif not_submit <= 10 and not result_name:
                        show_image = encode_chinese_url(f"http://154.83.95.52:8080/{task}/物联网2407.html")
                        await message.reply(content=f"\n你的名字:{name}\n提交时间:\n{str(datetime.now()).split('.')[0]}\n已录入\nTask:\n{task}\nDone.\n使用下方链接进行检查:\n{show_image}")
                    else:
                        await message.reply(content=f"\n你的名字:{name}\n提交时间:\n{str(datetime.now()).split('.')[0]}\n已录入\n剩余未交:{not_submit}人")

                else:
                    await message.reply(content=f"\n你的名字:{name}\n提交时间:\n{str(datetime.now()).split('.')[0]}\n群没有此人")
            except IndexError:
                await message.reply(content=f"\n你的名字:{name}\n提交时间:\n{str(datetime.now()).split('.')[0]}\n未成功 没有提交图片")
        else:
            await message.reply(content=f"\n提交时间:\n{str(datetime.now()).split('.')[0]}\n未成功 不存在该任务")
    else:
        await message.reply(content=f"\n 没有该任务")


    return True


class MyClient(botpy.Client):
    async def on_c2c_message_create(self, message: C2CMessage):
        handlers = [ # 注册装饰器命令
            top, # 查看服务器负载
            sub,
            newtask,
            group_class_password_set, # 修改群密码
            group_class_student_password_set, # 管理员修改群对应的用户密码
            random_names,
        ]

        for handler in handlers:
            if await handler(api=self.api, message=message):
                return

        raw_msg = message
        msg = message.content.strip()
        user_openid = raw_msg.author.user_openid
        print("[私聊消息]", "用户ID:", user_openid, "消息:", msg)

        """
        local_command = ["设置群密码", "设置用户密码"]
        for i in local_command:
            if i in  msg:
                return

        html_text = markdown(py.ai.chat_with_robot(msg))
        plain_text = re.sub(r'<[^>]+>', lambda L: '\n' if 'blockquote' in L.group(0) else ' ', html_text)
        await message.reply(content=f"{plain_text}")
        """

    async def on_group_at_message_create(self, message: Message):
        handlers = [ # 注册装饰器命令
            top, # 查看服务器负载
            newtask,
            bind_super_admin,
            del_bind_super_admin,
            group_add,
            group_del,
            group_admin_add,
            group_get_info,
            group_del_ben,
            class_group_student,
            group_bind_student,
            task_show,
            submit,
            sub,
            count,
            changing_matching_degree,
            task_del,
            random_names,
        ]
        for handler in handlers:
            if await handler(api=self.api, message=message):
                return

        raw_msg = message
        msg = message.content.strip()
        group_openid = raw_msg.group_openid
        member_openid = raw_msg.author.member_openid
        print("[群聊消息]", "群QID:", group_openid, "用户ID:", member_openid, "消息:", msg)
        local_command = ["登录超级管理员", "退出超级管理员", "绑定群", "删除群", "绑定管理员", "本群信息", "删除本群", "我的信息", "绑定用户", "新建任务", "查看任务", "/submit", "submit", "sub", "/sub", "更改匹配度", "删除任务", "统计任务"]

        """
        /submit = submit 代表提交群任务
        /sub = sub 代表提交学院任务
        """

        """
        for i in local_command:
            if i in  msg:
                return

        html_text = markdown(py.ai.chat_with_robot(msg))
        plain_text = re.sub(r'<[^>]+>', lambda L: '\n' if 'blockquote' in L.group(0) else ' ', html_text)
        await message.reply(content=f"\n{plain_text}")
        """

if __name__ == "__main__":
    with open("config.json", "r", encoding="utf-8") as f:
        _config = load(f)

    intents =  botpy.Intents.all()
    client = MyClient(intents=intents)
    client.run(_config["Argentina"], _config["secret"])
