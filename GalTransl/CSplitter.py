from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
import json
from GalTransl import LOGGER


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

    chunk_index: int
    start_index: int
    end_index: int
    chunk_non_cross_size: int
    chunk_real_size: int
    cross_num: int
    content: Any
    file_name: str = ""


class InputSplitter:
    """
    输入分割器的基类，定义了分割方法的接口。
    """

    @staticmethod
    def split(
        content: Union[str, List], cross_num: int, file_name: str = ""
    ) -> List[SplitChunkMetadata]:
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

    def split(
        self, content: Union[str, List], cross_num: int, file_name: str = ""
    ) -> List[SplitChunkMetadata]:
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
                return [
                    SplitChunkMetadata(
                        chunk_index=0,
                        start_index=0,
                        end_index=len(content),
                        chunk_non_cross_size=len(content),
                        chunk_real_size=len(content),
                        cross_num=0,
                        content=content,
                    )
                ]
        else:
            data = content

        if not isinstance(data, list):
            return [
                SplitChunkMetadata(
                    chunk_index=0,
                    start_index=0,
                    end_index=1,
                    chunk_non_cross_size=1,
                    chunk_real_size=1,
                    cross_num=0,
                    content=json.dumps(data, ensure_ascii=False, indent=2),
                )
            ]

        total_items = len(data)
        result = []

        for start in range(0, total_items, self.dict_count):
            end = min(start + self.dict_count, total_items)
            chunk_start = max(0, start - cross_num)
            chunk_end = min(total_items, end + cross_num)
            chunk = data[chunk_start:chunk_end]

            result.append(
                SplitChunkMetadata(
                    chunk_index=len(result),
                    start_index=start,
                    end_index=end,
                    chunk_non_cross_size=end - start,
                    chunk_real_size=len(chunk),
                    cross_num=cross_num,
                    content=json.dumps(chunk, ensure_ascii=False, indent=2),
                    file_name=file_name,
                )
            )

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

    def split(
        self, content: Union[str, List], cross_num: int, file_name: str = ""
    ) -> List[SplitChunkMetadata]:
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
                return [SplitChunkMetadata(0, 0, 1, 1, 1, 0, content)]
        else:
            data = content

        if not isinstance(data, list):
            return [
                SplitChunkMetadata(
                    0, 0, 1, 1, 1, 0, json.dumps(data, ensure_ascii=False, indent=2)
                )
            ]

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
            result.append(
                SplitChunkMetadata(
                    chunk_index=len(result),
                    start_index=start,
                    end_index=end,
                    chunk_non_cross_size=end - start,
                    chunk_real_size=len(chunk),
                    cross_num=cross_num,
                    content=json.dumps(chunk, ensure_ascii=False, indent=2),
                    file_name=file_name,
                )
            )
            start = end

        return result


class OutputCombiner:
    """
    输出合并器的基类，定义了合并方法的接口。
    """

    @staticmethod
    def combine(
        results: List[Tuple[List, List, SplitChunkMetadata]]
    ) -> Tuple[List, List]:
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
    def combine(
        results: List[Tuple[List, List, SplitChunkMetadata]]
    ) -> Tuple[List, List]:
        """
        实现合并方法，合并分割后的翻译结果。

        参数:
        results: 包含翻译结果、JSON列表和元数据的元组列表

        返回:
        合并后的翻译列表和JSON列表的元组
        """
        if len(results) == 1:
            # 如果只有一个结果，直接返回
            return results[0][0], results[0][1]

        all_trans_list = []
        all_json_list = []
        sorted_results = sorted(results, key=lambda x: x[2].start_index)

        for i, (trans_list, json_list, metadata) in enumerate(sorted_results):
            if i == 0:
                # 对于第一个块，我们取全部内容
                all_trans_list.extend(trans_list[: metadata.chunk_non_cross_size])
                all_json_list.extend(json_list[: metadata.chunk_non_cross_size])
            else:
                # 对于后续块，我们只取非交叉部分
                start = metadata.cross_num
                end = start + metadata.chunk_non_cross_size
                all_trans_list.extend(trans_list[start:end])
                all_json_list.extend(json_list[start:end])

        return all_trans_list, all_json_list
