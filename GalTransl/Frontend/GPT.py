from typing import List, Dict, Any, Optional, Union, Tuple
from os import makedirs, sep as os_sep
from os.path import join as joinpath, exists as isPathExists, getsize as getFileSize, basename, dirname
from tqdm.asyncio import tqdm as atqdm
from asyncio import Semaphore, gather, Queue
from time import time
import asyncio
import json
from dataclasses import dataclass

from GalTransl import LOGGER
from GalTransl.Backend.GPT3Translate import CGPT35Translate
from GalTransl.Backend.GPT4Translate import CGPT4Translate
from GalTransl.Backend.BingGPT4Translate import CBingGPT4Translate
from GalTransl.Backend.SakuraTranslate import CSakuraTranslate
from GalTransl.Backend.RebuildTranslate import CRebuildTranslate
from GalTransl.ConfigHelper import initDictList, CProjectConfig, CProxyPool
from GalTransl.Loader import load_transList
from GalTransl.Dictionary import CGptDict, CNormalDic
from GalTransl.Problem import find_problems
from GalTransl.Cache import save_transCache_to_json
from GalTransl.Name import load_name_table
from GalTransl.CSerialize import update_json_with_transList, save_json
from GalTransl.Dictionary import CNormalDic, CGptDict
from GalTransl.ConfigHelper import CProjectConfig, initDictList, CProxyPool
from GalTransl.COpenAI import COpenAITokenPool
from GalTransl.Utils import get_file_list

name_dict = {}


@dataclass
class SplitChunkMetadata:
    """
    用于存储分割后的文本块元数据的数据类。

    属性:
    start_index: 块在原始文本中的起始索引
    end_index: 块在原始文本中的结束索引
    chunk_non_cross_size: 不包括交叉部分的块大小
    chunk_real_size: 包括交叉部分的实际块大小
    cross_num: 交叉句子数量
    content: 块的实际内容
    """
    start_index: int
    end_index: int
    chunk_non_cross_size: int
    chunk_real_size: int
    cross_num: int
    content: Any


class InputSplitter:
    """
    输入分割器的基类，定义了分割方法的接口。
    """
    @staticmethod
    def split(content: Union[str, List], cross_num: int) -> List[SplitChunkMetadata]:
        """
        分割输入内容的方法，由子类实现。

        参数:
        content: 要分割的内容，可以是字符串或列表
        cross_num: 交叉句子的数量

        返回:
        分割后的SplitChunkMetadata列表
        """
        pass


class DictionaryCountSplitter(InputSplitter):
    """
    基于字典计数的分割器，将输入内容按指定的字典数量进行分割。
    """

    def __init__(self, dict_count: int):
        """
        初始化分割器。

        参数:
        dict_count: 每个分割块中包含的字典数量
        """
        self.dict_count = dict_count

    def split(self, content: Union[str, List], cross_num: int) -> List[SplitChunkMetadata]:
        """
        实现分割方法，将输入内容按字典数量分割。

        参数:
        content: 要分割的内容
        cross_num: 交叉句子的数量

        返回:
        分割后的SplitChunkMetadata列表
        """
        if isinstance(content, str):
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                LOGGER.warning(f"无法解析JSON：{content[:100]}...")
                return [SplitChunkMetadata(0, 1, 1, 1, 0, content)]
        else:
            data = content

        if not isinstance(data, list):
            return [SplitChunkMetadata(0, 1, 1, 1, 0, json.dumps(data, ensure_ascii=False, indent=2))]

        result = []
        for i in range(0, len(data), self.dict_count):
            start = max(0, i - cross_num)
            end = min(len(data), i + self.dict_count + cross_num)
            chunk = data[start:end]
            result.append(SplitChunkMetadata(
                start_index=i,
                end_index=min(i + self.dict_count, len(data)),
                chunk_non_cross_size=min(self.dict_count, len(data) - i),
                chunk_real_size=len(chunk),
                cross_num=cross_num,
                content=json.dumps(chunk, ensure_ascii=False, indent=2)
            ))

        return result


