import botpy
from botpy.types.message import Message
from botpy.types.message import Reference   # 该模块为引用回复暂时没用
from botpy.message import C2CMessage

# 以下为注册命令所用模块
from botpy import logging, BotAPI
from botpy.ext.command_util import Commands
from botpy.types.message import Ark, ArkKv


# 以下为自写模块
from py.systeminfo import *
from py.downimg import *
from py.packzip import *
from py.toolsname import *
from py.writename import *

# 以下为系统模块
from datetime import datetime
from base64 import b64encode
from json import loads, dump
from os import makedirs



with open("conf.json", "r", encoding="utf-8") as fp:
    conf=loads(fp.read())
    Argentina = conf['Argentina']
    secret = conf['secret']
    classroom = conf['classroom']

def add_task(task_dict:dict, new_task:str):
    existing_values = set(task_dict.values())
    new_value = 1
    while new_value in existing_values:
        new_value += 1
    task_dict[new_task] = new_value

    return new_value

def create_directory(directory_path):
    try:
        # 使用 os.makedirs 创建目录，exist_ok=True 参数表示如果目录已经存在则不抛出异常
        makedirs(directory_path, exist_ok=True)
        print(f"目录 '{directory_path}' 已创建或已存在。")
    except Exception as e:
        print(f"创建目录时发生错误: {e}")


def search_task(raw_dict: dict, number:int):
    for key, value in raw_dict.items():
        if value == number:
            return key
            break
    else:
        return False

@Commands("top")
async def top(api: BotAPI, message: Message, params=None):
    # 如果使用 self.api 则会无法判断是群还是私聊
    msg = message
    await message.reply(content=f"\n当前服务器负载:\n{systeminfo()}")
    return True # 如果没有返回则会触发去重 msg_seq

@Commands("count")
async def count(api: BotAPI, message: Message, params=None):
    msg = message
    raw_message = msg.content.strip().split()
    _, task = [i for i in raw_message if i != ""] 

    with open("task.json", "r") as fp:
        task_dict = loads(fp.read())
        task_list = list(task_dict.keys())
    try:
        task = int(task)
        task = search_task(task_dict, task)
    except ValueError:
        pass

    try:
        if task:
            result = set(readname(f"name/{classroom}.txt")) - set(read_filename(f"db/{task}/"))
            result = {item for item in result if item != ''}
            result_name = formar_names(result, 3)
            get_number = get_len_number(f"db/{task}")

            if not result:
                await message.reply(content=f"\n{task} 任务 已全部收集完毕.")
            else:
                print(result)
                await message.reply(content=f"\n{task} 任务\n以下人员未交:\n{result_name}\n\n已提交 {get_number} 份.\n未交 {len(result)} 份.")
        else:
            await message.reply(content=f"\n 没有该任务")
    except FileNotFoundError:
            await message.reply(content=f"\n 没有该任务")

    return True


@Commands("newtask")
async def newtask(api: BotAPI, message: Message, params=None):
    msg = message
    new_task = msg.content.split("newtask")[-1].strip()

    if len(new_task) > 0:

        with open("task.json", "r") as fp:
            task_dict = loads(fp.read())
            task_list = list(task_dict.keys())
            if not istrue(task_list, new_task):
                # task_dict[new_task] = len(task_list)+1
                ID = add_task(task_dict, new_task)
                with open("task.json", "w") as fp:
                    dump(task_dict, fp, ensure_ascii=False, indent=4)
                create_directory(f"db/{new_task}")
                await message.reply(content=f"\n已添加 {new_task} 任务ID:{ID}")
            else:
                await message.reply(content=f"\n已存在此任务,请完成后或删除后再次添加.")
        return True
    else:
        await message.reply(content=f"\n请提交任务名称.")
        return True 

@Commands("tasklist")
async def tasklist(api: BotAPI, message: Message, params=None):
    with open("task.json", "r") as fp:
        task_dict = loads(fp.read())
        task_list = list(task_dict.keys())

    result = []

    # 遍历字典中的每个键值对
    for task_name, task_id in task_dict.items():
        # 格式化当前键值对
        formatted_line = f"{task_name} 任务ID:{task_id}"
        # 将格式化后的字符串添加到结果列表中
        result.append(formatted_line)

    # 将结果列表合并为一个字符串，每行一个任务
    formatted_string = '\n'.join(result)
    if len(formatted_string) == 0:
        await message.reply(content=f"\n无任务")
    else:
        await message.reply(content=f"\n当前任务如下:\n{formatted_string}")
    return True

