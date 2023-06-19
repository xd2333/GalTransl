import os

from command import BulletMenu
from GalTransl import (
    AUTHOR,
    CONFIG_FILENAME,
    CONTRIBUTORS,
    GALTRANSL_VERSION,
    PROGRAM_SPLASH,
    TRANSLATOR_SUPPORTED,
)
from GalTransl.ConfigHelper import CProjectConfig
from GalTransl.Runner import run_galtransl

print(PROGRAM_SPLASH)
print(f"GalTransl version: {GALTRANSL_VERSION}")
print(f"Author: {AUTHOR}")
print(f"Contributors: {CONTRIBUTORS}\n")

project_dir = input("请输入项目文件夹路径，或拖入项目文件夹：")
while not os.path.exists(os.path.join(project_dir, CONFIG_FILENAME)):
    print(f"项目文件夹内不存在配置文件{CONFIG_FILENAME}，请检查后重新输入\n")
    project_dir = input("请输入项目文件夹路径，或拖入项目文件夹：")

os.system("")   # 解决cmd的ANSI转义bug 
translator = BulletMenu("翻译器：", TRANSLATOR_SUPPORTED).run()

cfg = CProjectConfig(project_dir)
run_galtransl(cfg, translator)
