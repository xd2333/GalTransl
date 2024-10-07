from typing import List, Dict, Any, Optional, Union, Tuple
from os import makedirs, sep as os_sep
from os.path import (
    join as joinpath,
    exists as isPathExists,
    dirname
)
from tqdm.asyncio import tqdm as atqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from time import time
import asyncio
from dataclasses import dataclass
from GalTransl import LOGGER
from GalTransl.Backend.GPT3Translate import CGPT35Translate
from GalTransl.Backend.GPT4Translate import CGPT4Translate
from GalTransl.Backend.BingGPT4Translate import CBingGPT4Translate
from GalTransl.Backend.SakuraTranslate import CSakuraTranslate
from GalTransl.Backend.RebuildTranslate import CRebuildTranslate
from GalTransl.ConfigHelper import initDictList, CProjectConfig
from GalTransl.Dictionary import CGptDict, CNormalDic
from GalTransl.Problem import find_problems
from GalTransl.Cache import save_transCache_to_json
from GalTransl.Name import load_name_table, dump_name_table_from_chunks
from GalTransl.CSerialize import update_json_with_transList, save_json
from GalTransl.Dictionary import CNormalDic, CGptDict
from GalTransl.ConfigHelper import CProjectConfig, initDictList
from GalTransl.Utils import get_file_list
from GalTransl.CSplitter import SplitChunkMetadata, DictionaryCombiner


async def doLLMTranslate(
    projectConfig: CProjectConfig,
) -> bool:

    project_dir = projectConfig.getProjectDir()
    input_dir = projectConfig.getInputPath()
    output_dir = projectConfig.getOutputPath()
    cache_dir = projectConfig.getCachePath()
    pre_dic_list = projectConfig.getDictCfgSection()["preDict"]
    post_dic_list = projectConfig.getDictCfgSection()["postDict"]
    gpt_dic_list = projectConfig.getDictCfgSection()["gpt.dict"]
    default_dic_dir = projectConfig.getDictCfgSection()["defaultDictFolder"]
    workersPerProject = projectConfig.getKey("workersPerProject") or 1
    semaphore = asyncio.Semaphore(workersPerProject)
    fPlugins = projectConfig.fPlugins
    tPlugins = projectConfig.tPlugins
    eng_type = projectConfig.select_translator
    input_splitter = projectConfig.input_splitter
    SplitChunkMetadata.clear_file_finished_chunk()
    total_chunks = []

    makedirs(output_dir, exist_ok=True)
    makedirs(cache_dir, exist_ok=True)

    # 初始化人名替换表
    name_replaceDict_path = joinpath(projectConfig.getProjectDir(), "人名替换表.csv")
    if isPathExists(name_replaceDict_path):
        projectConfig.name_replaceDict = load_name_table(name_replaceDict_path)

    # 初始化字典
    projectConfig.pre_dic = CNormalDic(
        initDictList(pre_dic_list, default_dic_dir, project_dir)
    )
    projectConfig.post_dic = CNormalDic(
        initDictList(post_dic_list, default_dic_dir, project_dir)
    )
    projectConfig.gpt_dic = CGptDict(
        initDictList(gpt_dic_list, default_dic_dir, project_dir)
    )
    if projectConfig.getDictCfgSection().get("sortPrePostDict", False):
        projectConfig.pre_dic.sort_dic()
        projectConfig.post_dic.sort_dic()

    # 获取待翻译文件列表
    file_list = get_file_list(projectConfig.getInputPath())
    if not file_list:
        raise RuntimeError(f"{projectConfig.getInputPath()}中没有待翻译的文件")

    # 读取所有文件获得total_chunks列表
    with ThreadPoolExecutor(max_workers=workersPerProject) as executor:
        future_to_file = {
            executor.submit(fplugins_load_file, file_path, fPlugins): file_path
            for file_path in file_list
        }

        with tqdm(total=len(file_list), desc="读入文件", dynamic_ncols=True) as pbar:
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    json_list, save_func = future.result()
                    projectConfig.file_save_funcs[file_path] = save_func
                    total_chunks.extend(input_splitter.split(json_list, file_path))
                except Exception as exc:
                    LOGGER.error(f"处理文件 {file_path} 时发生错误: {exc}")
                finally:
                    pbar.update(1)

    if "dump-name" in eng_type:
        dump_name_table_from_chunks(total_chunks, projectConfig)
        return True

    progress_bar = atqdm(
        total=len(total_chunks),
        desc="Processing chunks/files",
        dynamic_ncols=True,
        leave=False,
    )

    async def run_task(task):
        result = await task
        progress_bar.update(1)
        # progress_bar.set_postfix(
        #     file=result[3].split(os_sep)[-1],
        #     chunk=f"{result[4].start_index}-{result[4].end_index}",
        # )
        return result

    all_tasks = []
    for i, chunk in enumerate(total_chunks):
        task = run_task(
            doLLMTranslSingleChunk(
                semaphore,
                split_chunk=chunk,
                projectConfig=projectConfig,
            )
        )
        all_tasks.append(task)

    results = await asyncio.gather(*all_tasks)
    progress_bar.close()


