import os, time
from os.path import exists as isPathExists
from os import makedirs as mkdir

from GalTransl import LOGGER, TRANSLATOR_SUPPORTED
from GalTransl.GTPlugin import GTextPlugin, GFilePlugin
from GalTransl.COpenAI import COpenAITokenPool
from GalTransl.yapsy.PluginManager import PluginManager
from GalTransl.ConfigHelper import CProjectConfig, CProxyPool
from GalTransl.Frontend.GPT import doLLMTranslate


async def run_galtransl(cfg: CProjectConfig, translator: str):
    PROJECT_DIR = cfg.getProjectDir()

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
            plug_info = candidate[2]
            plug_type = plug_info.yaml_dict["Core"].get("Type", "unknown").lower()
            if PROJECT_DIR in plug_path:
                plug_type = "Project-local " + plug_type
            LOGGER.info(f" {plug_name} ({plug_type} Plugin)")
            LOGGER.info(f"  > {plug_info.name} v{plug_info.version} by {plug_info.author}")
            LOGGER.info(f"    描述: {plug_info.description}")
            LOGGER.info(f"    路径: {plug_path}")
            LOGGER.info("---------------------------------")

    start_time = time.time()

    if translator not in TRANSLATOR_SUPPORTED.keys():
        raise Exception(f"不支持的翻译器: {translator}")
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
    if translator == "showplugs":
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
    if fname and fname != "file_galtransl_json":
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
        project_conf = cfg.getCommonConfigSection()
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
    if proxyPool and translator != "Rebuild":
        await proxyPool.checkAvailablity()
        if not proxyPool.proxies:
            raise Exception("没有可用的代理，请检查代理设置")

    # OpenAITokenPool初始化
    if "gpt" in translator:
        OpenAITokenPool = COpenAITokenPool(cfg, translator)
        await OpenAITokenPool.checkTokenAvailablity(
            proxyPool.getProxy() if proxyPool else None, translator
        )
    else:
        OpenAITokenPool = None

    await doLLMTranslate(
        cfg, OpenAITokenPool, proxyPool, text_plugins, file_plugins, translator
    )

    for plugin in text_plugins:
        plugin.plugin_object.gtp_final()

    end_time = time.time()
    LOGGER.info(f"总耗时: {end_time-start_time:.3f}s")


