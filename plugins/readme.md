# 插件规范

## 插件介绍

插件系统是GalTransl v4在基础功能上又一的微小升级。插件可以分为两种类型：文本插件和文件插件。
- 文本插件可以对文本进行自定义的处理，例如清洁文本、修复文本、修复人名位置等。
- 文件插件可以使GalTransl支持更多格式的文件，例如字幕文件、文本文件等。

如果你愿意贡献插件，或者只是希望编写自己的插件，那么请继续阅读本文档。

## 1. 插件命名规则

插件的命名应该清晰明了，能够准确地反映出插件的功能。命名应遵循以下规则：

- 统一格式为文本插件：`Text_(引擎名/文件类型名)_(用途)`，文件插件`File_(引擎名/文件类型名)_(后缀/noext)`
- 插件的文件名应以`Text`或`File`开头。
- 后接引擎名/文件类型名，例如`krkr（引擎名）`，`subtitle（字幕类文件）`等。通用文本插件可使用`common`。
- 最后是用途或后缀例如文本插件：`clean（清洁文本）`、`Fix（修复文本）`，文件插件：`ast`、`srt`
- 最终名称的样例：`Text_krkr_rubyClean`、`Text_common_linebreakFix`、`File_subtitle_srt`

## 2. 插件目录结构


## 2. 插件编写指引

插件应继承自`IPlugin`接口，并实现以下方法：

- `gtp_init(self, settings: SectionProxy)`: 在插件加载时被调用。如果配置文件中有Settings，则会传入用于初始化插件设置。
- `gtp_final(self)`: 在所有文件翻译完成之后的动作，例如输出提示信息。

对于处理文本的插件，还需要实现以下方法：

- `before_src_processed(self, tran: CSentense) -> CSentense`: 在源句子处理之前被调用。返回修改后的`CSentense`。
- `after_src_processed(self, tran: CSentense) -> CSentense`: 在源句子处理之后被调用。返回修改后的`CSentense`。
- `before_dst_processed(self, tran: CSentense) -> CSentense`: 在目标句子处理之前被调用。返回修改后的`CSentense`。
- `after_dst_processed(self, tran: CSentense) -> CSentense`: 在目标句子处理之后被调用。返回修改后的`CSentense`。

## 3. 注意事项

- 所有的插件方法都应该有适当的错误处理，以防止插件在运行时出现错误导致整个程序崩溃。
- 插件应避免使用全局变量，以防止插件之间的相互影响。
- 插件应尽可能地减少对外部资源的依赖，以提高插件的可移植性。

以上就是插件的基本规范，希望对你有所帮助。