async def doLLMTranslSingleChunk(
    semaphore: asyncio.Semaphore,
    split_chunk: SplitChunkMetadata,
    projectConfig: CProjectConfig,
) -> Tuple[bool, List, List, str, SplitChunkMetadata]:

    async with semaphore:
        st = time()
        proj_dir = projectConfig.getProjectDir()
        input_dir = projectConfig.getInputPath()
        output_dir = projectConfig.getOutputPath()
        cache_dir = projectConfig.getCachePath()
        pre_dic = projectConfig.pre_dic
        post_dic = projectConfig.post_dic
        gpt_dic = projectConfig.gpt_dic
        file_path = split_chunk.file_path
        file_name = (
            file_path.replace(input_dir, "").lstrip(os_sep).replace(os_sep, "-}")
        )  # 多级文件夹
        tPlugins = projectConfig.tPlugins
        eng_type = projectConfig.select_translator

        total_splits = split_chunk.total_chunks
        file_index = split_chunk.chunk_index
        input_file_path = file_path
        output_file_path = input_file_path.replace(input_dir, output_dir)

        cache_file_path = joinpath(
            cache_dir,
            file_name + (f"_{file_index}" if total_splits > 1 else ""),
        )
        print("\n", flush=True)
        part_info = f" (part {file_index+1}/{total_splits})" if total_splits > 1 else ""
        LOGGER.info(f"开始翻译 {file_name}{part_info}, 引擎类型: {eng_type}")

        gptapi = await init_gptapi(projectConfig)

        LOGGER.debug(f"文件 {file_name} 分块 {file_index+1}/{total_splits}:")
        LOGGER.debug(f"  开始索引: {split_chunk.start_index}")
        LOGGER.debug(f"  结束索引: {split_chunk.end_index}")
        LOGGER.debug(f"  非交叉大小: {split_chunk.chunk_non_cross_size}")
        LOGGER.debug(f"  实际大小: {split_chunk.chunk_size}")
        LOGGER.debug(f"  交叉数量: {split_chunk.cross_num}")

        # 翻译前处理
        for tran in split_chunk.trans_list:
            for plugin in tPlugins:
                try:
                    tran = plugin.plugin_object.before_src_processed(tran)
                except Exception as e:
                    LOGGER.error(f"插件 {plugin.name} 执行失败: {e}")

            if projectConfig.getFilePlugin() == "file_galtransl_json":
                tran.analyse_dialogue()
            tran.post_jp = pre_dic.do_replace(tran.post_jp, tran)
            if projectConfig.getDictCfgSection("usePreDictInName"):
                if isinstance(tran.speaker, str) and isinstance(tran._speaker, str):
                    tran.speaker = pre_dic.do_replace(tran.speaker, tran)
            for plugin in tPlugins:
                try:
                    tran = plugin.plugin_object.after_src_processed(tran)
                except Exception as e:
                    LOGGER.error(f"插件 {plugin.name} 执行失败: {e}")

        # 执行翻译
        await gptapi.batch_translate(
            file_name,
            cache_file_path,
            split_chunk.trans_list,
            projectConfig.getKey("gpt.numPerRequestTranslate"),
            retry_failed=projectConfig.getKey("retranslFail"),
            gpt_dic=gpt_dic,
            retran_key=projectConfig.getKey("retranslKey"),
        )

        # 执行校对（如果启用）
        if projectConfig.getKey("gpt.enableProofRead"):
            if (
                "newbing" in gptapi.__class__.__name__.lower()
                or "gpt4" in gptapi.__class__.__name__.lower()
            ):
                await gptapi.batch_translate(
                    file_name,
                    cache_file_path,
                    split_chunk.trans_list,
                    projectConfig.getKey("gpt.numPerRequestProofRead"),
                    retry_failed=projectConfig.getKey("retranslFail"),
                    gpt_dic=gpt_dic,
                    proofread=True,
                    retran_key=projectConfig.getKey("retranslKey"),
                )
            else:
                LOGGER.warning("当前引擎不支持校对，跳过校对步骤")

        # 翻译后处理
        for tran in split_chunk.trans_list:
            for plugin in tPlugins:
                try:
                    tran = plugin.plugin_object.before_dst_processed(tran)
                except Exception as e:
                    LOGGER.error(f" 插件 {plugin.name} 执行失败: {e}")
            tran.recover_dialogue_symbol()
            tran.post_zh = post_dic.do_replace(tran.post_zh, tran)
            if projectConfig.getDictCfgSection("usePostDictInName"):
                if tran._speaker:
                    if isinstance(tran.speaker, list) and isinstance(
                        tran._speaker, list
                    ):
                        tran._speaker = [
                            post_dic.do_replace(s, tran, True) for s in tran.speaker
                        ]
                    elif isinstance(tran.speaker, str) and isinstance(
                        tran._speaker, str
                    ):
                        tran._speaker = post_dic.do_replace(tran.speaker, tran, True)
            for plugin in tPlugins:
                try:
                    tran = plugin.plugin_object.after_dst_processed(tran)
                except Exception as e:
                    LOGGER.error(f"插件 {plugin.name} 执行失败: {e}")

        et = time()
        LOGGER.info(f"文件 {file_name}{part_info} 翻译完成，用时 {et-st:.3f}s.")
        gptapi.clean_up()

        split_chunk.update_file_finished_chunk()
        # 检查是否该文件的所有chunk都翻译完成
        if split_chunk.is_file_finished():
            LOGGER.debug(f"文件 {file_name} 的所有chunk都翻译完成")
            await postprocess_results(
                split_chunk.get_file_finished_chunks(), projectConfig
            )


