"""
GPT3.5 / 4 / New Bing 前端翻译的控制逻辑
"""
from os.path import join as joinpath
from os.path import exists as isPathExists
from os import makedirs as mkdir
from os import listdir
from typing import Optional
from asyncio import Semaphore, gather
from time import time
import traceback
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
from GalTransl.ConfigHelper import CProjectConfig, initDictList, CProxyPool
from GalTransl.COpenAI import COpenAITokenPool
from GalTransl import LOGGER


async def doGPT3TranslateSingleFile(
    semaphore: Semaphore,
    file_name: str,
    projectConfig: CProjectConfig,
    type: str,
    pre_dic: CNormalDic,
    post_dic: CNormalDic,
    gpt_dic: CGptDict,
    gptapi: CGPT35Translate,
) -> bool:
    async with semaphore:
        st = time()
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

        await gptapi.batch_translate(
            file_name,
            cache_file_path,
            trans_list,
            projectConfig.getKey("gpt.numPerRequestTranslate"),
            retry_failed=projectConfig.getKey("retranslFail"),
            gptdict=gpt_dic,
            retran_key=projectConfig.getKey("retranslKey"),
        )

        # 4、翻译后处理
        for i, tran in enumerate(trans_list):
            tran.some_normal_fix()
            tran.recover_dialogue_symbol()  # 恢复对话框
            tran.post_zh = post_dic.do_replace(tran.post_zh, tran)  # 译后字典替换

    # 用于保存problems
    arinashi_dict = projectConfig.getProblemAnalyzeArinashiDict()
    find_problems(
        trans_list,
        find_type=projectConfig.getProblemAnalyzeConfig("GPT35"),
        arinashi_dict=arinashi_dict,
    )
    save_transCache_to_json(trans_list, cache_file_path, post_save=True)
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
    et = time()
    LOGGER.info(f"文件 {file_name} 翻译完成，用时 {st-st}s.")


async def doGPT3Translate(
    projectConfig: CProjectConfig,
    tokenPool: COpenAITokenPool,
    proxyPool: Optional[CProxyPool],
    type="offapi",
) -> bool:
    print(projectConfig.getKey("internals.enableProxy"))
    # 加载字典
    pre_dic = CNormalDic(
        initDictList(
            projectConfig.getDictCfgSection()["preDict"],
            projectConfig.getDictCfgSection()["defaultDictFolder"],
            projectConfig.getProjectDir(),
        )
    )
    post_dic = CNormalDic(
        initDictList(
            projectConfig.getDictCfgSection()["postDict"],
            projectConfig.getDictCfgSection()["defaultDictFolder"],
            projectConfig.getProjectDir(),
        )
    )
    gpt_dic = CGptDict(
        initDictList(
            projectConfig.getDictCfgSection()["gpt.dict"],
            projectConfig.getDictCfgSection()["defaultDictFolder"],
            projectConfig.getProjectDir(),
        )
    )
    # TODO: 代理池 / 令牌池

    gptapi = CGPT35Translate(
        projectConfig,
        type,
        proxyPool if projectConfig.getKey("internals.enableProxy") else None,
        tokenPool,
    )

    for dir_path in [
        projectConfig.getInputPath(),
        projectConfig.getOutputPath(),
        projectConfig.getCachePath(),
    ]:
        if not isPathExists(dir_path):
            LOGGER.info("%s 文件夹不存在，让我们创建它...", dir_path)
            mkdir(dir_path)

    semaphore = Semaphore(projectConfig.getKey("workersPerProject"))
    tasks = [
        doGPT3TranslateSingleFile(
            semaphore,
            file_name,
            projectConfig,
            type,
            pre_dic,
            post_dic,
            gpt_dic,
            gptapi,
        )
        for file_name in listdir(projectConfig.getInputPath())
    ]
    await gather(*tasks)  # run


async def doGPT4TranslateSingleFile(
    semaphore: Semaphore,
    file_name: str,
    projectConfig: CProjectConfig,
    type: str,
    pre_dic: CNormalDic,
    post_dic: CNormalDic,
    gpt_dic: CGptDict,
    gptapi: CGPT4Translate,
):
    async with semaphore:
        st = time()
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

        await gptapi.batch_translate(
            file_name,
            cache_file_path,
            trans_list,
            projectConfig.getKey("gpt.numPerRequestTranslate"),
            retry_failed=projectConfig.getKey("retranslFail"),
            chatgpt_dict=gpt_dic,
            retran_key=projectConfig.getKey("retranslKey"),
        )
        if projectConfig.getKey("gpt.enableProofRead"):
            await gptapi.batch_translate(
                file_name,
                cache_file_path,
                trans_list,
                projectConfig.getKey("gpt.numPerRequestProofRead"),
                retry_failed=projectConfig.getKey("retranslFail"),
                chatgpt_dict=gpt_dic,
                proofread=True,
                retran_key=projectConfig.getKey("retranslKey"),
            )

        # 4、翻译后处理
        for i, tran in enumerate(trans_list):
            tran.some_normal_fix()
            tran.recover_dialogue_symbol()  # 恢复对话框
            tran.post_zh = post_dic.do_replace(tran.post_zh, tran)  # 译后字典替换

    # 用于保存problems
    arinashi_dict = projectConfig.getProblemAnalyzeArinashiDict()
    find_problems(
        trans_list,
        find_type=projectConfig.getProblemAnalyzeConfig("GPT4"),
        arinashi_dict=arinashi_dict,
    )
    save_transCache_to_json(trans_list, cache_file_path, post_save=True)

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
    et = time()
    LOGGER.info(f"文件 {file_name} 翻译完成，用时 {st-st}s.")