class EqualPartsSplitter(InputSplitter):
    """
    将输入内容平均分割成指定数量的部分。
    """

    def __init__(self, parts: int):
        """
        初始化分割器。

        参数:
        parts: 要分割成的部分数量
        """
        self.parts = parts

    def split(self, content: Union[str, List], cross_num: int) -> List[SplitChunkMetadata]:
        """
        实现分割方法，将输入内容平均分割。

        参数:
        content: 要分割的内容
        cross_num: 交叉句子的数量

        返回:
        分割后的SplitChunkMetadata列表
        """
        if isinstance(content, str):
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                return [SplitChunkMetadata(0, 1, 1, 1, 0, content)]
        else:
            data = content

        if not isinstance(data, list):
            return [SplitChunkMetadata(0, 1, 1, 1, 0, json.dumps(data, ensure_ascii=False, indent=2))]

        total_items = len(data)
        items_per_part = total_items // self.parts
        remainder = total_items % self.parts

        result = []
        start = 0
        for i in range(self.parts):
            end = start + items_per_part + (1 if i < remainder else 0)
            chunk_start = max(0, start - cross_num)
            chunk_end = min(total_items, end + cross_num)
            chunk = data[chunk_start:chunk_end]
            result.append(SplitChunkMetadata(
                start_index=start,
                end_index=end,
                chunk_non_cross_size=end - start,
                chunk_real_size=len(chunk),
                cross_num=cross_num,
                content=json.dumps(chunk, ensure_ascii=False, indent=2)
            ))
            start = end

        return result


class OutputCombiner:
    """
    输出合并器的基类，定义了合并方法的接口。
    """
    @staticmethod
    def combine(results: List[Tuple[List, List, SplitChunkMetadata]]) -> Tuple[List, List]:
        """
        合并输出结果的方法，由子类实现。

        参数:
        results: 包含翻译结果、JSON列表和元数据的元组列表

        返回:
        合并后的翻译列表和JSON列表的元组
        """
        pass


class DictionaryCombiner(OutputCombiner):
    """
    基于字典的输出合并器，用于合并分割后的翻译结果。
    """
    @staticmethod
    def combine(results: List[Tuple[List, List, SplitChunkMetadata]]) -> Tuple[List, List]:
        """
        实现合并方法，合并分割后的翻译结果。

        参数:
        results: 包含翻译结果、JSON列表和元数据的元组列表

        返回:
        合并后的翻译列表和JSON列表的元组
        """
        all_trans_list = []
        all_json_list = []
        sorted_results = sorted(results, key=lambda x: x[2].start_index)

        for i, (trans_list, json_list, metadata) in enumerate(sorted_results):
            start = metadata.cross_num if i > 0 else 0
            end = len(
                trans_list) - metadata.cross_num if i < len(sorted_results) - 1 else len(trans_list)

            all_trans_list.extend(trans_list[start:end])
            all_json_list.extend(json_list[start:end])

        return all_trans_list, all_json_list


async def init_endpoint_queue(projectConfig: CProjectConfig, workersPerProject: int, eng_type: str) -> Optional[Queue]:
    """
    初始化端点队列，用于Sakura或GalTransl引擎。

    参数:
    projectConfig: 项目配置对象
    workersPerProject: 每个项目的工作线程数
    eng_type: 引擎类型

    返回:
    初始化的端点队列，如果不需要则返回None
    """
    if "sakura" in eng_type or "galtransl" in eng_type:
        endpoint_queue = asyncio.Queue()
        backendSpecific = projectConfig.projectConfig["backendSpecific"]
        section_name = "SakuraLLM" if "SakuraLLM" in backendSpecific else "Sakura"
        if "endpoints" in projectConfig.getBackendConfigSection(section_name):
            endpoints = projectConfig.getBackendConfigSection(section_name)[
                "endpoints"]
        else:
            endpoints = [projectConfig.getBackendConfigSection(section_name)[
                "endpoint"]]
        repeated = (workersPerProject + len(endpoints) - 1) // len(endpoints)
        for _ in range(repeated):
            for endpoint in endpoints:
                await endpoint_queue.put(endpoint)
        LOGGER.info(f"当前使用 {workersPerProject} 个Sakura worker引擎")
        return endpoint_queue
    else:
        return None


