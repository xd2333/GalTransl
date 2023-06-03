import os
from GalTransl.ConfigHelper import CProjectConfig
from GalTransl.Runner import run_galtransl
from GalTransl import LOGGER, PROGRAM_SPLASH, CONFIG_FILENAME,TRANSLATOR_SUPPORTED

print(PROGRAM_SPLASH)

project_dir = input("请输入项目文件夹路径，或拖入项目文件夹：")
while not os.path.exists(os.path.join(project_dir, CONFIG_FILENAME)):
    print(f"项目文件夹内不存在配置文件{CONFIG_FILENAME}，请检查后重新输入\n")
    project_dir = input("请输入项目文件夹路径，或拖入项目文件夹：")

print()
print("可选翻译器：")
for translator in TRANSLATOR_SUPPORTED:
    print(f"    {translator}")

translator = input("请输入翻译器：")
while translator not in TRANSLATOR_SUPPORTED:
    print(f"翻译器{translator}不在支持列表，请重新输入\n")
    translator = input("请输入翻译器：")

cfg = CProjectConfig(project_dir)


run_galtransl(cfg, translator)
