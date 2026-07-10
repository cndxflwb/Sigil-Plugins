
#!/Python3/python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, division, absolute_import, print_function

#********************************************************************************#
#                                                                                #
# MIT Licence(OSI)                                                               #
# Copyright (c) 2017 Bill Thompson                                               #
#                                                                                #
# Permission is hereby granted, free of charge, to any person obtaining a copy   # 
# of this software and associated documentation files (the "Software"), to deal  # 
# in the Software without restriction, including without limitation the rights   #
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell      #
# copies of the Software, and to permit persons to whom the Software is          #
# furnished to do so, subject to the following conditions:                       # 
#                                                                                #
# The above copyright notice and this permission notice shall be included in all #
# copies or substantial portions of the Software.                                #
#                                                                                # 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR     # 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,       #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE    #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER         # 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,  # 
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE  # 
# SOFTWARE.                                                                      #
#                                                                                #  
#********************************************************************************#
import os, os.path, sys, codecs, shutil, inspect, time, html, re
import options
#from tempfile import mkdtemp                 
import tkinter as tk
import tkinter.messagebox as mbox

try:
    from sigil_bs4 import BeautifulSoup, NavigableString
except:
    from bs4 import BeautifulSoup, NavigableString
    
iswindows = sys.platform.startswith('win')
isosx = sys.platform.startswith('darwin')
islinux = sys.platform.startswith('linux')    

PLUGIN_PATH = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
options.PLUGIN_PATH = PLUGIN_PATH

cover_search = ['cover.xhtml',
                'cover.html',
                'coverpage.xhtml',
                'coverpage.html',
                'titlepage.xhtml',
                'titlepage.html'
               ]
              
    
def removeAllTags(bk, epub_version):
    """ Read-only: extract plain text from each HTML and write to a .txt file.
        The EPUB itself is NOT modified.
    """
    print('In RemoveAllTags()...\n')

    prefs = bk.getPrefs()

    #derive output txt path from current epub path (same folder)
    #file name fallback chain: OPF dc:title -> epub file name
    try:
        epub_filepath = bk._w.epub_filepath
    except AttributeError:
        epub_filepath = ''
    if epub_filepath:
        epub_dir = os.path.dirname(epub_filepath)
        base_name = ''
        #1) try OPF metadata <dc:title>
        opf_title = getOpfTitle(bk)
        if opf_title:
            base_name = sanitizeFilename(opf_title)
        #2) fallback to epub file name (without extension)
        if not base_name:
            base_name = os.path.splitext(os.path.basename(epub_filepath))[0]
        prefs['save_file_path'] = os.path.join(epub_dir, base_name + '.txt')

    #remove the last saved plain text file
    outpath = prefs['save_file_path']
    if os.path.exists(outpath):
        os.remove(outpath)

    #extract body text from each HTML file and write to the plain text file
    for (id, href) in bk.text_iter():

        #ignore the cover file
        fname = bk.href_to_basename(href)
        if fname.strip().lower() in " ".join(cover_search) or \
            'cover' in id.lower():
            continue

        data = bk.readfile(id)
        print('Processing: id=%s  href=%s' % (id, href))
        soup = BeautifulSoup(data, 'html.parser')

        if soup.body is None:
            print('  -> soup.body is None, skipping.')
            continue

        #extract text via safe recursive traversal (avoids sigil_bs4 next_element bug)
        mark_headings = prefs.get('mark_headings_as_markdown', False)
        text_only = safeGetText(soup.body, mark_headings)
        text_only = '\n' + text_only.strip() + '\n'

        #save all sections to an plain text output file
        if prefs['save_plain_text_to_file'] == True:
            lines = text_only.splitlines(True)
            outfile = prefs['save_file_path']
            with open(outfile, 'at', encoding='utf-8') as outfp:
                for line in lines:
                    if line.strip() == '':
                        continue
                    outfp.write(line.strip() + '\n')

    print('Exiting RemoveAllTags()...\n')
    return(0)    