def init_dictionaries(projectConfig: CProjectConfig) -> Tuple[CNormalDic, CNormalDic, CGptDict]:
    """
    初始化翻译使用的字典。

    参数:
    projectConfig: 项目配置对象

    返回:
    预处理字典、后处理字典和GPT字典的元组
    """
    pre_dic_dir = projectConfig.getDictCfgSection()["preDict"]
    post_dic_dir = projectConfig.getDictCfgSection()["postDict"]
    gpt_dic_dir = projectConfig.getDictCfgSection()["gpt.dict"]
    default_dic_dir = projectConfig.getDictCfgSection()["defaultDictFolder"]
    project_dir = projectConfig.getProjectDir()

    pre_dic = CNormalDic(initDictList(
        pre_dic_dir, default_dic_dir, project_dir))
    post_dic = CNormalDic(initDictList(
        post_dic_dir, default_dic_dir, project_dir))
    gpt_dic = CGptDict(initDictList(gpt_dic_dir, default_dic_dir, project_dir))

    if projectConfig.getDictCfgSection().get("sortPrePostDict", False):
        pre_dic.sort_dic()
        post_dic.sort_dic()

    return pre_dic, post_dic, gpt_dic


async def get_gptapi(projectConfig: CProjectConfig, eng_type: str, endpoint: Optional[str], proxyPool: Optional[CProxyPool], tokenPool: COpenAITokenPool):
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
        case "sakura-009" | "sakura-010" | "galtransl-v1.5":
            if endpoint is None:
                raise ValueError(
                    f"Endpoint is required for engine type {eng_type}")
            return CSakuraTranslate(projectConfig, eng_type, endpoint, proxyPool)
        case "rebuildr" | "rebuilda" | "dump-name":
            return CRebuildTranslate(projectConfig, eng_type)
        case _:
            raise ValueError(f"不支持的翻译引擎类型 {eng_type}")


def load_input(file_path: str, fPlugins: list) -> Tuple[str, Any]:
    """
    加载输入文件内容。

    参数:
    file_path: 文件路径
    fPlugins: 文件插件列表

    返回:
    文件内容和保存函数的元组
    """
    origin_input = ""
    save_func = None
    for plugin in fPlugins:
        if isinstance(plugin, str):
            LOGGER.warning(f"跳过无效的插件项: {plugin}")
            continue
        try:
            origin_input = plugin.plugin_object.load_file(file_path)
            save_func = plugin.plugin_object.save_file
            break
        except AttributeError as e:
            LOGGER.error(
                f"插件 {getattr(plugin, 'name', 'Unknown')} 缺少必要的属性或方法: {e}")
        except TypeError as e:
            LOGGER.error(
                f"{file_path} 不是文件插件'{getattr(plugin, 'name', 'Unknown')}'支持的格式：{e}")
        except Exception as e:
            LOGGER.error(
                f"插件 {getattr(plugin, 'name', 'Unknown')} 读取文件 {file_path} 出错: {e}")

    if not origin_input and file_path.endswith(".json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                origin_input = f.read()
            save_func = save_json
        except Exception as e:
            LOGGER.error(f"读取JSON文件 {file_path} 失败: {e}")

    return origin_input, save_func


async def process_input(
    trans_list: List,
    json_list: List,
    file_name: str,
    pre_dic: CNormalDic,
    tPlugins: list,
    gptapi: Any,
    projectConfig: CProjectConfig,
    gpt_dic: CGptDict,
    cache_file_path: str,
    post_dic: CNormalDic
) -> Tuple[List, List]:
    """
    处理输入内容，包括翻译前处理、翻译和翻译后处理。

    参数:
    trans_list: 翻译列表
    json_list: JSON列表
    file_name: 文件名
    pre_dic: 预处理字典
    tPlugins: 翻译插件列表
    gptapi: GPT API实例
    projectConfig: 项目配置对象
    gpt_dic: GPT字典
    cache_file_path: 缓存文件路径
    post_dic: 后处理字典

    返回:
    处理后的翻译列表和JSON列表的元组
    """
    try:
        # 翻译前处理
        for tran in trans_list:
            for plugin in tPlugins:
                try:
                    tran = plugin.plugin_object.before_src_processed(tran)
                except Exception as e:
                    LOGGER.error(f"插件 {plugin.name} 执行失败: {e}")
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
            trans_list,
            projectConfig.getKey("gpt.numPerRequestTranslate"),
            retry_failed=projectConfig.getKey("retranslFail"),
            gpt_dic=gpt_dic,
            retran_key=projectConfig.getKey("retranslKey"),
        )

        # 执行校对（如果启用）
        if projectConfig.getKey("gpt.enableProofRead"):
            if "newbing" in gptapi.__class__.__name__.lower() or "gpt4" in gptapi.__class__.__name__.lower():
                await gptapi.batch_translate(
                    file_name,
                    cache_file_path,
                    trans_list,
                    projectConfig.getKey("gpt.numPerRequestProofRead"),
                    retry_failed=projectConfig.getKey("retranslFail"),
                    gpt_dic=gpt_dic,
                    proofread=True,
                    retran_key=projectConfig.getKey("retranslKey"),
                )
            else:
                LOGGER.warning("当前引擎不支持校对，跳过校对步骤")

        # 翻译后处理
        for tran in trans_list:
            for plugin in tPlugins:
                try:
                    tran = plugin.plugin_object.before_dst_processed(tran)
                except Exception as e:
                    LOGGER.error(f" 插件 {plugin.name} 执行失败: {e}")
            tran.recover_dialogue_symbol()
            tran.post_zh = post_dic.do_replace(tran.post_zh, tran)
            if projectConfig.getDictCfgSection("usePostDictInName"):
                if tran._speaker:
                    if isinstance(tran.speaker, list) and isinstance(tran._speaker, list):
                        tran._speaker = [post_dic.do_replace(
                            s, tran) for s in tran.speaker]
                    elif isinstance(tran.speaker, str) and isinstance(tran._speaker, str):
                        tran._speaker = post_dic.do_replace(tran.speaker, tran)
            for plugin in tPlugins:
                try:
                    tran = plugin.plugin_object.after_dst_processed(tran)
                except Exception as e:
                    LOGGER.error(f"插件 {plugin.name} 执行失败: {e}")

    except Exception as e:
        LOGGER.error(f"处理内容时出错: {e}")
        return [], []

    return trans_list, json_list


