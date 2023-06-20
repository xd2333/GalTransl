import configparser
import json
import random
import re
import shutil
import struct
import subprocess
import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from ttkbootstrap import Style

VERSION="1.1"
message_dict = {}
name_dict = {}


class VNTextPatchGUI:
    def __init__(self, master):
        self.master = master
        master.title(f"GalTransl 提取注入工具v{VERSION} by cx2333")
        master.config(padx=20, pady=20)

        # Create Notebook widget
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill="both", expand=True)

        # Create first tab
        self.tab1 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text="VNTextPatch模式")

        # 日文脚本文件夹
        self.script_jp_folder_label = tk.Label(self.tab1, text="日文脚本文件夹")
        self.script_jp_folder_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.script_jp_folder_textbox = tk.Entry(self.tab1, width=50)
        self.script_jp_folder_textbox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.script_jp_folder_browse_button = tk.Button(
            self.tab1, text="浏览", command=self.browse_script_jp_folder
        )
        self.script_jp_folder_browse_button.grid(row=0, column=2, padx=5, pady=5)

        # 日文JSON保存文件夹
        self.json_jp_folder_label = tk.Label(self.tab1, text="日文JSON保存文件夹")
        self.json_jp_folder_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.json_jp_folder_textbox = tk.Entry(self.tab1, width=50)
        self.json_jp_folder_textbox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.json_jp_folder_browse_button = tk.Button(
            self.tab1, text="浏览", command=self.browse_json_jp_folder
        )
        self.json_jp_folder_browse_button.grid(row=1, column=2, padx=5, pady=5)

        # 提取脚本到JSON
        self.extract_button = tk.Button(
            self.tab1, text="提取脚本到JSON", command=self.extract
        )
        self.extract_button.grid(row=2, column=1, padx=5, pady=5, sticky="e")

        # 引擎选择下拉列表框
        self.engine_label = tk.Label(self.tab1, text="指定引擎")
        self.engine_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.engine_var = tk.StringVar(value="自动判断")
        self.engine_optionmenu = tk.OptionMenu(
            self.tab1,
            self.engine_var,
            "自动判断",
            "artemistxt",
            "ethornell",
            "kirikiriks",
            "reallive",
            "tmrhiroadvsystemtext",
            "whale",
        )
        self.engine_optionmenu.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        # 译文JSON文件夹
        self.json_cn_folder_label = tk.Label(self.tab1, text="译文JSON文件夹")
        self.json_cn_folder_label.grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.json_cn_folder_textbox = tk.Entry(self.tab1, width=50)
        self.json_cn_folder_textbox.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.json_cn_folder_browse_button = tk.Button(
            self.tab1, text="浏览", command=self.browse_json_cn_folder
        )
        self.json_cn_folder_browse_button.grid(row=3, column=2, padx=5, pady=5)

        # 译文脚本保存文件夹
        self.script_cn_folder_label = tk.Label(self.tab1, text="译文脚本保存文件夹")
        self.script_cn_folder_label.grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.script_cn_folder_textbox = tk.Entry(self.tab1, width=50)
        self.script_cn_folder_textbox.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        self.script_cn_folder_browse_button = tk.Button(
            self.tab1, text="浏览", command=self.browse_script_cn_folder
        )
        self.script_cn_folder_browse_button.grid(row=4, column=2, padx=5, pady=5)

        # 注入JSON回脚本
        self.insert_button = tk.Button(self.tab1, text="注入JSON回脚本", command=self.insert)
        self.insert_button.grid(row=5, column=1, padx=5, pady=5, sticky="e")

        # Add a Checkbutton for GBK encoding injection
        self.gbk_encoding_var = tk.BooleanVar(value=False)
        self.gbk_encoding_checkbox = tk.Checkbutton(
            self.tab1,
            text="GBK编码注入",
            variable=self.gbk_encoding_var,
            onvalue=True,
            offvalue=False,
        )
        self.gbk_encoding_checkbox.grid(row=5, column=0, padx=5, pady=5, sticky="w")

        # Add a Checkbutton for SJIS replacement mode injection
        self.sjis_replace_mode_var = tk.BooleanVar(value=False)
        self.sjis_replace_mode_checkbox = tk.Checkbutton(
            self.tab1,
            text="SJIS替换模式注入",
            variable=self.sjis_replace_mode_var,
            onvalue=True,
            offvalue=False,
        )
        self.sjis_replace_mode_checkbox.grid(
            row=6, column=0, padx=5, pady=5, sticky="w"
        )

        # Add a TextBox for the character to be replaced in SJIS replacement mode
        self.sjis_replace_char_textbox = tk.Entry(self.tab1, width=10)
        self.sjis_replace_char_textbox.grid(
            row=6, column=1, padx=5, pady=5, sticky="ew"
        )
        # Add a Label for the character to be replaced in SJIS replacement mode
        self.sjis_replace_char_label = tk.Label(self.tab1, text="👆要替换的字符(空为全量替换)")
        self.sjis_replace_char_label.grid(row=7, column=1, padx=5, pady=5, sticky="w")
        # 显示cmd输出结果
        self.sjis_replace_char_label = tk.Label(self.tab1, text="输出结果")
        self.sjis_replace_char_label.grid(row=8, column=0, padx=5, pady=5, sticky="w")

        self.output_textbox = ScrolledText(self.tab1, wrap=tk.WORD, height=14, width=50)
        self.output_textbox.grid(
            row=9, column=0, columnspan=3, padx=5, pady=5, sticky="ew"
        )
        # ================================================================
        # Create tab2
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text="正则表达式模式")

        # Copy controls from tab1
        self.script_jp_folder_label2 = tk.Label(self.tab2, text="日文脚本文件夹")
        self.script_jp_folder_label2.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.script_jp_folder_textbox2 = tk.Entry(self.tab2, width=50)
        self.script_jp_folder_textbox2.grid(
            row=0, column=1, padx=5, pady=5, sticky="ew"
        )
        self.script_jp_folder_browse_button2 = tk.Button(
            self.tab2, text="浏览", command=self.browse_script_jp_folder
        )
        self.script_jp_folder_browse_button2.grid(row=0, column=2, padx=5, pady=5)

        self.json_jp_folder_label2 = tk.Label(self.tab2, text="日文JSON保存文件夹")
        self.json_jp_folder_label2.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.json_jp_folder_textbox2 = tk.Entry(self.tab2, width=50)
        self.json_jp_folder_textbox2.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.json_jp_folder_browse_button2 = tk.Button(
            self.tab2, text="浏览", command=self.browse_json_jp_folder
        )
        self.json_jp_folder_browse_button2.grid(row=1, column=2, padx=5, pady=5)

        self.regex_label = tk.Label(self.tab2, text="正文提取正则")
        self.regex_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.regex_textbox = tk.Entry(self.tab2, width=50)
        self.regex_textbox.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.name_regex_label = tk.Label(self.tab2, text="人名提取正则")
        self.name_regex_label.grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.name_regex_textbox = tk.Entry(self.tab2, width=50)
        self.name_regex_textbox.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        self.japanese_encoding_label = tk.Label(self.tab2, text="日文脚本编码")
        self.japanese_encoding_label.grid(row=4, column=0, padx=5, pady=5, sticky="e")

        self.japanese_encoding_var = tk.StringVar(self.tab2)
        self.japanese_encoding_var.set("sjis")
        self.japanese_encoding_optionmenu = tk.OptionMenu(
            self.tab2, self.japanese_encoding_var, "sjis", "utf8", "gbk"
        )
        self.japanese_encoding_optionmenu.grid(
            row=4, column=1, padx=5, pady=5, sticky="w"
        )

        self.extract_button2 = tk.Button(
            self.tab2, text="提取脚本到JSON", command=self.extract_re
        )
        self.extract_button2.grid(row=4, column=1, padx=5, pady=5, sticky="e")

        self.json_cn_folder_label2 = tk.Label(self.tab2, text="译文JSON文件夹")
        self.json_cn_folder_label2.grid(row=5, column=0, padx=5, pady=5, sticky="e")
        self.json_cn_folder_textbox2 = tk.Entry(self.tab2, width=50)
        self.json_cn_folder_textbox2.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        self.json_cn_folder_browse_button2 = tk.Button(
            self.tab2, text="浏览", command=self.browse_json_cn_folder
        )
        self.json_cn_folder_browse_button2.grid(row=5, column=2, padx=5, pady=5)

        self.script_cn_folder_label2 = tk.Label(self.tab2, text="译文脚本保存文件夹")
        self.script_cn_folder_label2.grid(row=6, column=0, padx=5, pady=5, sticky="e")
        self.script_cn_folder_textbox2 = tk.Entry(self.tab2, width=50)
        self.script_cn_folder_textbox2.grid(
            row=6, column=1, padx=5, pady=5, sticky="ew"
        )
        self.script_cn_folder_browse_button2 = tk.Button(
            self.tab2, text="浏览", command=self.browse_script_cn_folder
        )
        self.script_cn_folder_browse_button2.grid(row=6, column=2, padx=5, pady=5)

        self.chinese_encoding_label = tk.Label(self.tab2, text="中文脚本编码")
        self.chinese_encoding_label.grid(row=7, column=0, padx=5, pady=5, sticky="e")

        self.chinese_encoding_var = tk.StringVar(self.tab2)
        self.chinese_encoding_var.set("gbk")
        self.chinese_encoding_optionmenu = tk.OptionMenu(
            self.tab2, self.chinese_encoding_var, "sjis", "utf8", "gbk"
        )
        self.chinese_encoding_optionmenu.grid(
            row=7, column=1, padx=5, pady=5, sticky="w"
        )

        self.insert_button2 = tk.Button(
            self.tab2, text="注入JSON回脚本", command=self.insert_re
        )
        self.insert_button2.grid(row=7, column=1, padx=5, pady=5, sticky="e")

        # Add a Checkbutton for SJIS replacement mode injection
        self.sjis_replace_mode_var2 = tk.BooleanVar(value=False)
        self.sjis_replace_mode_checkbox2 = tk.Checkbutton(
            self.tab2,
            text="SJIS替换模式注入",
            variable=self.sjis_replace_mode_var2,
            onvalue=True,
            offvalue=False,
        )
        self.sjis_replace_mode_checkbox2.grid(
            row=8, column=0, padx=5, pady=5, sticky="w"
        )

        # Add a Label for the character to be replaced in SJIS replacement mode
        self.sjis_replace_char_label2 = tk.Label(self.tab2, text="👆要替换的字符(空为全量替换)")
        self.sjis_replace_char_label2.grid(row=9, column=1, padx=5, pady=5, sticky="w")

        # Add a TextBox for the character to be replaced in SJIS replacement mode
        self.sjis_replace_char_textbox2 = tk.Entry(self.tab2, width=10)
        self.sjis_replace_char_textbox2.grid(
            row=8, column=1, padx=5, pady=5, sticky="ew"
        )
        # 输出结果
        self.sjis_replace_char_label2 = tk.Label(self.tab2, text="输出结果")
        self.sjis_replace_char_label2.grid(row=10, column=0, padx=5, pady=5, sticky="w")
        self.output_textbox2 = ScrolledText(
            self.tab2, wrap=tk.WORD, height=10, width=50
        )
        self.output_textbox2.grid(
            row=11, column=0, columnspan=3, padx=5, pady=5, sticky="ew"
        )

        width = 584
        height = 659
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        self.master.geometry(
            "%dx%d+%d+%d"
            % (width, height, (screen_width - width) / 2, (screen_height - height) / 2)
        )

    def browse_script_jp_folder(self):
        folder_path = filedialog.askdirectory()
        self.script_jp_folder_textbox.delete(0, tk.END)
        self.script_jp_folder_textbox.insert(0, folder_path)
        self.script_jp_folder_textbox2.delete(0, tk.END)
        self.script_jp_folder_textbox2.insert(0, folder_path)

    def browse_json_jp_folder(self):
        folder_path = filedialog.askdirectory()
        self.json_jp_folder_textbox.delete(0, tk.END)
        self.json_jp_folder_textbox.insert(0, folder_path)
        self.json_jp_folder_textbox2.delete(0, tk.END)
        self.json_jp_folder_textbox2.insert(0, folder_path)

    def browse_json_cn_folder(self):
        folder_path = filedialog.askdirectory()
        self.json_cn_folder_textbox.delete(0, tk.END)
        self.json_cn_folder_textbox.insert(0, folder_path)
        self.json_cn_folder_textbox2.delete(0, tk.END)
        self.json_cn_folder_textbox2.insert(0, folder_path)

    def browse_script_cn_folder(self):
        folder_path = filedialog.askdirectory()
        self.script_cn_folder_textbox.delete(0, tk.END)
        self.script_cn_folder_textbox.insert(0, folder_path)
        self.script_cn_folder_textbox2.delete(0, tk.END)
        self.script_cn_folder_textbox2.insert(0, folder_path)

    def extract(self):
        script_jp_folder = self.script_jp_folder_textbox.get()
        json_jp_folder = self.json_jp_folder_textbox.get()
        if not script_jp_folder:
            messagebox.showerror("Error", "请选择日文脚本目录.")
            return False
        if not json_jp_folder:
            messagebox.showerror("Error", "请选择日文json保存目录.")
            return False
        self.output_textbox.delete(1.0, tk.END)
        engine = self.engine_var.get()
        if " " in script_jp_folder:
            script_jp_folder = f'"{script_jp_folder}"'
        if " " in json_jp_folder:
            json_jp_folder = f'"{json_jp_folder}"'
        if engine != "自动判断":
            cmd = f".\\VNTextPatch\\VNTextPatch.exe extractlocal {script_jp_folder} {json_jp_folder} --format={engine}"
        else:
            cmd = f".\\VNTextPatch\\VNTextPatch.exe extractlocal {script_jp_folder} {json_jp_folder}"
        self.execute_command(cmd)

    def insert(self):
        script_jp_folder = self.script_jp_folder_textbox.get()
        json_cn_folder = self.json_cn_folder_textbox.get()
        script_cn_folder = self.script_cn_folder_textbox.get()
        if not script_jp_folder:
            messagebox.showerror("Error", "请选择日文脚本目录.")
            return False
        if not json_cn_folder:
            messagebox.showerror("Error", "请选择译文json目录.")
            return False
        if not script_cn_folder:
            messagebox.showerror("Error", "请选择译文脚本保存目录.")
            return False

        self.output_textbox.delete(1.0, tk.END)
        sjis_ext_path = os.path.join(script_cn_folder, "sjis_ext.bin")
        if os.path.exists(sjis_ext_path):
            os.remove(sjis_ext_path)

        hanzi_chars_list = []
        kanji_chars_list = []
        if self.sjis_replace_mode_var.get():
            json_cn_folder, hanzi_chars_list, kanji_chars_list = sjis_replace(
                json_cn_folder, self.sjis_replace_char_textbox.get()
            )

        cmd = ""
        if not self.gbk_encoding_var.get():
            cmd = ".\\VNTextPatch\\VNTextPatch.exe "
        else:
            cmd = ".\\VNTextPatch\\VNTextPatchGBK.exe "

        if " " in script_jp_folder:
            script_jp_folder = f'"{script_jp_folder}"'
        if " " in json_cn_folder:
            json_cn_folder = f'"{json_cn_folder}"'
        if " " in script_cn_folder:
            script_cn_folder = f'"{script_cn_folder}"'
        engine = self.engine_var.get()
        if engine != "自动判断":
            cmd = (
                cmd
                + f"insertlocal {script_jp_folder} {json_cn_folder} {script_cn_folder} --format={engine}"
            )
        else:
            cmd = (
                cmd
                + f"insertlocal {script_jp_folder} {json_cn_folder} {script_cn_folder}"
            )
        self.execute_command(cmd)
        if os.path.exists(sjis_ext_path):
            sjis_ext_str = read_sjis_ext_bin(
                os.path.join(script_cn_folder, "sjis_ext.bin")
            )
            self.output_textbox.insert(tk.END, f"sjis_ext.bin包含文字：{sjis_ext_str}\n")
            self.output_textbox.see(tk.END)

        if self.sjis_replace_mode_var.get():
            self.output_textbox.insert(tk.END, "sjis替换模式配置:\n")
            self.output_textbox.insert(
                tk.END, f'"source_characters":"{"".join(kanji_chars_list)}",\n'
            )
            self.output_textbox.insert(
                tk.END, f'"target_characters":"{"".join(hanzi_chars_list)}"'
            )
            self.output_textbox.see(tk.END)

    def execute_command(self, cmd):
        self.output_textbox.delete(1.0, tk.END)
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        while True:
            output = process.stdout.readline()
            if output == b"" and process.poll() is not None:
                break
            if output:
                self.output_textbox.insert(tk.END, output.decode("gbk"))
                self.output_textbox.see(tk.END)
                self.master.update_idletasks()
        error = process.stderr.read()
        if error:
            self.output_textbox.insert(tk.END, error.decode("gbk"))
            self.output_textbox.insert(tk.END, "执行失败\n")
            self.output_textbox.see(tk.END)
            self.master.update_idletasks()

        self.output_textbox.insert(tk.END, "执行完毕\n")

    def extract_re(self):
        script_jp_folder = self.script_jp_folder_textbox.get()
        json_jp_folder = self.json_jp_folder_textbox.get()
        if not script_jp_folder:
            messagebox.showerror("Error", "请选择日文脚本目录.")
            return False
        if not json_jp_folder:
            messagebox.showerror("Error", "请选择日文json保存目录.")
            return False

        self.output_textbox2.delete(1.0, tk.END)
        message_pattern = re.compile(self.regex_textbox.get())
        name_pattern = re.compile(self.name_regex_textbox.get())

        for filename in os.listdir(script_jp_folder):
            self.output_textbox2.insert(tk.END, f"{filename}\n")
            self.output_textbox2.see(tk.END)
            self.master.update_idletasks()
            message_list = []
            # Open the file and extract matches
            try:
                with open(
                    os.path.join(script_jp_folder, filename),
                    "r",
                    encoding=self.japanese_encoding_var.get(),
                ) as f:
                    text = f.read()
            except UnicodeDecodeError:
                messagebox.showerror("Error", "日文脚本编码解码错误")
                return False

            search_result = message_pattern.search(text)
            last_start = 0
            while search_result:
                try:
                    message = search_result.group(1)
                except IndexError:
                    messagebox.showerror("Error", "正则表达式未包含括号")
                    return False
                start = search_result.start(1)
                name = ""
                if self.name_regex_textbox.get():
                    name_search_result = name_pattern.search(text, last_start, start)
                    if name_search_result:
                        try:
                            name = name_search_result.group(1)
                        except IndexError:
                            messagebox.showerror("Error", "正则表达式未包含括号")
                            return False
                    else:
                        name = ""
                tmp_obj = {"name": name, "message": message}
                if name == "":
                    del tmp_obj["name"]
                message_list.append(tmp_obj)
                last_start = search_result.end(1)
                search_result = message_pattern.search(text, last_start)

            # Save matches as JSON file
            with open(
                os.path.join(json_jp_folder, os.path.splitext(filename)[0] + ".json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(message_list, f, ensure_ascii=False, indent=4)

    def insert_re(self):
        script_jp_folder = self.script_jp_folder_textbox.get()
        json_jp_folder = self.json_jp_folder_textbox.get()
        json_cn_folder = self.json_cn_folder_textbox.get()
        script_cn_folder = self.script_cn_folder_textbox.get()
        jp_encoding = str(self.japanese_encoding_var.get())
        cn_encoding = str(self.chinese_encoding_var.get())
        message_regex = self.regex_textbox.get()
        name_regex = self.name_regex_textbox.get()

        if not script_jp_folder:
            messagebox.showerror("Error", "请选择日文脚本目录.")
            return False
        if not json_cn_folder:
            messagebox.showerror("Error", "请选择译文json目录.")
            return False
        if not script_cn_folder:
            messagebox.showerror("Error", "请选择译文脚本保存目录.")
            return False
        if not json_jp_folder:
            messagebox.showerror("Error", "请选择日文json目录.")
            return False
        if not message_regex:
            messagebox.showerror("Error", "请输入正则.")
            return False

        self.output_textbox2.delete(1.0, tk.END)
        hanzi_chars_list = []
        kanji_chars_list = []
        if self.sjis_replace_mode_var2.get():
            json_cn_folder, hanzi_chars_list, kanji_chars_list = sjis_replace(
                json_cn_folder, self.sjis_replace_char_textbox2.get()
            )

        for filename in os.listdir(script_jp_folder):
            self.output_textbox2.insert(tk.END, f"{filename}\n")
            self.output_textbox2.see(tk.END)
            self.master.update_idletasks()
            script_path = os.path.join(script_jp_folder, filename)
            jp_json_path = os.path.join(
                json_jp_folder, os.path.splitext(filename)[0] + ".json"
            )
            cn_json_path = os.path.join(
                json_cn_folder, os.path.splitext(filename)[0] + ".json"
            )
            if not os.path.exists(jp_json_path) or not os.path.exists(cn_json_path):
                shutil.copy(script_path, script_cn_folder)
                continue
            with open(jp_json_path, "r", encoding="utf-8") as f:
                jp_data = json.load(f)
            with open(cn_json_path, "r", encoding="utf-8") as f:
                cn_data = json.load(f)

            global message_dict, name_dict
            for i in range(len(jp_data)):
                message_dict[jp_data[i]["message"]] = cn_data[i]["message"]
                if name_regex != "":
                    if "name" in jp_data[i] and "name" in cn_data[i]:
                        if jp_data[i]["name"] not in name_dict:
                            name_dict[jp_data[i]["name"]] = cn_data[i]["name"]

            with open(script_path, "r", encoding=jp_encoding, errors="ignore") as f:
                script_content = f.read()

            script_content = re.sub(message_regex, get_cn_message, script_content)
            if name_regex != "":
                script_content = re.sub(name_regex, get_cn_name, script_content)

            output_path = os.path.join(script_cn_folder, filename)
            with open(output_path, "w", encoding=cn_encoding, errors="ignore") as f:
                f.write(script_content)

        if self.sjis_replace_mode_var2.get():
            self.output_textbox2.insert(tk.END, "sjis替换模式配置:\n")
            self.output_textbox2.insert(
                tk.END, f'"source_characters":"{"".join(kanji_chars_list)}",\n'
            )
            self.output_textbox2.insert(
                tk.END, f'"target_characters":"{"".join(hanzi_chars_list)}"'
            )
            self.output_textbox2.see(tk.END)

    def save_config(self):
        # save config to config.ini
        config = configparser.ConfigParser()
        config["DEFAULT"] = {
            "script_jp_folder": self.script_jp_folder_textbox.get(),
            "json_jp_folder": self.json_jp_folder_textbox.get(),
            "json_cn_folder": self.json_cn_folder_textbox.get(),
            "script_cn_folder": self.script_cn_folder_textbox.get(),
            # add more config items here
            "regex": self.regex_textbox.get(),
            "name_regex": self.name_regex_textbox.get(),
            "japanese_encoding": self.japanese_encoding_var.get(),
            "chinese_encoding": self.chinese_encoding_var.get(),
        }
        # open config.ini file in write mode
        with open("config.ini", "w") as configfile:
            # write config to file
            config.write(configfile)
        self.master.destroy()

    def read_config(self):
        # read config from config.ini
        if not os.path.exists("config.ini"):
            return
        config = configparser.ConfigParser()
        config.read("config.ini")
        self.script_jp_folder_textbox.insert(0, config["DEFAULT"]["script_jp_folder"])
        self.json_jp_folder_textbox.insert(0, config["DEFAULT"]["json_jp_folder"])
        self.json_cn_folder_textbox.insert(0, config["DEFAULT"]["json_cn_folder"])
        self.script_cn_folder_textbox.insert(0, config["DEFAULT"]["script_cn_folder"])

        self.script_jp_folder_textbox2.insert(0, config["DEFAULT"]["script_jp_folder"])
        self.json_jp_folder_textbox2.insert(0, config["DEFAULT"]["json_jp_folder"])
        self.json_cn_folder_textbox2.insert(0, config["DEFAULT"]["json_cn_folder"])
        self.script_cn_folder_textbox2.insert(0, config["DEFAULT"]["script_cn_folder"])


def read_sjis_ext_bin(file_path):
    with open(file_path, "rb") as f:
        data = f.read()

    chars = []
    for i in range(0, len(data), 2):
        char = struct.unpack("<H", data[i : i + 2])[0]
        chars.append(chr(char))

    return "".join(chars)


def get_cn_message(matched):
    if matched.group(1) in message_dict:
        return matched.group().replace(matched.group(1),message_dict[matched.group(1)])
    else:
        return matched.group()


def get_cn_name(matched):
    if matched.group(1) in name_dict:
        return matched.group().replace(matched.group(1), name_dict[matched.group(1)])
    else:
        return matched.group()


def read_proxy_dict(filename, proxy_words=""):
    char_dict = {}
    with open(filename, "r", encoding="utf-8") as f:
        for line in f.readlines():
            orig_char, replace_char = line.strip().split("\t")
            if proxy_words != "":
                if orig_char in proxy_words:
                    char_dict[orig_char] = replace_char
            else:
                char_dict[orig_char] = replace_char

    return char_dict


def sjis_replace(json_cn_folder, replace_str):
    char_dict = read_proxy_dict("hanzi2kanji_table.txt", replace_str)
    hanzi_chars_list = []
    kanji_chars_list = []
    trans_json_replacead_folder = json_cn_folder + "_replaced"
    if not os.path.exists(trans_json_replacead_folder):
        os.mkdir(trans_json_replacead_folder)
    for file_name in os.listdir(json_cn_folder):
        file_path = os.path.join(json_cn_folder, file_name)
        replaced_file_path = os.path.join(trans_json_replacead_folder, file_name)
        with open(file_path, "r", encoding="utf-8") as f_in:
            input_str = f_in.read()

        output_str = ""
        for char in input_str:
            if char in char_dict:
                output_str += char_dict[char]
                if char not in hanzi_chars_list:
                    hanzi_chars_list.append(char)
                    kanji_chars_list.append(char_dict[char])
            else:
                output_str += char

        with open(replaced_file_path, "w", encoding="utf-8") as f_out:
            f_out.write(output_str)
    return trans_json_replacead_folder, hanzi_chars_list, kanji_chars_list


style = Style()
random_theme = random.choice(
    [
        "cosmo",
        "flatly",
        "litera",
        "minty",
        "lumen",
        "sandstone",
        "yeti",
        "pulse",
        "united",
        "journal",
    ]
)
style.theme_use(random_theme)
root = style.master

gui = VNTextPatchGUI(root)
root.protocol("WM_DELETE_WINDOW", gui.save_config)
gui.read_config()
root.mainloop()