def safeGetText(node, mark_headings=False):
    """ Safely extract text from a BeautifulSoup node using only node.children
        (avoids sigil_bs4's broken descendants/next_element traversal).
        When mark_headings is True, h1-h6 tags are prefixed with markdown '#'.
    """
    HEADING_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
    parts = []

    def _extract(n):
        try:
            children = list(n.children)
        except AttributeError:
            # NavigableString or leaf node
            text = ''
            try:
                text = str(n)
            except Exception:
                pass
            parts.append(text)
            return

        tag_name = getattr(n, 'name', None)
        if tag_name is None:
            # plain text node
            try:
                parts.append(str(n))
            except Exception:
                pass
            return

        tag_lower = tag_name.lower() if tag_name else ''

        if mark_headings and tag_lower in HEADING_TAGS:
            level = int(tag_lower[1])
            prefix = '#' * level + ' '
            # collect heading text safely
            sub = []
            for child in children:
                sub_parts = []
                def _collect(nn, out=sub_parts):
                    try:
                        cc = list(nn.children)
                    except AttributeError:
                        try:
                            out.append(str(nn))
                        except Exception:
                            pass
                        return
                    nn_name = getattr(nn, 'name', None)
                    if nn_name is None:
                        try:
                            out.append(str(nn))
                        except Exception:
                            pass
                        return
                    for c in cc:
                        _collect(c, out)
                _collect(child)
                sub.extend(sub_parts)
            heading_text = re.sub(r'\s+', ' ', ''.join(sub)).strip()
            # fallback: if tag body is empty, try the title attribute
            if not heading_text:
                try:
                    heading_text = (n.get('title') or '').strip()
                except Exception:
                    heading_text = ''
            if heading_text:
                parts.append('\n' + prefix + heading_text + '\n')
        else:
            for child in children:
                _extract(child)

    _extract(node)
    return ''.join(parts)


def getOpfTitle(bk):
    """ Return first non-empty <dc:title> text from OPF metadata, or '' """
    try:
        metaxml = bk.getmetadataxml()
    except Exception:
        return ''
    if not metaxml:
        return ''
    try:
        soup = BeautifulSoup(metaxml, 'xml')
    except Exception:
        soup = BeautifulSoup(metaxml, 'html.parser')
    for t in soup.find_all(['dc:title', 'title']):
        text = (t.get_text() or '').strip()
        if text:
            return text
    return ''


def sanitizeFilename(name):
    """ Strip characters illegal in Windows/Unix file names and trim """
    #replace illegal chars: \ / : * ? " < > | and control chars
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', name)
    #collapse whitespace, strip trailing dots/spaces (Windows restriction)
    name = re.sub(r'\s+', ' ', name).strip().rstrip('.')
    #limit length to avoid path-too-long
    if len(name) > 120:
        name = name[:120].rstrip()
    return name


def show_msgbox(title, msg, msgtype='info'):
    """ For general information, warnings and errors
    """
    localRoot = tk.Tk()
    localRoot.withdraw()
    localRoot.option_add('*font', 'Helvetica -12')
    localRoot.quit()
    if msgtype == 'info':
        return(mbox.showinfo(title, msg))
    elif msgtype == 'warning':
        return(mbox.showwarning(title, msg))
    elif msgtype == 'error':
        return(mbox.showerror(title, msg))          
  
  
def run(bk):
    print('Python version: ', sys.version, '\n')
    print('Running VerifyOPFData plugin...')
    error_list = []

    epub_version = 0 
    # protect against epub3 input
    epubversion = "2.0"
    if bk.launcher_version() >= 20160102:
        epubversion = bk.epub_version()
    if epubversion.startswith("3"):
        epub_version = 3
    else: 
        epub_version = 2    
    
    prefs = bk.getPrefs()
    if 'save_plain_text_to_file' not in prefs:
        prefs['save_plain_text_to_file'] = True
    if 'save_file_path' not in prefs:
        prefs['save_file_path'] = os.path.join(os.path.expanduser("~/Desktop"), 'textfile.txt')
    if 'mark_headings_as_markdown' not in prefs:
        prefs['mark_headings_as_markdown'] = False
    bk.savePrefs(prefs)
       
    # check and process the OPF file
    removeAllTags(bk, epub_version)
    
    #notify user if plain text file has been saved
    if prefs['save_plain_text_to_file'] == True:    
        msg = 'A plain text file has been saved to:\n\n' + prefs['save_file_path']
        show_msgbox('Information', msg, msgtype='info')      

    print('\n-- Completed SUCCESSFULLY...')
    return(0)                
    
def main():
    print('I reached main when I should not have\n')
    return(-1)

if __name__ == "__main__":
    sys.exit(main())                         