async def doLLMTranslateSingleFile(
    semaphore: asyncio.Semaphore,
    endpoint_queue: asyncio.Queue,
    file_path: str,
    projectConfig: CProjectConfig,
    eng_type: str,
    pre_dic: CNormalDic,
    post_dic: CNormalDic,
    gpt_dic: CGptDict,
    tPlugins: list,
    fPlugins: list,
    proxyPool: CProxyPool,
    tokenPool: COpenAITokenPool,
    split_chunk: SplitChunkMetadata,
    file_index: int = 0,
    total_splits: int = 1
) -> Tuple[bool, List, List, str, SplitChunkMetadata]:
    """
    处理单个文件的翻译任务。

    参数:
    semaphore: 用于控制并发的信号量
    endpoint_queue: API端点队列
    file_path: 文件路径
    projectConfig: 项目配置对象
    eng_type: 引擎类型
    pre_dic: 预处理字典
    post_dic: 后处理字典
    gpt_dic: GPT字典
    tPlugins: 翻译插件列表
    fPlugins: 文件插件列表
    proxyPool: 代理池
    tokenPool: Token池
    split_chunk: 分割的文件块元数据
    file_index: 文件块索引
    total_splits: 总分割数

    返回:
    包含处理结果的元组
    """
    async with semaphore:
        endpoint = None
        try:
            if endpoint_queue is not None:
                endpoint = await endpoint_queue.get()

            st = time()
            proj_dir = projectConfig.getProjectDir()
            input_dir = projectConfig.getInputPath()
            output_dir = projectConfig.getOutputPath()
            cache_dir = projectConfig.getCachePath()
            file_name = file_path.replace(input_dir, "").lstrip(os_sep)
            file_name = file_name.replace(os_sep, "-}")
            input_file_path = file_path
            output_file_path = input_file_path.replace(input_dir, output_dir)
            output_file_dir = dirname(output_file_path)
            makedirs(output_file_dir, exist_ok=True)
            cache_file_path = joinpath(cache_dir, f"{file_name}_{file_index}")
            print("\n", flush=True)
            LOGGER.info(
                f"开始翻译文件: {file_name} (part {file_index+1}/{total_splits}), 引擎类型: {eng_type}")

            gptapi = await get_gptapi(projectConfig, eng_type, endpoint, proxyPool, tokenPool)

            origin_input = split_chunk.content
            LOGGER.debug(f"原始输入: {str(origin_input)[:500]}...")

            try:
                trans_list, json_list = load_transList(origin_input)
            except Exception as e:
                LOGGER.error(f"文件 {file_name} 加载翻译列表失败: {e}")
                return False, [], [], file_path, split_chunk

            # 导出人名表功能
            if "dump-name" in eng_type:
                for tran in trans_list:
                    if tran.speaker and isinstance(tran.speaker, str):
                        if tran.speaker not in name_dict:
                            name_dict[tran.speaker] = 0
                        name_dict[tran.speaker] += 1
                        LOGGER.debug(f"发现人名: {tran.speaker}")
                LOGGER.debug(f"人名表: {name_dict}")
                return True, trans_list, json_list, file_path, split_chunk

            trans_list, json_list = await process_input(
                trans_list,
                json_list,
                file_name,
                pre_dic,
                tPlugins,
                gptapi,
                projectConfig,
                gpt_dic,
                cache_file_path,
                post_dic
            )

            LOGGER.debug(
                f"翻译后长度: trans_list={len(trans_list)}, json_list={len(json_list)}")

            et = time()
            LOGGER.info(
                f"文件 {file_name} (part {file_index+1}/{total_splits}) 翻译完成，用时 {et-st:.3f}s.")
            return True, trans_list, json_list, file_path, split_chunk
        finally:
            if endpoint_queue is not None and endpoint is not None:
                endpoint_queue.put_nowait(endpoint)


