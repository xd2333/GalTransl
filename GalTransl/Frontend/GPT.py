from typing import List, Dict, Any, Optional, Union, Tuple
from os import makedirs, sep as os_sep
from os.path import join as joinpath, exists as isPathExists, getsize as getFileSize, basename, dirname
from tqdm.asyncio import tqdm as atqdm
from asyncio import Semaphore, gather, Queue
from time import time
import asyncio
import json

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

class InputSplitter:
    @staticmethod
    def split(content: Union[str, List]) -> List[str]:
        # 如果已经是列表，直接返回JSON字符串
        if isinstance(content, list):
            return [json.dumps(content, ensure_ascii=False, indent=2)]
        # 如果是字符串，尝试解析为JSON，如果失败则直接返回
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return [json.dumps(data, ensure_ascii=False, indent=2)]
        except json.JSONDecodeError:
            pass
        return [content]


class DictionaryCountSplitter(InputSplitter):
    def __init__(self, dict_count: int):
        self.dict_count = dict_count

    def split(self, content: Union[str, List]) -> List[str]:
        # 如果是字符串，尝试解析为JSON
        if isinstance(content, str):
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                LOGGER.warning(f"无法解析JSON：{content[:10]}...")  # 打印前10个字符作为警告        
                return [content]  # 如果解析失败，返回原内容
        else:
            data = content

        # 确保data是列表
        if not isinstance(data, list):
            return [json.dumps(data, ensure_ascii=False, indent=2)]

        result = []
        current_chunk = []
        for item in data:
            current_chunk.append(item)
            if len(current_chunk) >= self.dict_count:
                result.append(json.dumps(current_chunk, ensure_ascii=False, indent=2))
                current_chunk = []
        
        if current_chunk:
            result.append(json.dumps(current_chunk, ensure_ascii=False, indent=2))
        
        return result


class EqualPartsSplitter(InputSplitter):
    def __init__(self, parts: int):
        self.parts = parts

    def split(self, content: Union[str, List]) -> List[str]:
        # 如果是字符串，尝试解析为JSON
        if isinstance(content, str):
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                return [content]  # 如果解析失败，返回原内容
        else:
            data = content

        # 确保data是列表
        if not isinstance(data, list):
            return [json.dumps(data, ensure_ascii=False, indent=2)]

        total_items = len(data)
        items_per_part = total_items // self.parts
        remainder = total_items % self.parts

        result = []
        start = 0
        for i in range(self.parts):
            end = start + items_per_part + (1 if i < remainder else 0)
            chunk = data[start:end]
            result.append(json.dumps(chunk, ensure_ascii=False, indent=2))
            start = end

        return result


class OutputCombiner:
    @staticmethod
    def combine(results: List[str]) -> str:
        # 默认实现：直接返回
        return results[0] if results else ''


class DictionaryCombiner(OutputCombiner):
    @staticmethod
    def combine(results: List[str]) -> str:
        combined_data = []
        for result in results:
            try:
                data = json.loads(result)
                combined_data.extend(data)
            except json.JSONDecodeError:
                LOGGER.warning(f"无法解析JSON：{result[:10]}...")  # 打印前10个字符作为警告        
        return json.dumps(combined_data, ensure_ascii=False, indent=2)


async def init_endpoint_queue(projectConfig: CProjectConfig, workersPerProject: int, eng_type: str) -> Optional[Queue]:
    if "sakura" in eng_type or "galtransl" in eng_type:
        endpoint_queue = asyncio.Queue()
        backendSpecific = projectConfig.projectConfig["backendSpecific"]
        section_name = "SakuraLLM" if "SakuraLLM" in backendSpecific else "Sakura"
        if "endpoints" in projectConfig.getBackendConfigSection(section_name):
            endpoints = projectConfig.getBackendConfigSection(section_name)["endpoints"]
        else:
            endpoints = [projectConfig.getBackendConfigSection(section_name)["endpoint"]]
        repeated = (workersPerProject + len(endpoints) - 1) // len(endpoints)
        for _ in range(repeated):
            for endpoint in endpoints:
                await endpoint_queue.put(endpoint)
        LOGGER.info(f"当前使用 {workersPerProject} 个Sakura worker引擎")
        return endpoint_queue
    else:
        return None


def init_dictionaries(projectConfig: CProjectConfig) -> Tuple[CNormalDic, CNormalDic, CGptDict]:
    pre_dic_dir = projectConfig.getDictCfgSection()["preDict"]
    post_dic_dir = projectConfig.getDictCfgSection()["postDict"]
    gpt_dic_dir = projectConfig.getDictCfgSection()["gpt.dict"]
    default_dic_dir = projectConfig.getDictCfgSection()["defaultDictFolder"]
    project_dir = projectConfig.getProjectDir()
    
    pre_dic = CNormalDic(initDictList(pre_dic_dir, default_dic_dir, project_dir))
    post_dic = CNormalDic(initDictList(post_dic_dir, default_dic_dir, project_dir))
    gpt_dic = CGptDict(initDictList(gpt_dic_dir, default_dic_dir, project_dir))

    if projectConfig.getDictCfgSection().get("sortPrePostDict", False):
        pre_dic.sort_dic()
        post_dic.sort_dic()

    return pre_dic, post_dic, gpt_dic


