作者AtomCrafty，原项目地址：https://github.com/AtomCrafty/UniversalInjectorFramework   
newbing翻译   

## 用户手册

本文档介绍了“通用注入框架”（UIF）的功能和配置选项。UIF是一个可扩展的库，可以用来修改现有Windows应用程序的行为。

UIF内置了一些功能，主要用于日本游戏的本地化。所有功能的启用和控制都可以通过与代理dll同一目录下的config.json文件来实现。有些功能是互斥的，因为同一个游戏函数只能被一个功能修改一次。

配置文件是一个JSON文件，人和机器都可以轻松读取。所有配置选项必须包含在一个根对象中，用一对花括号表示。

以下各节将解释所有默认功能及其配置选项。

## 注射器

这不是一个功能，而是注射器本身（负责管理其他功能的组件）的通用配置。这些是可用的选项：

如果 /injector/enable 设置为 false，注射器将只加载原始 dll 并立即终止。如果该字段不存在或包含任何其他值，注入过程将照常继续。

target_module 选项允许您指定哪个模块的入口点应该被劫持来执行注射器的初始化。在大多数情况下，这将是应用程序可执行文件，因此省略该选项将默认为该选项。这主要在注射器不是 .exe 的直接依赖项，而是在运行时加载时有用 - 无论是通过显式 LoadLibrary 调用还是通过延迟加载。

print_loade_modules 选项 - 如果设置为 true - 将在注入器初始化之前打印所有已加载模块的列表。这纯粹是用于调试目的。

hook_modules 是一个名称数组，指的是目标可执行文件加载的模块。当一个功能试图挂钩一个导入时，导入的函数将在主可执行文件以及此处列出的所有模块中被挂钩。确保此列表不包含您的代理 dll 的名称，因为这会影响注入器本身的导入。

load_modules 是一个字符串数组，其中每个字符串包含一个应该在启动时加载的 dll 文件的路径。您可能想要通过 hook_modules 在目标可执行文件的依赖项中挂钩函数。如果在加载所述依赖项之前运行功能初始化，则会失败，因此将其添加到此列表中以强制在初始化之前加载它。
```json
{
  "injector": {
    "enable": true,
    "target_module": "Engine.dll",
    "print_loaded_modules": false,
    "load_modules": [
      "plugin/EngineHelpers.dll"
    ],
    "hook_modules": [
      "EngineHelpers.dll"
    ]
  }
}
```
## 分配控制台

这个功能非常简单，只有一个配置选项。它打开一个控制台窗口来显示相关信息。建议在测试期间启用此功能，但在分发代理时禁用它。

当通过命令行启动程序时，该功能将首先尝试附加到现有的控制台。

要启用控制台分配，请将 /allocate_console 选项设置为 true：
```json
{
  "allocate_console": true
}
```

## 字符替换

这个功能可以将某些字符替换为其他字符。它可以用来打印应用程序由于字符集而不支持的字符。许多日本游戏引擎使用 Shift-JIS 字符集，它不支持英语中使用的一些字符。字符替换功能可以用来将你不需要的支持的字符替换为你需要的字符。

要启用这个功能，将选项 `/character_substitution/enable` 设置为 true。你还需要设置 `source_characters` 和 `target_characters` 选项，告诉该功能哪些字符应该映射到哪些字符。下面的配置文件将把所有 `ｱ` 替换为 `á`，把所有 `ｲ` 替换为 `í`，依此类推。

```json
{
  "character_substitution": {
    "enable": true,
    "source_characters": "ｱｲｳｴｵ",
    "target_characters": "áíúéó"
  }
}
```

## 隧道解码器

隧道解码器是一个更强大，但更复杂的替代字符替换功能的方案。它实现了由 [arcusmaximus](https://github.com/arcusmaximus/VNTranslationTools) 开发的 Shift-JIS 隧道编码，它将多达 3422 个字符映射到未分配的 Shift-JIS 代码点。要启用这个功能，将选项 `/tunnel_decoder/enable` 设置为 true。除此之外，只有一个选项：`mapping`。这应该与相应的 [隧道编码器](https://github.com/AtomCrafty/yukatool2/blob/master/src/Yuka.Core/Util/EncodingUtils.cs#L55) 返回的值相同。

```json
{
  "tunnel_decoder": {
    "enable": true,
    "mapping": "éáäöüß"
  }
}
```

## LocaleEmulator

这个功能允许你在应用程序没有使用正确的 ansi 代码页启动时自动重新启动应用程序。要启用它，将选项 `/locale_emulator/enable` 设置为 true。要使用这个功能，你还需要从 [Locale Emulator](https://pooi.moe/Locale-Emulator/) 项目下载 `LoaderDll.dll` 和 `LocaleEmulator.dll` 并将它们放在应用程序可执行文件旁边。

有几个选项可以指定所需的区域设置环境。

- `codepage` 指定应用程序期望运行的代码页。默认值是 `932`，它指定了日语的 `Shift-JIS` 代码页。如果应用程序没有使用这个代码页启动，它将尝试通过 Locale Emulator 重新启动自己。
- `locale` 指定所需的 [LCID](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oe376/6c085406-a698-4e12-9d4d-c3b0ee3dbc4a)，默认值是 `1041`（日语）。
- `charset` 指定默认字符集。其默认值为 `128`，即 `SHIFTJIS_CHARSET` 常量的值。
- `timezone` 允许你指定要模拟的时区。默认值是 `Tokyo Standard Time`。可用的时区名称可以在 `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones` 下找到。

最后，`wait_for_exit` 选项控制父进程何时终止。如果设置为 true，它将等待子进程结束，否则它将立即退出。

```json
{
  "locale_emulator": {
    "enable": true,
    "codepage": 932,
    "locale": 1041,
    "charset": 128,
    "timezone": "Tokyo Standard Time",
    "wait_for_exit": false
  }
}
```
