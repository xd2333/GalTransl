import json
from typing import List, Dict, Any, Optional, Union, Tuple
from os import makedirs, sep as os_sep
from os.path import join as joinpath, exists as isPathExists, getsize as getFileSize, basename, dirname
from tqdm.asyncio import tqdm as atqdm
from asyncio import Semaphore, gather, Queue
from time import time
import asyncio

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
                LOGGER.warning(f"无法解析JSON：{result[:10]}...")  # 打印前10个字符作为警告        
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

async def doLLMTranslateSingleFile(
    semaphore: asyncio.Semaphore,
    endpoint_queue: asyncio.Queue,
    file_path: str,
    projectConfig: CProjectConfig,
    eng_type: str,
    pre_dic: CNormalDic,
    post_dic: CNormalDic,
    gpt_dic: CGptDict,
    tlugins: list,
    fPlugins: list,
    proxyPool: CProxyPool,
    tokenPool: COpenAITokenPool,
    split_content: str = None,
    file_index: int = 0,
    total_splits: int = 1
) -> Tuple[bool, List, List, str]:
    async with semaphore:
        if endpoint_queue is not None:
            endpoint = await endpoint_queue.get()
        try:
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
            LOGGER.info(f"start translating: {file_name} (part {file_index+1}/{total_splits}), engine type: {eng_type}")

            match eng_type:
                case "gpt35-0613" | "gpt35-1106" | "gpt35-0125":
                    gptapi = CGPT35Translate(projectConfig, eng_type, proxyPool, tokenPool)
                case "gpt4" | "gpt4-turbo":
                    gptapi = CGPT4Translate(projectConfig, eng_type, proxyPool, tokenPool)
                case "newbing":
                    cookiePool: list[str] = []
                    for i in projectConfig.getBackendConfigSection("bingGPT4")["cookiePath"]:
                        cookiePool.append(joinpath(projectConfig.getProjectDir(), i))
                    gptapi = CBingGPT4Translate(projectConfig, cookiePool, proxyPool)
                case "sakura-009" | "sakura-010" | "galtransl-v1.5":
                    gptapi = CSakuraTranslate(projectConfig, eng_type, endpoint, proxyPool)
                case "rebuildr" | "rebuilda" | "dump-name":
                    gptapi = CRebuildTranslate(projectConfig, eng_type)
                case _:
                    raise ValueError(f"不支持的翻译引擎类型 {eng_type}")

            # 如果是分割的内容，直接使用传入的 split_content
            if split_content:
                origin_input = split_content
            else:
                # 读取文件内容
                origin_input = ""
                if getFileSize(input_file_path) == 0:
                    return True, [], [], file_path
                for plugin in fPlugins:
                    try:
                        origin_input = plugin.plugin_object.load_file(input_file_path)
                        break
                    except TypeError as e:
                        LOGGER.error(f"{file_name} 不是文件插件'{plugin.name}'支持的格式：{e}")
                    except Exception as e:
                        LOGGER.error(f"插件 {plugin.name} 读取文件 {file_name} 出错: {e}")
                if not origin_input:
                    with open(input_file_path, 'r', encoding='utf-8') as f:
                        origin_input = f.read()

            LOGGER.info(f"origin input: {str(origin_input)[:500]}...")

            # 处理内容
            try:
                trans_list, json_list = load_transList(origin_input)
                
                # 翻译前处理
                for tran in trans_list:
                    for plugin in tlugins:
                        try:
                            tran = plugin.plugin_object.before_src_processed(tran)
                        except Exception as e:
                            LOGGER.error(f"插件 {plugin.name} 执行失败: {e}")
                    tran.analyse_dialogue()
                    tran.post_jp = pre_dic.do_replace(tran.post_jp, tran)
                    if projectConfig.getDictCfgSection("usePreDictInName"):
                        if type(tran.speaker) == type(tran._speaker) == str:
                            tran.speaker = pre_dic.do_replace(tran.speaker, tran)

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
                    if "newbing" in eng_type or "gpt4" in eng_type:
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
                    for plugin in tlugins:
                        try:
                            tran = plugin.plugin_object.before_dst_processed(tran)
                        except Exception as e:
                            LOGGER.error(f"插件 {plugin.name} 执行失败: {e}")
                    tran.recover_dialogue_symbol()
                    tran.post_zh = post_dic.do_replace(tran.post_zh, tran)
                    if projectConfig.getDictCfgSection("usePostDictInName"):
                        if tran._speaker:
                            if type(tran.speaker) == type(tran._speaker) == list:
                                tran._speaker = [post_dic.do_replace(s, tran) for s in tran.speaker]
                            elif type(tran.speaker) == type(tran._speaker) == str:
                                tran._speaker = post_dic.do_replace(tran.speaker, tran)

            except Exception as e:
                LOGGER.error(f"处理内容时出错: {e}")
                LOGGER.error(f"问题内容: {origin_input[:500]}")
                return False, [], [], file_path

            et = time()
            LOGGER.info(f"文件 {file_name} (part {file_index+1}/{total_splits}) 翻译完成，用时 {et-st:.3f}s.")
            return True, trans_list, json_list, file_path
        finally:
            if endpoint_queue is not None:
                endpoint_queue.put_nowait(endpoint)