async def get_gptapi(projectConfig: CProjectConfig, eng_type: str, endpoint: Optional[str], proxyPool: Optional[CProxyPool], tokenPool: COpenAITokenPool):
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
                raise ValueError(f"Endpoint is required for engine type {eng_type}")
            return CSakuraTranslate(projectConfig, eng_type, endpoint, proxyPool)
        case "rebuildr" | "rebuilda" | "dump-name":
            return CRebuildTranslate(projectConfig, eng_type)
        case _:
            raise ValueError(f"不支持的翻译引擎类型 {eng_type}")


def load_input(file_path: str, fPlugins: list) -> Tuple[str, Any]:
    origin_input = ""
    save_func = None
    for plugin in fPlugins:
        try:
            origin_input = plugin.plugin_object.load_file(file_path)
            save_func = plugin.plugin_object.save_file
            break
        except TypeError as e:
            LOGGER.error(f"{file_path} 不是文件插件'{plugin.name}'支持的格式：{e}")
        except Exception as e:
            LOGGER.error(f"插件 {plugin.name} 读取文件 {file_path} 出错: {e}")

    if not origin_input and file_path.endswith(".json"):
        with open(file_path, 'r', encoding='utf-8') as f:
            origin_input = f.read()
        save_func = save_json

    return origin_input, save_func

async def doLLMTranslateSingleFile(
    semaphore: Semaphore,
    endpoint_queue: Queue,
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
    split_content: str = None,
    file_index: int = 0,
    total_splits: int = 1
) -> Tuple[bool, List, List, str]:
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
            LOGGER.info(f"开始翻译文件: {file_name} (part {file_index+1}/{total_splits}), 引擎类型: {eng_type}")

            gptapi = await get_gptapi(projectConfig, eng_type, endpoint, proxyPool, tokenPool)

            # 如果是分割的内容，直接使用传入的 split_content
            if split_content:
                origin_input = split_content
            else:
                # 读取文件内容
                origin_input, save_func = load_input(input_file_path, fPlugins)
                if not origin_input and getFileSize(input_file_path) == 0:
                    return True, [], [], file_path

            LOGGER.debug(f"原始输入: {str(origin_input)[:500]}...")

            try:
                trans_list, json_list = load_transList(origin_input)
            except Exception as e:
                LOGGER.error(f"文件 {file_name} 加载翻译列表失败: {e}")
                return False, [], [], file_path
            
            # 导出人名表功能
            if "dump-name" in eng_type:
                for tran in trans_list:
                    if tran.speaker and isinstance(tran.speaker, str):
                        if tran.speaker not in name_dict:
                            name_dict[tran.speaker] = 0
                        name_dict[tran.speaker] += 1
                        LOGGER.debug(f"发现人名: {tran.speaker}")
                LOGGER.info(f"人名表: {name_dict}")
                return True, trans_list, json_list, file_path

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

            et = time()
            LOGGER.info(f"文件 {file_name} (part {file_index+1}/{total_splits}) 翻译完成，用时 {et-st:.3f}s.")
            return True, trans_list, json_list, file_path
        finally:
            if endpoint_queue is not None and endpoint is not None:
                endpoint_queue.put_nowait(endpoint)

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
                    LOGGER.error(f"插件 {plugin.name} 执行失败: {e}")
            tran.recover_dialogue_symbol()
            tran.post_zh = post_dic.do_replace(tran.post_zh, tran)
            if projectConfig.getDictCfgSection("usePostDictInName"):
                if tran._speaker:
                    if isinstance(tran.speaker, list) and isinstance(tran._speaker, list):
                        tran._speaker = [post_dic.do_replace(s, tran) for s in tran.speaker]
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

