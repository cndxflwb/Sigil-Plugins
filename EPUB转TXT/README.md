# EPUB2TXT — Sigil 插件（中文版）

将 Sigil 中打开的 EPUB 一键导出为纯文本 `.txt` 文件的 Sigil 插件。

> 本插件基于 slowsmile 的原始插件 [RemoveHTMLTags_v013](https://www.mobileread.com/forums/showthread.php?t=352023) 修改而来，仅保留并强化了「导出纯文本到外部文件」这一核心功能，移除了会修改 EPUB 自身内容的操作，使插件以 **只读** 方式工作，对原书更安全。

当前版本：**v0.0.2**
适用于：Sigil（Python 3.4+），支持 EPUB2 与 EPUB3，支持 Windows / macOS / Linux。

---

## 功能简介

运行插件后，会读取 Book Browser 中所有 XHTML 章节，把 `<body></body>` 之间的正文提取为纯文本，并合并保存为一个 `.txt` 文件。

主要特点：

- **只读、不改 EPUB**：插件只读取章节内容，不会向你的 EPUB 写回任何修改，运行后无需再做"还原"操作。
- **自动命名输出文件**：输出文件名优先取自 OPF 元数据中的 `<dc:title>`（书名），若没有则使用 EPUB 文件名；非法字符会被自动替换为下划线。
- **保存到 EPUB 同目录**：默认把 `.txt` 文件保存到当前 EPUB 所在的同一文件夹下，方便归档和管理（不再像原版那样固定保存到桌面）。
- **自动跳过封面页**：根据常见的 cover 文件名（`cover.xhtml`、`titlepage.xhtml` 等）和 id 中包含 `cover` 的章节自动跳过，避免输出"封面"两个字这类无意义内容。
- **可选 Markdown 标题标记**：可在 JSON 配置中开启，将 `<h1>~<h6>` 输出为 `#`、`##`、…… 等 Markdown 风格的标题行，便于后续做章节分割、目录提取或转 Markdown。
- **空行清理**：输出时自动去掉每段前后多余空白和空行，得到紧凑、便于阅读的纯文本。
- **完成后弹窗提示**：导出完成后会弹出消息框，显示生成的 `.txt` 文件完整路径。

## 与原插件的区别

相对原版 RemoveHTMLTags，本中文修改版做了以下调整：

| 项目 | 原版 | 本版本 |
| --- | --- | --- |
| 是否修改 EPUB 内容 | 会把 `<body>` 内 HTML 改写为纯文本或简单 `<p>` 包裹 | **不修改 EPUB**，纯只读 |
| `convert_to_plain_text` 选项 | 有，用于切换"纯文本视图 / 简单 HTML 视图" | **已移除**（始终输出纯文本到外部文件） |
| `remove_unused_files` 选项 | 有，可一键删除 Styles/Images/Fonts | **已移除**，避免误删资源 |
| 输出文件路径 | 默认固定为桌面 `textfile.txt` | 默认与当前 EPUB **同目录**，文件名取自书名 |
| 封面识别 | 简单匹配 | 文件名 + id 双重匹配，更稳定 |
| 标题标记 | 无 | 新增 `mark_headings_as_markdown`，可输出 `#`/`##` 风格标题 |

## 使用方法

1. 在 Sigil 中打开任意 EPUB（EPUB2 或 EPUB3 均可）。
2. 菜单：**插件 → 校验 → EPUB2TXT**。
3. 等待运行结束，弹窗会提示生成的 `.txt` 文件路径，例如：

   ```
   D:\Books\我的书名.txt
   ```

   该文件位于当前 EPUB 所在目录，可直接用任意文本编辑器打开。

## 偏好设置（JSON Prefs）

插件首次运行后，会在 Sigil 的插件偏好目录下生成 `EPUB2TXT.json`，可在 Sigil 中通过 **插件 → 插件管理 → 打开首选项文件夹** 找到并编辑：

```json
{
  "save_plain_text_to_file": true,
  "save_file_path": "C:\\Users\\<YOU>\\Desktop\\textfile.txt",
  "mark_headings_as_markdown": false
}
```

各字段说明：

- **`save_plain_text_to_file`**（默认 `true`）
  是否把提取出来的纯文本保存为外部 `.txt` 文件。设为 `false` 时，插件只会在控制台/调试输出中处理，不写文件。

- **`save_file_path`**
  上一次保存的 `.txt` 文件完整路径。**通常无需手动修改** —— 每次运行时，插件会自动根据当前 EPUB 路径与书名重新计算并覆盖该字段。这里保留它仅作为记录或在异常情况（无法获取 EPUB 路径）下作为回退路径使用。

- **`mark_headings_as_markdown`**（默认 `false`）
  是否将各级标题以 Markdown 形式输出。开启后：

  - `<h1>章节一</h1>` → `# 章节一`
  - `<h2>第一节</h2>` → `## 第一节`
  - …… 以此类推到 `<h6>` → `######`

  非常适合后续用脚本按 `#` 切分章节，或直接转换成 Markdown 文档。

## 输出示例

开启 `mark_headings_as_markdown` 后，输出大致如下：

```
# 第一章 启程

那是一个很普通的早晨……
他推开门，外面下着小雨。

## 1.1 旧友

许久未见的老朋友突然来电……
```

不开启时，则得到不带任何标记的紧凑纯文本（每段一行，章节之间无多余空白）。

## 常见问题

**Q：为什么我的输出文件不在桌面，而在 EPUB 所在文件夹？**
这是本版本的设计调整：把 `.txt` 与原书放在一起更便于管理。如果你需要桌面输出，可以在导出后手工拷贝，或自行修改 `plugin.py` 中 `removeAllTags()` 内组装 `save_file_path` 的那几行。

**Q：插件会不会破坏我的 EPUB？**
不会。本版本是纯只读插件，仅调用 `bk.readfile()` 与 `bk.text_iter()` 读取章节内容，不会调用任何写回 EPUB 的接口。

**Q：导出文件中夹杂了"封面 / Cover"等字样怎么办？**
插件已根据常见文件名和 id 关键字自动跳过封面页。如果你的封面 XHTML 命名比较特殊，可在 `plugin.py` 顶部的 `cover_search` 列表中加入对应的文件名。

**Q：运行后想得到"完全不分段、没有空行的一团纯文本"怎么办？**
可在 Sigil 中先运行本插件得到 `.txt`，再用任意文本工具去除换行；或参考原插件作者建议：在 Sigil 中执行 **Tools → Reformat → Mend and Prettify**（针对 EPUB 内容做规整后再导出）。

## 许可证

沿用原插件的 **MIT License**。版权信息保留在 `EPUB2TXT/Licence.txt` 与 `plugin.py` 文件头中。

## 致谢

- 原始插件作者：**slowsmile**（[MobileRead 帖子](https://www.mobileread.com/forums/showthread.php?t=352023)）
- 原始灵感来源：kbanelas 的 **smoothRemove** 插件（Python 2.7）
- 中文修改与维护：**赤霓**
