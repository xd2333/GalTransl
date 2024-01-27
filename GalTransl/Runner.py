import os, time
from os.path import exists as isPathExists
from os import makedirs as mkdir

from GalTransl import LOGGER,TRANSLATOR_SUPPORTED
from GalTransl.GTPlugin import GTTextPlugin, GTFilePlugin
from GalTransl.COpenAI import COpenAITokenPool
from GalTransl.yapsy.PluginManager import PluginManager
from GalTransl.ConfigHelper import CProjectConfig, CProxyPool
from GalTransl.Frontend.GPT import doLLMTranslate


async def run_galtransl(cfg: CProjectConfig, translator: str):
    start_time = time.time()
    PROJECT_DIR = cfg.getProjectDir()
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
    def get_plugin_path(name):
        if "(project_dir)" in name:
            name = name.replace("(project_dir)", "")
            return os.path.join(PROJECT_DIR, "plugins", name)
        else:
            return os.path.join(os.path.abspath("plugins"), name)
    plugin_manager = PluginManager(
        {"GTTextPlugin": GTTextPlugin, "GTFilePlugin": GTFilePlugin},
        ["plugins", os.path.join(PROJECT_DIR, "plugins")],
    )
    plugin_manager.locatePlugins()
    plugin_candidates = plugin_manager.getPluginCandidates()
    new_candidates = []
    for name in cfg.getTextPluginList():
        path = get_plugin_path(name)
        for candidate in plugin_candidates:
            if path in candidate[0]:
                new_candidates.append(candidate)
                break
        else:
            LOGGER.warning(f"未找到插件: {name}，请检查设置")
    plugin_manager.setPluginCandidates(new_candidates)
    plugin_manager.loadPlugins()
    text_plugins = plugin_manager.getPluginsOfCategory("GTTextPlugin")
    for plugin in text_plugins:
        details = plugin.details
        settings = details["Settings"] if "Settings" in details else None
        try:
            LOGGER.info(f'加载插件"{plugin.name}"')
            plugin.plugin_object.gtp_init(settings)
        except Exception as e:
            LOGGER.error(f'插件"{plugin.name}"加载失败: {e}')

    # proxyPool初始化
    proxyPool = CProxyPool(cfg) if cfg.getKey("internals.enableProxy") else None
    if proxyPool and translator != "Rebuild":
        await proxyPool.checkAvailablity()

    # OpenAITokenPool初始化
    if "gpt" in translator:
        OpenAITokenPool = COpenAITokenPool(cfg, translator)
        await OpenAITokenPool.checkTokenAvailablity(
            proxyPool.getProxy() if proxyPool else None, translator
        )
    else:
        OpenAITokenPool = None

    await doLLMTranslate(cfg, OpenAITokenPool, proxyPool, text_plugins, translator)

    for plugin in text_plugins:
        plugin.plugin_object.gtp_final()

    end_time = time.time()
    LOGGER.info(f"总耗时: {end_time-start_time:.3f}s")