async def postprocess_results(
    file_list: List[str],
    results: List[Tuple[bool, List, List, str]],
    eng_type: str,
    projectConfig: CProjectConfig,
    file_save_funcs: Dict[str, Any],
    split_file: bool,
    cross_num: int,
    gpt_dic: CGptDict
):
    if "dump-name" in eng_type:
        import csv
        global name_dict
        proj_dir = projectConfig.getProjectDir()
        LOGGER.info(f"开始保存人名表...{name_dict}")
        name_dict = dict(sorted(name_dict.items(), key=lambda item: item[1], reverse=True))
        LOGGER.info(f"共发现 {len(name_dict)} 个人名，按出现次数排序如下：")
        for name, count in name_dict.items():
            LOGGER.info(f"{name}: {count}")
        with open(joinpath(proj_dir, "人名替换表.csv"), "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["JP_Name", "CN_Name", "Count"])  # 写入表头
            for name, count in name_dict.items():
                writer.writerow([name, "", count])
        LOGGER.info(f"name已保存到'人名替换表.csv'（UTF-8编码，用Emeditor编辑），填入CN_Name后可用于后续翻译name字段。")

    for file_name in file_list:
        file_results = [result for result in results if result[0] and result[1] and result[2] and result[3] == file_name]
        if file_results:
            all_trans_list = []
            all_json_list = []
            for i, (success, trans_list, json_list, result_file_name) in enumerate(file_results):
                # 处理交叉句子
                if split_file and len(file_results) > 1:
                    if i == 0:
                        trans_list = trans_list[:-cross_num]
                        json_list = json_list[:-cross_num]
                    elif i == len(file_results) - 1:
                        trans_list = trans_list[cross_num:]
                        json_list = json_list[cross_num:]
                    else:
                        trans_list = trans_list[cross_num:-cross_num]
                        json_list = json_list[cross_num:-cross_num]
                
                all_trans_list.extend(trans_list)
                all_json_list.extend(json_list)

            if all_trans_list and all_json_list:
                name_dict = load_name_table(joinpath(projectConfig.getProjectDir(), "人名替换表.csv")) \
                    if isPathExists(joinpath(projectConfig.getProjectDir(), "人名替换表.csv")) else {}
                final_result = update_json_with_transList(all_trans_list, all_json_list, name_dict)

                output_file_path = file_name.replace(projectConfig.getInputPath(), projectConfig.getOutputPath())
                save_func = file_save_funcs.get(file_name, save_json)
                save_func(output_file_path, final_result)

                if eng_type != "rebuildr":
                    find_problems(all_trans_list, projectConfig, gpt_dic)
                    cache_file_path = joinpath(projectConfig.getCachePath(), basename(file_name))
                    save_transCache_to_json(all_trans_list, cache_file_path, post_save=True)
        else:
            LOGGER.error(f"没有成功处理任何内容: {file_name}")

async def doLLMTranslate(
    projectConfig: CProjectConfig,
    tokenPool: COpenAITokenPool,
    proxyPool: Optional[CProxyPool],
    tPlugins: list,
    fPlugins: list,
    eng_type: str = "offapi",
    input_splitter: InputSplitter = InputSplitter(),
    output_combiner: OutputCombiner = DictionaryCombiner(),
) -> bool:
    pre_dic, post_dic, gpt_dic = init_dictionaries(projectConfig)
    workersPerProject = projectConfig.getKey("workersPerProject")
    endpoint_queue = await init_endpoint_queue(projectConfig, workersPerProject, eng_type)

    file_list = get_file_list(projectConfig.getInputPath())
    if not file_list:
        raise RuntimeError(f"{projectConfig.getInputPath()}中没有待翻译的文件")
    semaphore = asyncio.Semaphore(workersPerProject)
    progress_bar = atqdm(total=len(file_list), desc="Processing files", dynamic_ncols=True, leave=False)

    async def run_task(task):
        result = await task
        progress_bar.update(1)
        return result

    all_tasks = []
    file_save_funcs = {}
    cross_num = projectConfig.getKey("splitFileCrossNum")
    split_file = projectConfig.getKey("splitFile")

    for file_name in file_list:
        origin_input, save_func = load_input(file_name, fPlugins)
        file_save_funcs[file_name] = save_func

        split_contents = input_splitter.split(origin_input) if split_file else [origin_input]
        
        for i, split_content in enumerate(split_contents):
            if isinstance(split_content, str):
                try:
                    split_content = json.loads(split_content)
                except json.JSONDecodeError:
                    split_content = [split_content]

            if split_file:
                if i > 0:
                    prev_content = split_contents[i-1]
                    if isinstance(prev_content, str):
                        try:
                            prev_content = json.loads(prev_content)
                        except json.JSONDecodeError:
                            prev_content = [prev_content]
                    split_content = prev_content[-cross_num:] + split_content

                if i < len(split_contents) - 1:
                    next_content = split_contents[i+1]
                    if isinstance(next_content, str):
                        try:
                            next_content = json.loads(next_content)
                        except json.JSONDecodeError:
                            next_content = [next_content]
                    split_content = split_content + next_content[:cross_num]

            if isinstance(split_content, list):
                split_content = json.dumps(split_content, ensure_ascii=False, indent=2)

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
                    split_content,
                    i,
                    len(split_contents)
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
        split_file,
        cross_num,
        gpt_dic
    )

    return True