async def doLLMTranslate(
    projectConfig: CProjectConfig,
    tokenPool: COpenAITokenPool,
    proxyPool: Optional[CProxyPool],
    tPlugins: list,
    fPlugins: list,
    eng_type: str = "offapi",
    input_splitter: InputSplitter = InputSplitter(),
    output_combiner: OutputCombiner = OutputCombiner()
) -> bool:
    """
    执行LLM翻译的主函数。

    参数:
    projectConfig: 项目配置对象
    tokenPool: Token池
    proxyPool: 代理池
    tPlugins: 翻译插件列表
    fPlugins: 文件插件列表
    eng_type: 引擎类型
    input_splitter: 输入分割器
    output_combiner: 输出合并器

    返回:
    翻译是否成功完成
    """
    pre_dic, post_dic, gpt_dic = init_dictionaries(projectConfig)
    workersPerProject = projectConfig.getKey("workersPerProject")
    endpoint_queue = await init_endpoint_queue(projectConfig, workersPerProject, eng_type)
    all_tasks = []
    file_save_funcs = {}
    cross_num = projectConfig.getKey("splitFileCrossNum")
    split_file = projectConfig.getKey("splitFile")

    file_list = get_file_list(projectConfig.getInputPath())
    if not file_list:
        raise RuntimeError(f"{projectConfig.getInputPath()}中没有待翻译的文件")
    semaphore = asyncio.Semaphore(workersPerProject)
    total_chunks = sum(len(input_splitter.split(load_input(file_name, fPlugins)[0], cross_num)) for file_name in file_list)
    progress_bar = atqdm(total=total_chunks, desc="Processing chunks/files", dynamic_ncols=True, leave=False)

    async def run_task(task):
        result = await task
        progress_bar.update(1)
        progress_bar.set_postfix(file=result[3], chunk=f"{result[4].start_index}-{result[4].end_index}")
        return result

    for file_name in file_list:
        origin_input, save_func = load_input(file_name, fPlugins)
        file_save_funcs[file_name] = save_func

        split_chunks = input_splitter.split(origin_input, cross_num) if split_file else [
            SplitChunkMetadata(0, len(origin_input), len(origin_input), len(origin_input), 0, origin_input)]

        for i, split_chunk in enumerate(split_chunks):
            task = run_task(
                doLLMTranslateSingleFile(
                    semaphore,
                    endpoint_queue,
                    file_name,
                    projectConfig,
                    eng_type,
                    pre_dic,
                    post_dic,
                    gpt_dic,
                    tPlugins,
                    fPlugins,
                    proxyPool,
                    tokenPool,
                    split_chunk,
                    i,
                    len(split_chunks)
                )
            )
            all_tasks.append(task)

    results = await asyncio.gather(*all_tasks)
    progress_bar.close()

    await postprocess_results(
        file_list,
        results,
        eng_type,
        projectConfig,
        file_save_funcs,
        fPlugins,
        gpt_dic,
        output_combiner
    )

    return True


