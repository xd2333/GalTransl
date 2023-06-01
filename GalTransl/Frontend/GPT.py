"""
GPT3.5 / 4 / New Bing 前端翻译的控制逻辑
"""
from os.path import join as joinpath
from os.path import exists as isPathExists
from os import makedirs as mkdir
from os import listdir
from GalTransl.Backend.GPT3Translate import CGPT35Translate
from GalTransl.Backend.GPT4Translate import CGPT4Translate
from GalTransl.Backend.BingGPT4Translate import CBingGPT4Translate
from GalTransl.ConfigHelper import initDictList
from GalTransl.Loader import load_transList_from_json_jp
from GalTransl.Dictionary import CGptDict, CNormalDic
from GalTransl.Problem import find_problems
from GalTransl.Cache import save_transCache_to_json
from GalTransl.Name import load_name_table
from GalTransl.CSerialize import save_transList_to_json_cn
from GalTransl.Problem import CTranslateProblem
from GalTransl.Dictionary import CNormalDic, CGptDict
from GalTransl.ConfigHelper import CProjectConfig, initDictList
from os import listdir

GPT3_PROBLEMS = [
    CTranslateProblem.词频过高,
    CTranslateProblem.本无括号,
    CTranslateProblem.本无引号,
    CTranslateProblem.残留日文,
    CTranslateProblem.丢失换行,
    CTranslateProblem.多加换行,
    CTranslateProblem.比日文长,
]

GPT4_PROBLEMS = [
    CTranslateProblem.词频过高,
    CTranslateProblem.本无括号,
    CTranslateProblem.本无引号,
    CTranslateProblem.残留日文,
    CTranslateProblem.丢失换行,
    CTranslateProblem.多加换行,
]

BINGGPT4_PROBLEMS = [
    CTranslateProblem.词频过高,
    CTranslateProblem.本无括号,
    CTranslateProblem.本无引号,
    CTranslateProblem.残留日文,
    CTranslateProblem.丢失换行,
    CTranslateProblem.多加换行,
]

arinashi_dict = {}


def doGPT3Translate(projectConfig: CProjectConfig) -> bool:
    # 加载字典
    pre_dic = CNormalDic(
        initDictList(
            projectConfig.getDictCfgSection()["preDict"],
            projectConfig.getProjectDir(),
        )
    )
    post_dic = CNormalDic(
        initDictList(
            projectConfig.getDictCfgSection()["postDict"],
            projectConfig.getProjectDir(),
        )
    )
    gpt_dic = CGptDict(
        initDictList(
            projectConfig.getDictCfgSection()["gpt.dict"],
            projectConfig.getProjectDir(),
        )
    )

    gptapi = CGPT35Translate(projectConfig)

    for dir_path in [
        projectConfig.getInputPath(),
        projectConfig.getOutputPath(),
        projectConfig.getCachePath(),
    ]:
        if not isPathExists(dir_path):
            mkdir(dir_path)
    for file_name in listdir(projectConfig.getInputPath()):
        # 1、初始化trans_list
        trans_list = load_transList_from_json_jp(
            joinpath(projectConfig.getInputPath(), file_name)
        )

        # 2、翻译前处理
        for i, tran in enumerate(trans_list):
            tran.analyse_dialogue()  # 解析是否为对话
            tran.post_jp = pre_dic.do_replace(tran.post_jp, tran)  # 译前字典替换

        # 3、读出未命中的Translate然后批量翻译
        cache_file_path = joinpath(projectConfig.getCachePath(), file_name)
        gptapi.batch_translate(
            file_name,
            cache_file_path,
            trans_list,
            projectConfig.getKey("gpt.numPerRequestTranslate"),
            retry_failed=projectConfig.getKey("retryFail"),
            chatgpt_dict=gpt_dic,
        )

        # 4、翻译后处理
        for i, tran in enumerate(trans_list):
            tran.some_normal_fix()
            tran.recover_dialogue_symbol()  # 恢复对话框
            tran.post_zh = post_dic.do_replace(tran.post_zh, tran)  # 译后字典替换

        # 用于保存problems
        find_problems(trans_list, find_type=GPT3_PROBLEMS, arinashi_dict=arinashi_dict)
        save_transCache_to_json(trans_list, cache_file_path)
        # 5、整理输出
        if isPathExists(joinpath(projectConfig.getProjectDir(), "人名替换表.csv")):
            name_dict = load_name_table(
                joinpath(projectConfig.getProjectDir(), "人名替换表.csv")
            )
        else:
            name_dict = {}
        save_transList_to_json_cn(
            trans_list, joinpath(projectConfig.getOutputPath(), file_name), name_dict
        )
    pass


