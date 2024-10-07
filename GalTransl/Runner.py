import os, time, sys
from os.path import exists as isPathExists
from os import makedirs as mkdir
import logging, colorlog
from GalTransl import LOGGER, TRANSLATOR_SUPPORTED, new_version, GALTRANSL_VERSION
from GalTransl.GTPlugin import GTextPlugin, GFilePlugin
from GalTransl.COpenAI import COpenAITokenPool,init_sakura_endpoint_queue
from GalTransl.yapsy.PluginManager import PluginManager
from GalTransl.ConfigHelper import CProjectConfig, CProxyPool
from GalTransl.Frontend.LLMTranslate import doLLMTranslate
from GalTransl.CSplitter import (
    DictionaryCountSplitter,
    EqualPartsSplitter,
    DictionaryCombiner,
)


CONSOLE_FORMAT = colorlog.ColoredFormatter(
    "[%(asctime)s]%(log_color)s[%(levelname)s]%(reset)s%(message)s",
    datefmt="%m-%d %H:%M:%S",
    log_colors={
        "DEBUG": "white",
        "INFO": "white",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
)
File_FORMAT = logging.Formatter(
    "[%(asctime)s][%(levelname)s] %(message)s", datefmt="%m-%d %H:%M:%S"
)


async def run_galtransl(cfg: CProjectConfig, translator: str):
    PROJECT_DIR = cfg.getProjectDir()
    cfg.select_translator=translator

    def get_pluginInfo_path(name):
        if "(project_dir)" in name:
            name = name.replace("(project_dir)", "")
            return os.path.join(PROJECT_DIR, "plugins", name, f"{name}.yaml")
        else:
            return os.path.join(os.path.abspath("plugins"), name, f"{name}.yaml")

    def print_plugin_list(plugin_manager: PluginManager):
        LOGGER.info("插件列表:")
        for candidate in plugin_manager.getPluginCandidates():
            plug_path = os.path.dirname(candidate[1])
            plug_name = os.path.basename(plug_path)
            if "text_example_nouse" in plug_name:
                continue
            plug_info = candidate[2]
            plug_type = plug_info.yaml_dict["Core"].get("Type", "unknown").lower()
            if PROJECT_DIR in plug_path:
                plug_type = "Project-local " + plug_type
            if "Settings" in plug_info.yaml_dict:
                plug_settings = plug_info.yaml_dict["Settings"]
            else:
                plug_settings = {}

            LOGGER.info(f"  > {plug_name} ({plug_type} Plugin)")
            LOGGER.info(
                f"    名称：{plug_info.name} v{plug_info.version} by {plug_info.author}"
            )
            LOGGER.info(f"    描述: {plug_info.description}")
            LOGGER.info(f"    路径: {plug_path}")
            if plug_settings:
                LOGGER.info(f"    设置: ")
                for key, value in plug_settings.items():
                    LOGGER.info(f"     - {key}: {value}")
            LOGGER.info("---------------------------------")
        LOGGER.info("* 要修改插件的设置，可以进入插件路径，编辑其中的.yaml文件。")

    start_time = time.time()

    if translator not in TRANSLATOR_SUPPORTED.keys():
        raise Exception(f"不支持的翻译器: {translator}")

    # 日志初始化
    for handler in LOGGER.handlers:
        LOGGER.removeHandler(handler)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(CONSOLE_FORMAT)
    LOGGER.addHandler(handler)
    if cfg.getCommonConfigSection().get("saveLog", False):
        log_path = os.path.join(PROJECT_DIR, "GalTransl.log")
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(File_FORMAT)
        LOGGER.addHandler(file_handler)

    # 目录初始化
    for dir_path in [
        cfg.getInputPath(),
        cfg.getOutputPath(),
        cfg.getCachePath(),
    ]:
        if not isPathExists(dir_path):
            LOGGER.info("%s 文件夹不存在，让我们创建它...", dir_path)
            mkdir(dir_path)
    # 插件初始化
    plugin_manager = PluginManager(
        {"GTextPlugin": GTextPlugin, "GFilePlugin": GFilePlugin},
        ["plugins", os.path.join(PROJECT_DIR, "plugins")],
    )
    plugin_manager.locatePlugins()
    # 打印插件列表
    if translator == "show-plugs":
        print_plugin_list(plugin_manager)
        return
    new_candidates = []
    for tname in cfg.getTextPluginList():
        info_path = get_pluginInfo_path(tname)
        candidate = plugin_manager.getPluginCandidateByInfoPath(info_path)
        if candidate:
            new_candidates.append(candidate)
        else:
            LOGGER.warning(f"未找到文本插件: {tname}，跳过该插件")
    fname = cfg.getFilePlugin()
    if fname:
        info_path = get_pluginInfo_path(fname)
        candidate = plugin_manager.getPluginCandidateByInfoPath(info_path)
        assert candidate, f"未找到文件插件: {fname}，请检查设置"
        new_candidates.append(candidate)

    plugin_manager.setPluginCandidates(new_candidates)
    plugin_manager.loadPlugins()
    text_plugins = plugin_manager.getPluginsOfCategory("GTextPlugin")
    file_plugins = plugin_manager.getPluginsOfCategory("GFilePlugin")
    for plugin in file_plugins + text_plugins:
        plugin_conf = plugin.yaml_dict
        plugin_module = plugin_conf["Core"]["Module"]
        project_conf = cfg.getCommonConfigSection()
        project_plugin_conf = cfg.getPluginConfigSection()
        if plugin_module in project_plugin_conf:
            plugin_conf["Settings"].update(project_plugin_conf[plugin_module])
        project_conf["project_dir"] = cfg.getProjectDir()
        try:
            LOGGER.info(f'加载插件"{plugin.name}"...')
            plugin.plugin_object.gtp_init(plugin_conf, project_conf)
        except Exception as e:
            LOGGER.error(f'插件"{plugin.name}"加载失败: {e}')
            if plugin in text_plugins:
                text_plugins.remove(plugin)
            elif plugin in file_plugins:
                file_plugins.remove(plugin)

    # proxyPool初始化
    proxyPool = CProxyPool(cfg) if cfg.getKey("internals.enableProxy") else None
    if proxyPool and translator not in [
        "rebuildr",
        "rebuilda",
        "dump-name",
        "show-plugs",
    ]:
        await proxyPool.checkAvailablity()
        if not proxyPool.proxies:
            raise Exception("没有可用的代理，请检查代理设置")
    if not proxyPool:
        LOGGER.warning("不使用代理")

    # OpenAITokenPool初始化
    if "gpt" in translator:
        OpenAITokenPool = COpenAITokenPool(cfg, translator)
        await OpenAITokenPool.checkTokenAvailablity(
            proxyPool.getProxy() if proxyPool else None, translator
        )
    else:
        OpenAITokenPool = None
    
    # 初始化sakura端点队列
    if "sakura" in translator or "galtransl" in translator:
        sakura_endpoint_queue = await init_sakura_endpoint_queue(cfg)
        cfg.endpointQueue = sakura_endpoint_queue

    # 检查更新
    if new_version and new_version[0] != GALTRANSL_VERSION:
        LOGGER.info(
            f"\033[32m检测到新版本: {new_version[0]}\033[0m  当前版本: {GALTRANSL_VERSION}"
        )
        LOGGER.info(
            f"\033[32m更新地址：https://github.com/xd2333/GalTransl/releases\033[0m"
        )

    if project_conf.get("splitFile", False):
        splitFileNum = int(project_conf.get("splitFileNum", -1))
        cross_num = int(project_conf.get("splitFileCrossNum", 0))
        if "dump-name" in translator: # 提取人名表时不交叉
            cross_num = 0
        if splitFileNum == -1:
            splitFileNum = int(project_conf.get("workersPerProject", -1))
        splitFileMethod = project_conf.get("splitFileMethod", "EqualPartsSplitter")
        if splitFileMethod == "DictionaryCountSplitter":
            assert splitFileNum > 10, "DictionaryCountSplitter下分割数量必须大于10"
            input_splitter = DictionaryCountSplitter(splitFileNum, cross_num)
        elif splitFileMethod == "EqualPartsSplitter":
            input_splitter = EqualPartsSplitter(splitFileNum, cross_num)
        else:
            raise Exception(f"不支持的分割方法: {splitFileMethod}")

        # 默认的输出合并器
        output_combiner = DictionaryCombiner()
    else:
        input_splitter = EqualPartsSplitter(1)
        output_combiner = DictionaryCombiner()
    
    cfg.tPlugins = text_plugins
    cfg.fPlugins = file_plugins
    cfg.tokenPool = OpenAITokenPool
    cfg.proxyPool = proxyPool
    cfg.input_splitter = input_splitter

    await doLLMTranslate(cfg)

    for plugin in file_plugins + text_plugins:
        plugin.plugin_object.gtp_final()

    end_time = time.time()
    LOGGER.info(f"总耗时: {end_time-start_time:.3f}s")
