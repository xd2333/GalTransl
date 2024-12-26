import orjson, re
import os
from GalTransl import LOGGER
from GalTransl.GTPlugin import GFilePlugin


class file_plugin(GFilePlugin):
    def gtp_init(self, plugin_conf: dict, project_conf: dict):
        """
        This method is called when the plugin is loaded.在插件加载时被调用。
        :param plugin_conf: The settings for the plugin.插件yaml中所有设置的dict。
        :param project_conf: The settings for the project.项目yaml中common下设置的dict。
        """
        self.all_stats = []  # 存储所有句子的统计数据
        self.file_stats = {}  # 按文件存储统计数据
        self.line_count = 0
        pass                                          

    def load_file(self, file_path: str) -> list:
        """
        This method is called to load a file.
        加载文件时被调用。
        :param file_path: The path of the file to load.文件路径。
        :return: A list of objects with message and name(optional).返回一个包含message和name(可空)的对象列表。
        """
        if not file_path.endswith(".json"):
            # 检查不支持的文件类型并抛出TypeError
            raise TypeError("请检查filePlugin的配置并选择合适的文件插件.")
        with open(file_path, "r", encoding="utf-8") as f:
            json_list = orjson.loads(f.read())
        return json_list

    def save_file(self, file_path: str, transl_json: list):
        """
        This method is called to save a file.
        保存文件时被调用。
        :param file_path: The path of the file to save.保存文件路径
        :param transl_json: A list of objects same as the return of load_file().load_file提供的json在翻译message和name后的结果。
        :return: None.
        """
        file_stats = []
        
        # 收集该文件所有句子的统计数据
        for item in transl_json:
            message = item['message']
            ref = item['ref']
            if not message or not ref:
                continue
            message = message.replace("\n", "").replace("\r", "")
            ref = ref.replace("\n", "").replace("\r", "")
            stats = get_chrf_statistics(message, ref)  # 获取统计数据而不是分数
            file_stats=add_stats(file_stats,stats)
            self.all_stats=add_stats(self.all_stats,stats)
            item['chrf_score'] = compute_f_score(stats)  # 单句的分数仍然计算
            self.line_count += 1
        
        # 使用累积的统计数据计算文件的总体分数
        self.file_stats[file_path] = file_stats
        
        with open(file_path, "wb") as f:
            f.write(orjson.dumps(transl_json, option=orjson.OPT_INDENT_2))

    def gtp_final(self):
        """
        This method is called after all translations are done.
        在所有文件翻译完成之后的动作，例如输出提示信息。
        """
        # 使用累积的统计数据计算每个文件的分数
        for file_path, stats in self.file_stats.items():
            file_score = compute_f_score(stats)
            file_name=os.path.basename(file_path)
            LOGGER.info(f"[chrF翻译评估] {file_name} 的 chrF 分数为 {file_score:.2f}")
        
        # 使用所有统计数据计算总体分数
        total_score = compute_f_score(self.all_stats)
        LOGGER.info(f"[chrF翻译评估] 总体 chrF 分数为 {total_score:.2f}")


def get_chrf_statistics(input: str, ref: str, n: int = 6) -> list:
    """获取chrF统计数据"""
    stats = []
    for i in range(1, n + 1):
        hyp_ngrams = extract_char_ngrams(input, i)
        ref_ngrams = extract_char_ngrams(ref, i)
        stats.extend(get_match_statistics(hyp_ngrams, ref_ngrams))
    return stats

def extract_char_ngrams(text: str, n: int) -> dict:
    # Remove whitespace and get char n-grams
    text = ''.join(text.split())
    ngrams = {}
    for i in range(len(text) - n + 1):
        gram = text[i:i+n]
        ngrams[gram] = ngrams.get(gram, 0) + 1
    return ngrams

def get_match_statistics(hyp_ngrams: dict, ref_ngrams: dict) -> list:
    # Calculate matches between hypothesis and reference n-grams
    match_count = 0
    hyp_count = sum(hyp_ngrams.values())
    ref_count = sum(ref_ngrams.values())
    
    for ng, count in hyp_ngrams.items():
        if ng in ref_ngrams:
            match_count += min(count, ref_ngrams[ng])
            
    return [hyp_count if ref_ngrams else 0, ref_count, match_count]

def add_stats(stats_a,stats_b):
    result=[]
    if not stats_a:
        return stats_b
    if not stats_b:
        return stats_a
    for i in range(len(stats_a)):
        result.append(stats_a[i]+stats_b[i])
    return result
    

def compute_f_score(statistics: list, beta: int = 2) -> float:
    """Calculate chrF score from match statistics
    
    Args:
        statistics: List of [hyp_count, ref_count, match_count] for each n-gram order
        beta: Weight of recall versus precision (default: 2)
    
    Returns:
        chrF score between 0 and 100
    """
    eps = 1e-16
    score = 0.0
    effective_order = 0
    factor = beta ** 2
    avg_prec, avg_rec = 0.0, 0.0

    # Process statistics for each n-gram order
    n = len(statistics) // 3
    for i in range(n):
        n_hyp, n_ref, n_match = statistics[3 * i: 3 * i + 3]
        
        prec = n_match / n_hyp if n_hyp > 0 else eps
        rec = n_match / n_ref if n_ref > 0 else eps

        if n_hyp > 0 and n_ref > 0:
            avg_prec += prec
            avg_rec += rec
            effective_order += 1

    if effective_order == 0:
        return 0.0
        
    avg_prec /= effective_order
    avg_rec /= effective_order

    if avg_prec + avg_rec:
        score = (1 + factor) * avg_prec * avg_rec
        score /= ((factor * avg_prec) + avg_rec)
        return 100 * score
    return 0.0