async def doLLMTranslate(
    projectConfig: CProjectConfig,
    tokenPool: COpenAITokenPool,
    proxyPool: Optional[CProxyPool],
    tPlugins: list,
    fPlugins: list,
    eng_type="offapi",
    input_splitter: InputSplitter = InputSplitter(),
    output_combiner: OutputCombiner = DictionaryCombiner(),
) -> bool:
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

    workersPerProject = projectConfig.getKey("workersPerProject")

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
                endpoint_queue.put_nowait(endpoint)
        LOGGER.info(f"当前使用 {workersPerProject} 个Sakura worker引擎")
    else:
        endpoint_queue = None
    
    # 人名表初始化
    if "dump-name" in eng_type:
        global name_dict
        name_dict = {}

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
    split_file = projectConfig.getKey("splitFile")  # 新增：获取分割文件的开关

    for file_name in file_list:
        # 读取文件内容
        origin_input = ""
        save_func = None
        for plugin in fPlugins:
            try:
                origin_input = plugin.plugin_object.load_file(file_name)
                save_func = plugin.plugin_object.save_file
                break
            except TypeError as e:
                LOGGER.error(f"{file_name} 不是文件插件'{plugin.name}'支持的格式：{e}")
            except Exception as e:
                LOGGER.error(f"插件 {plugin.name} 读取文件 {file_name} 出错: {e}")
        
        if not origin_input and file_name.endswith(".json"):
            with open(file_name, 'r', encoding='utf-8') as f:
                origin_input = f.read()
            save_func = save_json

        file_save_funcs[file_name] = save_func
        
        # 使用 input_splitter 拆分内容，只有在 split_file 为 True 时才进行分割
        split_contents = input_splitter.split(origin_input) if split_file else [origin_input]
        
        # 为每个分割的内容创建一个任务，并添加交叉句
        for i, split_content in enumerate(split_contents):
            if isinstance(split_content, str):
                try:
                    split_content = json.loads(split_content)
                except json.JSONDecodeError:
                    split_content = [split_content]  # 如果不是有效的JSON，将其作为单元素列表

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

            # 确保 split_content 是 JSON 字符串
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

    # 处理结果
    for file_name in file_list:
        file_results = [result for result in results if result[0] and result[1] and result[2] and result[3] == file_name]
        if file_results:
            all_trans_list = []
            all_json_list = []
            for i, (success, trans_list, json_list, result_file_name) in enumerate(file_results):
                # 处理交叉句子
                if split_file and len(file_results) > 1:
                    # 如果是第一个分片，只移除末尾的一半交叉句
                    if i == 0:
                        trans_list = trans_list[:-cross_num]
                        json_list = json_list[:-cross_num]
                    # 如果是最后一个分片，只移除开头的一半交叉句
                    elif i == len(file_results) - 1:
                        trans_list = trans_list[cross_num:]
                        json_list = json_list[cross_num:]
                    # 对于中间的分片，移除开头和末尾各一半的交叉句
                    else:
                        trans_list = trans_list[cross_num:-cross_num]
                        json_list = json_list[cross_num:-cross_num]
                
                all_trans_list.extend(trans_list)
                all_json_list.extend(json_list)

            # 使用所有处理后的 trans_list 和 json_list
            if all_trans_list and all_json_list:
                if isPathExists(joinpath(project_dir, "人名替换表.csv")):
                    name_dict = load_name_table(joinpath(project_dir, "人名替换表.csv"))
                else:
                    name_dict = {}
                final_result = update_json_with_transList(all_trans_list, all_json_list, name_dict)

                # 保存最终结果
                output_file_path = file_name.replace(projectConfig.getInputPath(), projectConfig.getOutputPath())
                save_func = file_save_funcs.get(file_name, save_json)
                save_func(output_file_path, final_result)

                if eng_type != "rebuildr":
                    find_problems(all_trans_list, projectConfig, gpt_dic)
                    cache_file_path = joinpath(projectConfig.getCachePath(), basename(file_name))
                    save_transCache_to_json(all_trans_list, cache_file_path, post_save=True)
        else:
            LOGGER.error(f"没有成功处理任何内容: {file_name}")

    if "dump-name" in eng_type:
        import csv
        proj_dir = projectConfig.getProjectDir()
        name_dict = dict(sorted(name_dict.items(), key=lambda item: item[1], reverse=True))
        with open(joinpath(proj_dir, "人名替换表.csv"), "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["JP_Name", "CN_Name", "Count"])  # 写入表头
            for name, count in name_dict.items():
                writer.writerow([name, "", count])
            LOGGER.info(f"name已保存到'人名替换表.csv'（UTF-8编码，用Emeditor编辑），填入CN_Name后可用于后续翻译name字段。")

    return True