async def postprocess_results(
    file_list: List[str],
    results: List[Tuple[bool, List, List, str, SplitChunkMetadata]],
    eng_type: str,
    projectConfig: CProjectConfig,
    file_save_funcs: Dict[str, Any],
    fPlugins: list,
    gpt_dic: CGptDict,
    output_combiner: OutputCombiner
):
    """
    处理翻译结果，包括保存结果、生成人名表等。

    参数:
    file_list: 文件列表
    results: 翻译结果列表
    eng_type: 引擎类型
    projectConfig: 项目配置对象
    file_save_funcs: 文件保存函数字典
    fPlugins: 文件插件列表
    gpt_dic: GPT字典
    output_combiner: 输出合并器
    """
    if "dump-name" in eng_type:
        import csv
        global name_dict
        proj_dir = projectConfig.getProjectDir()
        LOGGER.info(f"开始保存人名表...{name_dict}")
        name_dict = dict(
            sorted(name_dict.items(), key=lambda item: item[1], reverse=True))
        LOGGER.info(f"共发现 {len(name_dict)} 个人名，按出现次数排序如下：")
        for name, count in name_dict.items():
            LOGGER.info(f"{name}: {count}")
        with open(joinpath(proj_dir, "人名替换表.csv"), "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["JP_Name", "CN_Name", "Count"])  # 写入表头
            for name, count in name_dict.items():
                writer.writerow([name, "", count])
        LOGGER.info(
            f"name已保存到'人名替换表.csv'（UTF-8编码，用Emeditor编辑），填入CN_Name后可用于后续翻译name字段。")

    for file_name in file_list:
        file_results = [result for result in results if result[0]
                        and result[1] and result[2] and result[3] == file_name]
        if file_results:
            LOGGER.debug(f"处理文件 {file_name}")
            LOGGER.debug(f"分块数量: {len(file_results)}")
            for i, (_, trans_list, json_list, _, chunk_metadata) in enumerate(file_results):
                LOGGER.debug(f"分块 {i}: start_index={chunk_metadata.start_index}, "
                             f"end_index={chunk_metadata.end_index}, "
                             f"chunk_non_cross_size={chunk_metadata.chunk_non_cross_size}, "
                             f"chunk_real_size={chunk_metadata.chunk_real_size}, "
                             f"cross_num={chunk_metadata.cross_num}, "
                             f"处理后长度={len(trans_list)}")
            all_trans_list, all_json_list = output_combiner.combine(
                [(trans_list, json_list, chunk_metadata)
                 for _, trans_list, json_list, _, chunk_metadata in file_results]
            )

            if all_trans_list and all_json_list:
                name_dict = load_name_table(joinpath(projectConfig.getProjectDir(), "人名替换表.csv")) \
                    if isPathExists(joinpath(projectConfig.getProjectDir(), "人名替换表.csv")) else {}
                final_result = update_json_with_transList(
                    all_trans_list, all_json_list, name_dict)

                output_file_path = file_name.replace(
                    projectConfig.getInputPath(), projectConfig.getOutputPath())
                save_func = file_save_funcs.get(file_name, save_json)
                save_func(output_file_path, final_result)

                if eng_type != "rebuildr":
                    find_problems(all_trans_list, projectConfig, gpt_dic)
                    cache_file_path = joinpath(
                        projectConfig.getCachePath(), basename(file_name))
                    save_transCache_to_json(
                        all_trans_list, cache_file_path, post_save=True)

                # 添加输入输出行数检查
                origin_input, _ = load_input(file_name, fPlugins)
                total_input_lines = len(json.loads(origin_input) if isinstance(
                    origin_input, str) else origin_input)
                total_output_lines = len(all_trans_list)
                if total_input_lines != total_output_lines:
                    LOGGER.warning(
                        f"文件 {file_name} 的输入行数 ({total_input_lines}) 与输出行数 ({total_output_lines}) 不匹配！\n可能是拆分文件时出现问题，请关闭交叉句功能或直接关闭分割文件功能，并向开发者反馈。")
        else:
            LOGGER.warning(f"没有成功处理任何内容: {file_name}")