async def postprocess_results(
    resultChunks: List[SplitChunkMetadata],
    projectConfig: CProjectConfig,
):

    proj_dir = projectConfig.getProjectDir()
    input_dir = projectConfig.getInputPath()
    output_dir = projectConfig.getOutputPath()
    cache_dir = projectConfig.getCachePath()
    eng_type = projectConfig.select_translator
    gpt_dic = projectConfig.gpt_dic
    name_replaceDict = projectConfig.name_replaceDict

    # 对每个分块执行错误检查和缓存保存
    for i, chunk in enumerate(resultChunks):
        trans_list = chunk.trans_list
        file_path = chunk.file_path
        cache_file_path = joinpath(
            cache_dir,
            file_path.replace(input_dir, "").lstrip(os_sep).replace(os_sep, "-}")
            + (f"_{chunk.chunk_index}" if chunk.total_chunks > 1 else ""),
        )

        if eng_type != "rebuildr":
            find_problems(trans_list, projectConfig, gpt_dic)
            save_transCache_to_json(trans_list, cache_file_path, post_save=True)

    # 使用output_combiner合并结果，即使只有一个结果
    all_trans_list, all_json_list = DictionaryCombiner.combine(resultChunks)
    LOGGER.debug(f"合并后总行数: {len(all_trans_list)}")
    file_path = resultChunks[0].file_path
    output_file_path = file_path.replace(input_dir, output_dir)
    save_func = projectConfig.file_save_funcs.get(file_path, save_json)

    if all_trans_list and all_json_list:
        final_result = update_json_with_transList(
            all_trans_list, all_json_list, name_replaceDict
        )
        makedirs(dirname(output_file_path), exist_ok=True)
        save_func(output_file_path, final_result)
        LOGGER.info(f"已保存文件: {output_file_path}")  # 添加保存确认日志


async def init_gptapi(
    projectConfig: CProjectConfig,
):
    """
    根据引擎类型获取相应的API实例。

    参数:
    projectConfig: 项目配置对象
    eng_type: 引擎类型
    endpoint: API端点（如果适用）
    proxyPool: 代理池（如果适用）
    tokenPool: Token池

    返回:
    相应的API实例
    """
    proxyPool = projectConfig.proxyPool
    tokenPool = projectConfig.tokenPool
    sakuraEndpointQueue = projectConfig.endpointQueue
    eng_type = projectConfig.select_translator

    match eng_type:
        case "gpt35-0613" | "gpt35-1106" | "gpt35-0125":
            return CGPT35Translate(projectConfig, eng_type, proxyPool, tokenPool)
        case "gpt4" | "gpt4-turbo":
            return CGPT4Translate(projectConfig, eng_type, proxyPool, tokenPool)
        case "newbing":
            cookiePool: list[str] = []
            for i in projectConfig.getBackendConfigSection("bingGPT4")["cookiePath"]:
                cookiePool.append(joinpath(projectConfig.getProjectDir(), i))
            return CBingGPT4Translate(projectConfig, cookiePool, proxyPool)
        case "sakura-009" | "sakura-v1.0" | "galtransl-v2.5":
            sakura_endpoint = await sakuraEndpointQueue.get()
            if sakuraEndpointQueue is None:
                raise ValueError(f"Endpoint is required for engine type {eng_type}")
            return CSakuraTranslate(projectConfig, eng_type, sakura_endpoint, proxyPool)
        case "rebuildr" | "rebuilda" | "dump-name":
            return CRebuildTranslate(projectConfig, eng_type)
        case _:
            raise ValueError(f"不支持的翻译引擎类型 {eng_type}")


def fplugins_load_file(file_path: str, fPlugins: list) -> Tuple[List[Dict], Any]:
    result = None
    save_func = None
    for plugin in fPlugins:

        if isinstance(plugin, str):
            LOGGER.warning(f"跳过无效的插件项: {plugin}")
            continue
        try:
            result = plugin.plugin_object.load_file(file_path)
            save_func = plugin.plugin_object.save_file
            break
        except TypeError as e:
            LOGGER.error(
                f"{file_path} 不是文件插件'{getattr(plugin, 'name', 'Unknown')}'支持的格式：{e}"
            )
        except Exception as e:
            LOGGER.error(
                f"插件 {getattr(plugin, 'name', 'Unknown')} 读取文件 {file_path} 出错: {e}"
            )

    assert result is not None, f"文件 {file_path} 无法加载"

    assert isinstance(result, list), f"文件 {file_path} 不是列表"

    return result, save_func
