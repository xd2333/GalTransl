from typing import Dict, List
import csv
from os.path import join as joinpath
from GalTransl.CSplitter import SplitChunkMetadata
from GalTransl import LOGGER
from GalTransl.ConfigHelper import CProjectConfig


def load_name_table(name_table_path: str) -> Dict[str, str]:
    """
    This function loads the name table from the given path.

    Args:
    - name_table_path: The path to the name table.

    Returns:
    - A dictionary containing the name table.
    """
    name_table: Dict[str, str] = {}
    with open(name_table_path, mode="r", encoding="utf8") as f:
        reader = csv.reader(f)
        # Skip the header
        next(reader)
        for row in reader:
            if row[1] != "":
                name_table[row[0]] = row[1]
    return name_table


def dump_name_table_from_chunks(
    chunks: List[SplitChunkMetadata], proj_config: CProjectConfig
):
    name_dict = {}
    proj_dir = proj_config.getProjectDir()

    for chunk in chunks:
        for tran in chunk.trans_list:
            if tran.speaker and isinstance(tran.speaker, str):
                if tran.speaker not in name_dict:
                    name_dict[tran.speaker] = 0
                name_dict[tran.speaker] += 1

    name_dict = dict(sorted(name_dict.items(), key=lambda item: item[1], reverse=True))

    LOGGER.info(f"共发现 {len(name_dict)} 个人名，按出现次数排序如下：")
    for name, count in name_dict.items():
        LOGGER.info(f"{name}: {count}")
    with open(
        joinpath(proj_dir, "人名替换表.csv"), "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["JP_Name", "CN_Name", "Count"])  # 写入表头
        for name, count in name_dict.items():
            writer.writerow([name, "", count])
    LOGGER.info(
        f"name已保存到'人名替换表.csv'（UTF-8编码，用Emeditor编辑），填入CN_Name后可用于后续翻译name字段。"
    )