def doGPT4Translate(projectConfig: CProjectConfig) -> bool:
    # 加载字典
    pre_dic = CNormalDic(
        initDictList(
            projectConfig.getDictCfgSection()["preDict"],
            projectConfig.getProjectDir(),
        )
    )
    post_dic = CNormalDic(
        initDictList(
            projectConfig.getDictCfgSection()["postDict"],
            projectConfig.getProjectDir(),
        )
    )
    gpt_dic = CGptDict(
        initDictList(
            projectConfig.getDictCfgSection()["gpt.dict"],
            projectConfig.getProjectDir(),
        )
    )

    gptapi = CGPT4Translate(projectConfig)

    for dir_path in [
        projectConfig.getInputPath(),
        projectConfig.getOutputPath(),
        projectConfig.getCachePath(),
    ]:
        if not isPathExists(dir_path):
            mkdir(dir_path)
    for file_name in listdir(projectConfig.getInputPath()):
        # 1、初始化trans_list
        trans_list = load_transList_from_json_jp(
            joinpath(projectConfig.getInputPath(), file_name)
        )

        # 2、翻译前处理
        for i, tran in enumerate(trans_list):
            tran.analyse_dialogue()  # 解析是否为对话
            tran.post_jp = pre_dic.do_replace(tran.post_jp, tran)  # 译前字典替换

        # 3、读出未命中的Translate然后批量翻译
        cache_file_path = joinpath(projectConfig.getCachePath(), file_name)

        gptapi.batch_translate(
            file_name,
            cache_file_path,
            trans_list,
            projectConfig.getKey("gpt.numPerRequestTranslate"),
            retry_failed=projectConfig.getKey("retryFail"),
            chatgpt_dict=gpt_dic,
            proofread=True,
        )
        if projectConfig.getKey("gpt.enableProofRead"):
            gptapi.batch_translate(
                file_name,
                cache_file_path,
                trans_list,
                projectConfig.getKey("gpt.numPerRequestProofRead"),
                retry_failed=projectConfig.getKey("retryFail"),
                chatgpt_dict=gpt_dic,
            )

        # 4、翻译后处理
        for i, tran in enumerate(trans_list):
            tran.some_normal_fix()
            tran.recover_dialogue_symbol()  # 恢复对话框
            tran.post_zh = post_dic.do_replace(tran.post_zh, tran)  # 译后字典替换

        # 用于保存problems
        find_problems(trans_list, find_type=GPT4_PROBLEMS, arinashi_dict=arinashi_dict)
        save_transCache_to_json(trans_list, cache_file_path)

        # 5、整理输出
        if isPathExists(joinpath(projectConfig.getProjectDir(), "人名替换表.csv")):
            name_dict = load_name_table(
                joinpath(projectConfig.getProjectDir(), "人名替换表.csv")
            )
        else:
            name_dict = {}
        save_transList_to_json_cn(
            trans_list, joinpath(projectConfig.getOutputPath(), file_name), name_dict
        )

    pass


def doNewBingTranslate(projectConfig: CProjectConfig) -> bool:
    # 加载字典
    pre_dic = CNormalDic(
        initDictList(
            projectConfig.getDictCfgSection()["preDict"],
            projectConfig.getProjectDir(),
        )
    )
    post_dic = CNormalDic(
        initDictList(
            projectConfig.getDictCfgSection()["postDict"],
            projectConfig.getProjectDir(),
        )
    )
    gpt_dic = CGptDict(
        initDictList(
            projectConfig.getDictCfgSection()["gpt.dict"],
            projectConfig.getProjectDir(),
        )
    )

    cookieList: list[str] = []
    for i in projectConfig.getBackendConfigSection("newBing")["cookiePath"]:
        cookieList.append(joinpath(projectConfig.getProjectDir(), i))

    gptapi = CBingGPT4Translate(projectConfig, cookieList)

    for dir_path in [
        projectConfig.getInputPath(),
        projectConfig.getOutputPath(),
        projectConfig.getCachePath(),
    ]:
        if not isPathExists(dir_path):
            mkdir(dir_path)

    for file_name in listdir(projectConfig.getInputPath()):
        # 1、初始化trans_list
        trans_list = load_transList_from_json_jp(
            joinpath(projectConfig.getInputPath(), file_name)
        )

        # 2、翻译前处理
        for i, tran in enumerate(trans_list):
            tran.analyse_dialogue()  # 解析是否为对话
            tran.post_jp = pre_dic.do_replace(tran.post_jp, tran)  # 译前字典替换

        # 3、读出未命中的Translate然后批量翻译
        cache_file_path = joinpath(projectConfig.getCachePath(), file_name)
        gptapi.batch_translate(
            file_name,
            cache_file_path,
            trans_list,
            projectConfig.getKey("gpt.numPerRequestTranslate"),
            retry_failed=projectConfig.getKey("retryFail"),
            chatgpt_dict=gpt_dic,
        )
        if projectConfig.getKey("gpt.enableProofRead"):
            gptapi.batch_translate(
                file_name,
                cache_file_path,
                trans_list,
                projectConfig.getKey("gpt.numPerRequestProofRead"),
                retry_failed=projectConfig.getKey("retryFail"),
                chatgpt_dict=gpt_dic,
                proofread=True,
            )

        # 4、翻译后处理
        for i, tran in enumerate(trans_list):
            tran.some_normal_fix()
            tran.recover_dialogue_symbol()  # 恢复对话框
            tran.post_zh = post_dic.do_replace(tran.post_zh, tran)  # 译后字典替换

        # 用于保存problems
        find_problems(
            trans_list, find_type=BINGGPT4_PROBLEMS, arinashi_dict=arinashi_dict
        )
        save_transCache_to_json(trans_list, cache_file_path)

        # 5、整理输出
        if isPathExists(joinpath(projectConfig.getProjectDir(), "人名替换表.csv")):
            name_dict = load_name_table(
                joinpath(projectConfig.getProjectDir(), "人名替换表.csv")
            )
        else:
            name_dict = {}
        save_transList_to_json_cn(
            trans_list, joinpath(projectConfig.getOutputPath(), file_name), name_dict
        )

    pass