@Commands("clear")
async def clears(api: BotAPI, message: Message, params=None):
    msg = message
    raw_message = msg.content.strip().split()
    _, task = [i for i in raw_message if i != ""] 

    with open("task.json", "r") as fp:
        task_dict = loads(fp.read())
        task_list = list(task_dict.keys())
    try:
        task = int(task)
        task = search_task(task_dict, task)
    except ValueError:
        pass

    try:
        if task:
            del task_dict[task]
            with open("task.json", "w") as fp:
                dump(task_dict, fp, ensure_ascii=False, indent=4)
            delete_directory(f"db/{task}")
            
            await message.reply(content=f"\n已清除 {task} 任务缓存")
        else:
            await message.reply(content=f"\n 没有该任务")
    except KeyError:
            await message.reply(content=f"\n 没有该任务")
    return True


@Commands("help")
async def helps(api: BotAPI, message: Message, params=None):
    await message.reply(content=
                        """
/pack /count/ /submit /clear 都具有指定任务ID的功能
/newtask 大学习\n(新建一个大学习任务)\n
/count 大学习\n(查看大学习收集情况)\n
/count 1\n(同上 当青年大学习任务1时)\n
/tasklist\n(查看任务对应 ID)\n
/submit 大学习 张三\n(提交大学习名字叫张三的截图,需提供一张截图)\n
/submit 1 张三\n(同上 当青年大学习任务1时)\n
/pack 大学习\n(打包已收集的大学习任务)\n
/clear 大学习 或 1\n(删除青年大学习缓存)""")
    return True

@Commands("pack")
async def pack(api: BotAPI, message: Message, params=None):
    msg = message
    raw_message = msg.content.strip().split()
    _, task = [i for i in raw_message if i != ""] 

    with open("task.json", "r") as fp:
        task_dict = loads(fp.read())
        task_list = list(task_dict.keys())
    try:
        task = int(task)
        task = search_task(task_dict, task)
    except ValueError:
        pass
    if task:
        print(classroom)
        process_images_in_directory(f"db/{task}", classroom)
        create_zip_from_folder(f"db/{task}/", f"db/zip/{classroom}-{task}.zip")
        await message.reply(content=f"\n已打包 {task} 任务.\n 请使用专用下载器下载.") 
    else:
        await message.reply(content=f"\n没有该任务")
    return True

@Commands("submit")
async def sub(api: BotAPI, message: Message, params=None):
    # 如果使用 self.api 则会无法判断是群还是私聊
    msg = message
    raw_message = msg.content.strip().split()

    _, task, name  = [i for i in raw_message if i != ""] 

    with open("task.json", "r") as fp:
        task_dict = loads(fp.read())
        task_list = list(task_dict.keys())

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
                    img_url = msg.attachments[0].url
                    download(url=img_url, name=f"{task}/{name}")
                    await message.reply(content=f"\n你的名字:{name}\n提交时间:\n{str(datetime.now()).split('.')[0]}\n已录入")
                else:
                    await message.reply(content=f"\n你的名字:{name}\n提交时间:\n{str(datetime.now()).split('.')[0]}\n班级没有此人")
            except IndexError:
                await message.reply(content=f"\n你的名字:{name}\n提交时间:\n{str(datetime.now()).split('.')[0]}\n未成功 没有提交图片")
            return True # 如果没有返回则会触发去重 msg_seq
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
            count,
            helps,
            pack,
            clears,
            newtask,
            tasklist,
        ]

        for handler in handlers:
            if await handler(api=self.api, message=message):
                return

        msg = message
        await message.reply(content=f"机器人{self.robot.name}收到你的@消息了: {message.content}")

    async def on_group_at_message_create(self, message: Message):
        handlers = [ # 注册装饰器命令
            top, # 查看服务器负载
            sub,
            count,
            helps,
            pack,
            clears,
            newtask,
            tasklist,
        ]
        for handler in handlers:
            if await handler(api=self.api, message=message):
                return

        msg = message
        await message.reply(content=f"机器人{self.robot.name}收到你的@消息了: {message.content} [CQ:at,qq=2759372655]")

if __name__ == "__main__":
    with open("task.json", "r", encoding="utf-8") as fp:
        task_dict = loads(fp.read())
        task_list = list(task_dict.keys())
    for i in task_list:
        create_directory(f"db/{i}")

    intents =  botpy.Intents.all()
    client = MyClient(intents=intents)
    client.run(Argentina, secret)