async def doGPT4Translate(
    projectConfig: CProjectConfig,
    tokenPool: COpenAITokenPool,
    proxyPool: Optional[CProxyPool],
    type="offapi",
) -> bool:
    # 加载字典
    pre_dic = CNormalDic(
        initDictList(
            projectConfig.getDictCfgSection()["preDict"],
            projectConfig.getDictCfgSection()["defaultDictFolder"],
            projectConfig.getProjectDir(),
        )
    )
    post_dic = CNormalDic(
        initDictList(
            projectConfig.getDictCfgSection()["postDict"],
            projectConfig.getDictCfgSection()["defaultDictFolder"],
            projectConfig.getProjectDir(),
        )
    )
    gpt_dic = CGptDict(
        initDictList(
            projectConfig.getDictCfgSection()["gpt.dict"],
            projectConfig.getDictCfgSection()["defaultDictFolder"],
            projectConfig.getProjectDir(),
        )
    )

    gptapi = CGPT4Translate(
        projectConfig,
        type,
        proxyPool if projectConfig.getKey("internals.enableProxy") else None,
        tokenPool,
    )

    for dir_path in [
        projectConfig.getInputPath(),
        projectConfig.getOutputPath(),
        projectConfig.getCachePath(),
    ]:
        if not isPathExists(dir_path):
            mkdir(dir_path)

    semaphore = Semaphore(projectConfig.getKey("workersPerProject"))
    tasks = [
        doGPT4TranslateSingleFile(
            semaphore,
            file_name,
            projectConfig,
            type,
            pre_dic,
            post_dic,
            gpt_dic,
            gptapi,
        )
        for file_name in listdir(projectConfig.getInputPath())
    ]
    await gather(*tasks)  # run


async def doNewBingTranslateSingleFile(
    semaphore: Semaphore,
    file_name: str,
    projectConfig: CProjectConfig,
    pre_dic: CNormalDic,
    post_dic: CNormalDic,
    gpt_dic: CGptDict,
    gptapi: CBingGPT4Translate,
):
    async with semaphore:
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
        while True:
            success = False
            try:
                await gptapi.batch_translate(
                    file_name,
                    cache_file_path,
                    trans_list,
                    projectConfig.getKey("gpt.numPerRequestTranslate"),
                    retry_failed=projectConfig.getKey("retranslFail"),
                    chatgpt_dict=gpt_dic,
                    retran_key=projectConfig.getKey("retranslKey"),
                )
                if projectConfig.getKey("gpt.enableProofRead"):
                    await gptapi.batch_translate(
                        file_name,
                        cache_file_path,
                        trans_list,
                        projectConfig.getKey("gpt.numPerRequestProofRead"),
                        retry_failed=projectConfig.getKey("retranslFail"),
                        chatgpt_dict=gpt_dic,
                        proofread=True,
                        retran_key=projectConfig.getKey("retranslKey"),
                    )
                success = True
            except TypeError:  # https://github.com/acheong08/EdgeGPT/issues/376
                pass
            except KeyboardInterrupt:
                LOGGER.info("->KeyboardInterrupt")
                exit(0)
            except Exception as e:
                LOGGER.error("->Exception: %s", e)
                LOGGER.error("->Exception: %s", traceback.format_exc())
                LOGGER.info("->Retrying...")
            finally:
                if success:
                    break

        # 4、翻译后处理
        for i, tran in enumerate(trans_list):
            tran.some_normal_fix()
            tran.recover_dialogue_symbol()  # 恢复对话框
            tran.post_zh = post_dic.do_replace(tran.post_zh, tran)  # 译后字典替换

    # 用于保存problems
    arinashi_dict = projectConfig.getProblemAnalyzeArinashiDict()
    find_problems(
        trans_list,
        find_type=projectConfig.getProblemAnalyzeConfig("bingGPT4"),
        arinashi_dict=arinashi_dict,
    )
    save_transCache_to_json(trans_list, cache_file_path, post_save=True)

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


async def doNewBingTranslate(
    projectConfig: CProjectConfig, proxyPool: Optional[CProxyPool], multiThreading=False
) -> bool:
    # 加载字典
    pre_dic = CNormalDic(
        initDictList(
            projectConfig.getDictCfgSection()["preDict"],
            projectConfig.getDictCfgSection()["defaultDictFolder"],
            projectConfig.getProjectDir(),
        )
    )
    post_dic = CNormalDic(
        initDictList(
            projectConfig.getDictCfgSection()["postDict"],
            projectConfig.getDictCfgSection()["defaultDictFolder"],
            projectConfig.getProjectDir(),
        )
    )
    gpt_dic = CGptDict(
        initDictList(
            projectConfig.getDictCfgSection()["gpt.dict"],
            projectConfig.getDictCfgSection()["defaultDictFolder"],
            projectConfig.getProjectDir(),
        )
    )

    cookiePool: list[str] = []
    for i in projectConfig.getBackendConfigSection("bingGPT4")["cookiePath"]:
        cookiePool.append(joinpath(projectConfig.getProjectDir(), i))

    gptapi = CBingGPT4Translate(projectConfig, cookiePool, proxyPool)

    for dir_path in [
        projectConfig.getInputPath(),
        projectConfig.getOutputPath(),
        projectConfig.getCachePath(),
    ]:
        if not isPathExists(dir_path):
            mkdir(dir_path)

    semaphore = Semaphore(projectConfig.getKey("workersPerProject"))
    tasks = [
        doNewBingTranslateSingleFile(
            semaphore,
            file_name,
            projectConfig,
            pre_dic,
            post_dic,
            gpt_dic,
            gptapi,
        )
        for file_name in listdir(projectConfig.getInputPath())
    ]
    await gather(*tasks)  # run

    pass
