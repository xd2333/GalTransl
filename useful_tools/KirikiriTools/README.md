# KirikiriTools

用于Kirikiri视觉小说引擎的工具。

下载页面

如果你想翻译一个Kirikiri游戏，可以看看VNTextPatch。

## KirikiriDescrambler

有些Kirikiri游戏的明文脚本（.ks/.tjs）被打乱或压缩了。这样的文件可以通过以下签名来识别：

FE FE 00 FF FE FE FE 01 FF FE FE FE 02 FF FE

KirikiriDescrambler可以把这些文件转换成普通的文本文件，可以直接放回游戏中 - 不需要重新打乱。

## KirikiriUnencryptedArchive

一个DLL（命名为“version.dll”），使游戏接受未加密的.xp3归档文件。使用这个文件，就不再需要在尝试添加/替换.xp3文件时，识别和复制游戏的加密；只需用本仓库中的Xp3Pack工具创建一个未加密的文件，把version.dll放到游戏文件夹中，就可以了。

DLL会产生调试信息，可以用Microsoft的DebugView工具查看 - 这可以方便地确认它是否工作。一些特殊功能可以帮助处理包含加密/哈希文件名的.xp3归档文件，这些文件不受其他工具支持。具体来说，如果DebugView在游戏启动时显示了类似“Hooking storage media 'arc'”的信息（这不适用于媒体“psb”），那么这些功能就可用。

如果游戏文件夹中有一个名为extract-unencrypted.txt的文件，DLL会把游戏访问的任何文件提取到一个名为“unencrypted”的子文件夹中，并使用它们原来的名字。注意，只有当游戏读取它们时，文件才会被提取，所以如果你想提取所有内容，你必须跳过整个游戏。如果你可以用其他工具提取归档文件，请使用那个。

如果“unencrypted”文件夹中存在一个文件，游戏会使用它而不是加密.xp3归档文件中的原始文件。

如果存在一个名为“unencrypted.xp3”的归档文件，游戏会使用它而不是加密.xp3归档文件中的原始文件。

## Xp3Pack

创建未加密的.xp3归档文件，供KirikiriUnencryptedArchive DLL使用。与其他打包工具不同，它将文件表中的所有哈希设置为零；这作为一个标记，让DLL绕过那些文件的游戏解密。

典型的用法是将Xp3Pack.exe放在游戏文件夹中，创建一个包含你想要包含的文件的“patch”子文件夹，并从命令行运行“Xp3Pack patch”。这将在游戏文件夹中创建一个patch.xp3。如果游戏已经有自己的patch.xp3，请将你的文件夹命名为“patch2”，并运行“Xp3Pack patch2”。
