import os
import time

member_path = r'E:\爬虫\twitter'


def count_time(fun):
    def warpper(*args, **kwargs):
        s_time = time.time()
        arg = args[1] if len(args) > 1 else '-'
        res = fun(*args, **kwargs)
        e_time = time.time()
        t_time = int(e_time - s_time) // 60
        # print('%s耗时：%s,参数:%s' % (fun.__name__, t_time, arg))
        print('%s耗时：%s' % (fun.__name__, t_time))
        return res

    return warpper


def get_save_dir(unique_username):
    dir_list = os.listdir(member_path)
    for dir in dir_list:
        if unique_username in dir:
            return dir
