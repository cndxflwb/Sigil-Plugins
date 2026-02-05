#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EPUB 字数统计插件（兼容旧版 Sigil）
- 统计：总字数（非空白字符）、英文单词、英文半角标点、中文全角标点、CJK 字符（按分区统计）
- 弹窗显示：使用 Windows 原生 MessageBoxW
- 新增：统计指定 HTML 标签的出现次数
- 改造：新增所有字符、CJK 字符（按区块）、数字、字母、其他字符的详细统计和去重统计。
"""

import re
import sys
# import ctypes # 暂时不需要弹窗
from collections import defaultdict

# HTMLParser 兼容 (py2/py3)
try:
    from html.parser import HTMLParser
except ImportError:
    from HTMLParser import HTMLParser

# BeautifulSoup from sigil_bs4 (Sigil 内置适配)
try:
    from sigil_bs4 import BeautifulSoup
except Exception:
    # 如果 sigil_bs4 不存在，尝试普通 bs4（仅备用）
    try:
        from bs4 import BeautifulSoup
    except Exception:
        BeautifulSoup = None

# 完整的 CJK 扩展区定义（使用用户提供的完整列表）
CJK_EXTENSIONS = [
    {'name': '基本区', 'ranges': [(0x4E00, 0x9FFF)]},
    {'name': '兼容汉字', 'ranges': [(0xF900, 0xFAD9)]},
    {'name': '兼容扩展', 'ranges': [(0x2F800, 0x2FA1D)]},
    {'name': '私用区', 'ranges': [(0xE000, 0xF8FF)]},
    {'name': '补充私人使用区A', 'ranges': [(0xF0000, 0xFFFFF)]},
    {'name': '补充私人使用区B', 'ranges': [(0x100000, 0x10FFFF)]},
    {'name': '扩展A', 'ranges': [(0x3400, 0x4DB5)]},
    {'name': '扩展B', 'ranges': [(0x20000, 0x2A6DF)]},
    {'name': '扩展C', 'ranges': [(0x2A700, 0x2B73A)]},
    {'name': '扩展D', 'ranges': [(0x2B740, 0x2B81D)]},
    {'name': '扩展E', 'ranges': [(0x2B820, 0x2CEA1)]},
    {'name': '扩展F', 'ranges': [(0x2CEB0, 0x2EBE0)]},
    {'name': '扩展G', 'ranges': [(0x30000, 0x3134A)]},
    {'name': '扩展H', 'ranges': [(0x31350, 0x323AF)]},
    {'name': '扩展I', 'ranges': [(0x2EBF0, 0x2EE5D)]},
    {'name': '扩展J', 'ranges': [(0x323B0, 0x33479)]},
]

# 要统计的 HTML 标签列表
TAGS_TO_COUNT = ['b', 'i', 'u', "img", "table","ruby"]

# --- 原始辅助函数（MLStripper, strip_tags, iter_chars）保持不变 ---

# HTML -> 文本：使用 HTMLParser 提取文本节点
class MLStripper(HTMLParser):
    def __init__(self):
        # 兼容 py2/py3 的基类初始化方式
        try:
            HTMLParser.__init__(self)
        except Exception:
            super(MLStripper, self).__init__()
        self.reset()
        self.strict = False
        # py3 的 HTMLParser 有 convert_charrefs 参数，但 py2 没有也没关系
        try:
            self.convert_charrefs = True
        except Exception:
            pass
        self.text_parts = []

    def handle_data(self, d):
        self.text_parts.append(d)

    def get_data(self):
        return ''.join(self.text_parts)

def strip_tags(html):
    s = MLStripper()
    try:
        s.feed(html)
    except Exception:
        # 有时 feed 在旧版会出问题，兜底直接返回原始文本
        pass
    return s.get_data()

# 迭代文本字符（处理 UTF-16 surrogate pair，确保跨 BMP 的码点被当作一个字符处理）
def iter_chars(text):
    """
    遍历字符串，按“用户可见字符”切分：
    - 在 narrow build（如某些 Python2/Windows 环境）中，BMP 以外的字符以 surrogate pair 两个 code units 表示，
      本函数会把它们合并为单个项返回 (codepoint, string_slice)。
    返回：(codepoint_int, string_slice)
    """
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        cp = ord(ch)
        # high surrogate range
        if 0xD800 <= cp <= 0xDBFF and i + 1 < n:
            low = ord(text[i + 1])
            if 0xDC00 <= low <= 0xDFFF:
                # 合成实际码点
                full_cp = ((cp - 0xD800) << 10) + (low - 0xDC00) + 0x10000
                yield full_cp, text[i:i+2]
                i += 2
                continue
        yield cp, ch
        i += 1

def is_cjk_codepoint(cp):
    """判断 codepoint 是否属于任何一个 CJK 扩展区"""
    for part in CJK_EXTENSIONS:
        for (start, end) in part['ranges']:
            if start <= cp <= end:
                return True
    return False

def which_cjk_extension(cp):
    """返回第一个匹配的扩展区名称，找不到则返回 None"""
    for part in CJK_EXTENSIONS:
        for (start, end) in part['ranges']:
            if start <= cp <= end:
                return part['name']
    return None

# --- 改造后的统计函数 ---
def count_text(html_content):
    # 先去掉 HTML 标签
    text = strip_tags(html_content)

    # 兼容 py2/py3 的 unicode 判断：确保 text 是 unicode 类型
    try:
        unicode  # type: ignore
    except NameError:
        # py3
        _unicode_type = str
    else:
        _unicode_type = unicode  # type ignore

    if not isinstance(text, _unicode_type):
        try:
            text = text.decode('utf-8')
        except Exception:
            try:
                text = _unicode_type(text)
            except Exception:
                # 兜底：替换非 utf-8 字节
                try:
                    text = text.decode('utf-8', 'ignore')
                except Exception:
                    text = unicode(text, errors='ignore') if _unicode_type is not str else str(text)


    # 字典用于存储统计结果
    # { (codepoint, char_str): count }
    all_char_counts = defaultdict(int)
    # { 'Extension Name': { (codepoint, char_str): count } }
    cjk_char_counts_by_ext = defaultdict(lambda: defaultdict(int))

    # 按类别分组的字符（非空白）
    digits_chars = defaultdict(int)
    letters_chars = defaultdict(int)
    other_chars = defaultdict(int)

    # 原始的统计项（可选保留，但本改造主要关注新需求）
    total_chars = 0
    total_cjk = 0
    
    # 使用迭代器保证 surrogate pair 被当作一个字符
    for cp, chstr in iter_chars(text):
        # 排除空白
        if chstr.isspace():
            continue

        # 1. 总字符统计（非空白）
        total_chars += 1
        all_char_counts[(cp, chstr)] += 1
        
        # 2. CJK 字符分类统计
        is_cjk = False
        if is_cjk_codepoint(cp):
            total_cjk += 1
            ext = which_cjk_extension(cp)
            if ext:
                cjk_char_counts_by_ext[ext][(cp, chstr)] += 1
                is_cjk = True
        
        # 3. 数字、字母、其他字符分类统计 (非 CJK 且 非空白)
        if not is_cjk:
            if chstr.isdigit():
                digits_chars[(cp, chstr)] += 1
            elif chstr.isalpha():
                letters_chars[(cp, chstr)] += 1
            else:
                # 不属于 CJK, 数字, 字母, 空白 的都归入 '其他'
                other_chars[(cp, chstr)] += 1

    # 原始统计（仅保留总数，其他详细统计已通过 all_char_counts 实现）
    english_words = len(re.findall(r'[A-Za-z]+', text))
    halfwidth_punct = len(re.findall(r'[!"#$%&\'()*+,\-./:;<=>?@\[\]\\\^_`{|}~]', text))
    fullwidth_punct = len(re.findall(u'[！？｡。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～、《》〈〉「」『』【】〔〕——……￥]', text))
    
    return {
        'total_chars': total_chars,
        'english_words': english_words,
        'halfwidth_punct': halfwidth_punct,
        'fullwidth_punct': fullwidth_punct,
        'total_cjk': total_cjk,
        
        # 新增统计结果
        'all_char_counts': all_char_counts,
        'cjk_char_counts_by_ext': cjk_char_counts_by_ext,
        'digits_chars': digits_chars,
        'letters_chars': letters_chars,
        'other_chars': other_chars,
    }

# 统计 HTML 标签函数
def count_html_tags(html_content):
    """统计指定 HTML 标签的出现次数"""
    tag_counts = {tag: 0 for tag in TAGS_TO_COUNT}
    
    if not BeautifulSoup:
        return tag_counts
    
    try:
        # 使用 'html.parser' 兼容性更好
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for tag in TAGS_TO_COUNT:
            tag_counts[tag] = len(soup.find_all(tag))
            
    except Exception:
        # 如果解析失败，返回空统计
        pass
    
    return tag_counts

# --- 改造后的输出函数 ---
def format_char_counts(title, char_counts):
    """格式化输出字符统计列表"""
    lines = []
    
    # 按照出现次数降序，然后按 Unicode 码点升序排序
    # char_counts 是 {(cp, chstr): count} 的字典
    sorted_chars = sorted(
        char_counts.items(), 
        key=lambda item: (-item[1], item[0][0])
    )
    
    total_count = sum(char_counts.values())
    unique_count = len(char_counts)
    
    lines.append(u"### {0}".format(title))
    lines.append(u"总字符数：{0}, 去重字符数：{1}".format(total_count, unique_count))
    if unique_count > 0:
        lines.append(u"序号,Unicode,字符,出现次数")
        for i, ((cp, chstr), count) in enumerate(sorted_chars):
            # 格式化 Unicode：U+000000
            unicode_str = u"U+{0:04X}".format(cp)
            lines.append(u"{0},{1},{2},{3}".format(i+1, unicode_str, chstr, count))
    
    return lines

# Sigil 插件入口
def run(container):
    # 汇总所有文件统计
    total_chars = 0
    total_cjk = 0
    all_char_counts = defaultdict(int)
    cjk_char_counts_by_ext = defaultdict(lambda: defaultdict(int))
    digits_chars = defaultdict(int)
    letters_chars = defaultdict(int)
    other_chars = defaultdict(int)

    # 原始统计（可选保留）
    english_words = 0
    halfwidth_punct = 0
    fullwidth_punct = 0

    # 标签统计保持不变
    total_tag_counts = {tag: 0 for tag in TAGS_TO_COUNT}
    file_tag_stats = []

    # 遍历 EPUB 文档
    for name, href in container.text_iter():
        try:
            data = container.readfile(name)
        except Exception:
            continue

        # 统计 HTML 标签
        file_tag_counts = count_html_tags(data)
        file_tag_stats.append((name, file_tag_counts))
        for tag, count in file_tag_counts.items():
            total_tag_counts[tag] += count

        # 提取文本进行字符统计
        if BeautifulSoup:
            try:
                soup = BeautifulSoup(data, 'html.parser')
                # 尝试用 get_text() 获取纯文本
                html_for_count = soup.get_text() if hasattr(soup, 'get_text') else str(soup)
            except Exception:
                html_for_count = data
        else:
            html_for_count = data

        res = count_text(html_for_count)
        
        # 汇总字符统计
        total_chars += res['total_chars']
        total_cjk += res['total_cjk']
        english_words += res['english_words']
        halfwidth_punct += res['halfwidth_punct']
        fullwidth_punct += res['fullwidth_punct']

        for cp_chstr, count in res['all_char_counts'].items():
            all_char_counts[cp_chstr] += count
        for ext, counts in res['cjk_char_counts_by_ext'].items():
            for cp_chstr, count in counts.items():
                cjk_char_counts_by_ext[ext][cp_chstr] += count
        for cp_chstr, count in res['digits_chars'].items():
            digits_chars[cp_chstr] += count
        for cp_chstr, count in res['letters_chars'].items():
            letters_chars[cp_chstr] += count
        for cp_chstr, count in res['other_chars'].items():
            other_chars[cp_chstr] += count


    # 构造输出文本（unicode）
    all_lines = []

    # --- 1. 总览和原始统计 ---
    all_lines.append(u"# 📖 EPUB 字符统计报告")
    all_lines.append(u"总字数（非空白字符）：{0}".format(total_chars))
    all_lines.append(u"英文单词：{0}, 英文半角标点：{1}, 中文全角标点：{2}".format(english_words, halfwidth_punct, fullwidth_punct))
    all_lines.append(u"")
    
    # --- 2. 所有字符详细统计 ---
    all_lines.extend(format_char_counts(u"✅ 1. 所有非空白字符列表", all_char_counts))
    all_lines.append(u"")
    
    # --- 3. CJK 字符（按区块）详细统计 ---
    all_lines.append(u"## 📝 2. CJK 字符分区统计 (总数：{0}, 去重：{1})".format(total_cjk, len([c for ext in cjk_char_counts_by_ext.values() for c in ext])))
    if total_cjk > 0:
        for part in CJK_EXTENSIONS:
            name = part['name']
            counts = cjk_char_counts_by_ext[name]
            if counts: # 只显示有字符的分区
                all_lines.extend(format_char_counts(u"分区：{0}".format(name), counts))
                all_lines.append(u"")
    
    # --- 4. 数字、字母、其他字符统计 ---
    all_lines.append(u"## 🔢 3. 数字、字母、其他字符统计")
    all_lines.extend(format_char_counts(u"数字 (0-9)", digits_chars))
    all_lines.append(u"")
    all_lines.extend(format_char_counts(u"字母 (a-z, A-Z)", letters_chars))
    all_lines.append(u"")
    all_lines.extend(format_char_counts(u"🧩 4. 其他字符（非空白、非CJK、非数字、非字母）", other_chars))
    all_lines.append(u"")

    # --- 5. HTML 标签统计（可选保留） ---
    all_lines.append(u"# 🏷️ HTML 标签统计（各文件明细）")
    for filename, tag_counts in file_tag_stats:
        if any(count > 0 for count in tag_counts.values()):
            all_lines.append(u"  {0}:".format(filename))
            for tag in TAGS_TO_COUNT:
                if tag_counts[tag] > 0:
                    all_lines.append(u"    {0}: {1}".format(tag, tag_counts[tag]))

    msg = u"\n".join(all_lines)

    # 同时打印到控制台（Sigil 插件执行时的标准输出）
    try:
        if sys.version_info[0] < 3:
            # Python2：把 unicode 编码为 utf-8 打印
            sys.stdout.write(msg.encode('utf-8') + b"\n")
        else:
            print(msg)
    except Exception:
        # 最后兜底：不抛异常
        pass

    # 注释掉 Windows 消息框，只使用控制台输出
    # try:
    #     title = u"EPUB 字数统计"
    #     ctypes.windll.user32.MessageBoxW(0, msg, title, 0)
    # except Exception:
    #     pass

    # 返回 1 表示成功（Sigil 运行成功）
    return 1

def main():
    return run