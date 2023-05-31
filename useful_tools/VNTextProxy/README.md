# VNTextProxy

作者arcusmaximus，原项目地址：https://github.com/arcusmaximus/VNTranslationTools#vntextproxy   
NewBing翻译   

一个代理d2d1.dll，它钩入游戏并帮助它显示非日语文本。它可以做以下事情：

- 在SJIS-only游戏中渲染非SJIS字符（参见上一节）。
- 从游戏文件夹加载自定义字体（.ttf/.ttc/.otf）并强制游戏使用它。字体文件名应与字体名匹配。
- 为了正确显示比例字体的文本，重新定位渲染的字符（因为许多视觉小说引擎只能做等宽）。这目前适用于TextOutA()和ID2D1RenderTarget::DrawText()。
- 在一定程度上，使SJIS-only游戏兼容Unicode。这不仅可以让它们在非日语系统上运行而不崩溃，而且可以让它们处理非SJIS文件路径和接受非SJIS键盘输入（包括来自IME的输入）。
- 如果以上方法不足以防止崩溃，VNTextProxy还可以在非日语系统上使用Locale Emulator自动重新启动游戏。用户不需要安装模拟器；相反，你应该将LoaderDll.dll和LocaleEmulator.dll与游戏一起打包。

如果游戏没有引用d2d1.dll，你可以使用“AlternateProxies”子文件夹中的文件将DLL变成一个代理，比如说，version.dll。如果游戏没有引用任何提供的代理，你可以使用DLLProxyGenerator来制作自己的。

除此之外，你可能需要对源代码进行一些更改。

- 在dllmain.cpp中，你可以取消注释Locale Emulator重新启动器，并根据需要启用/禁用GDI和Direct2D支持。
- 在EnginePatches.cpp中，你可以添加任何你可能需要的特定于游戏的钩子。微软的Detours库已经包含在内。
