# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""BudouX parser to provide semantic chunks."""

import json
import os
import typing

from .html_processor import get_text, resolve

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')


class Parser:
  """BudouX's Parser.

  The main parser object with a variety of class methods to provide semantic
  chunks and markups from the given input string.

  Attributes:
    model: A dict mapping a feature (str) and its score (int).
  """

  def __init__(self, model: typing.Dict[str, typing.Dict[str, int]]):
    """Initializes the parser.

    Args:
      model (Dict[str, Dict[str, int]]): A dict mapping a feature and its score.
    """
    self.model = model

  def parse(self, sentence: str) -> typing.List[str]:
    """Parses the input sentence and returns a list of semantic chunks.

    Args:
      sentence (str): An input sentence.

    Returns:
      A list of semantic chunks (List[str]).
    """
    if sentence == '':
      return []
    chunks = [sentence[0]]
    base_score = -sum(sum(g.values()) for g in self.model.values()) * 0.5
    for i in range(1, len(sentence)):
      score = base_score
      if i > 2:
        score += self.model.get('UW1', {}).get(sentence[i - 3], 0)
      if i > 1:
        score += self.model.get('UW2', {}).get(sentence[i - 2], 0)
      score += self.model.get('UW3', {}).get(sentence[i - 1], 0)
      score += self.model.get('UW4', {}).get(sentence[i], 0)
      if i + 1 < len(sentence):
        score += self.model.get('UW5', {}).get(sentence[i + 1], 0)
      if i + 2 < len(sentence):
        score += self.model.get('UW6', {}).get(sentence[i + 2], 0)

      if i > 1:
        score += self.model.get('BW1', {}).get(sentence[i - 2:i], 0)
      score += self.model.get('BW2', {}).get(sentence[i - 1:i + 1], 0)
      if i + 1 < len(sentence):
        score += self.model.get('BW3', {}).get(sentence[i:i + 2], 0)

      if i > 2:
        score += self.model.get('TW1', {}).get(sentence[i - 3:i], 0)
      if i > 1:
        score += self.model.get('TW2', {}).get(sentence[i - 2:i + 1], 0)
      if i + 1 < len(sentence):
        score += self.model.get('TW3', {}).get(sentence[i - 1:i + 2], 0)
      if i + 2 < len(sentence):
        score += self.model.get('TW4', {}).get(sentence[i:i + 3], 0)

      if score > 0:
        chunks.append(sentence[i])
      else:
        chunks[-1] += sentence[i]
    return chunks

  def translate_html_string(self, html: str) -> str:
    """Translates the given HTML string with markups for semantic line breaks.

    Args:
      html (str): An input html string.

    Returns:
      The translated HTML string (str).
    """
    # TODO: Align with the JavaScript API regarding the parent element addition.
    text_content = get_text(html)
    chunks = self.parse(text_content)
    return resolve(chunks, html)


def load_default_japanese_parser() -> Parser:
  """Loads a parser equipped with the default Japanese model.

  Returns:
    A parser (:obj:`budoux.Parser`).
  """
  with open(os.path.join(MODEL_DIR, 'ja.json'), encoding='utf-8') as f:
    model = json.load(f)
  return Parser(model)


def load_default_simplified_chinese_parser() -> Parser:
  """Loads a parser equipped with the default Simplified Chinese model.

  Returns:
    A parser (:obj:`budoux.Parser`).
  """
  with open(os.path.join(MODEL_DIR, 'zh-hans.json'), encoding='utf-8') as f:
    model = json.load(f)
  return Parser(model)


def load_default_traditional_chinese_parser() -> Parser:
  """Loads a parser equipped with the default Traditional Chinese model.

  Returns:
    A parser (:obj:`budoux.Parser`).
  """
  with open(os.path.join(MODEL_DIR, 'zh-hant.json'), encoding='utf-8') as f:
    model = json.load(f)
  return Parser(model)


def load_default_thai_parser() -> Parser:
  """Loads a parser equipped with the default Thai model.

  Returns:
    A parser (:obj:`budoux.Parser`).
  """
  with open(os.path.join(MODEL_DIR, 'th.json'), encoding='utf-8') as f:
    model = json.load(f)
  return Parser(model)
