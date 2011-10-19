import os, sys
import re
import cgi

def parse(c):
    start_code = '----'
    end_code = '----'

    prompt_aside = '[ASIDE]'
    start_aside = '['
    end_aside = ']'

    pState = 'out'
    codeState = 'out'
    asideState = 'out'
    listState = 'out'
    promptState = None

    lines = c.splitlines()

    sections = []
    currentPara = ''
    currentCode = ''
    currentAside = ''
    currentList = ''

    for line in lines:
        sline = line.strip()
        if pState == 'in':
            if sline in ['', start_code, start_aside, prompt_aside]:
                pState = 'out'
                if currentPara:
                    sections.append(('p', currentPara))
            else:
                currentPara += ' ' + sline
        else:
            if (not (codeState == 'in'
                    or asideState == 'in'
                    or listState == 'in')
               and sline not in ['', start_code, start_aside, prompt_aside]):
                pState = 'in'
                currentPara = sline

        if codeState == 'in':
            if sline == end_code:
                codeState = 'out'
                if currentCode:
                    sections.append(('code', currentCode))
            else:
                currentCode += line + '\n'
        else:
            if sline == start_code:
                codeState = 'in'
                currentCode = ''

        if asideState == 'in':
            if sline == end_aside:
                asideState = 'out'
                if currentAside:
                    aside = parse(currentAside)
                    sections.append(('aside', aside))
            else:
                currentAside += line + '\n'
        else:
            if sline == start_aside:
                asideState = 'in'
                currentAside = ''

    # clean up at the EOF
    if pState == 'in':
        if currentPara:
            sections.append(('p', currentPara))

    if codeState == 'in':
        if currentCode:
            sections.append(('code', currentCode))

    if asideState == 'in':
        if currentAside:
            aside = parse(currentAside)
            sections.append(('aside', aside))

    return sections

def render_dumb_html(sections):
    for sect in sections:
        if sect[0] == 'p':
            print '<p>'
            print sect[1]
            print '</p>'
        elif sect[0] == 'code':
            print '<pre>'
            print sect[1]
            print '</pre>'
        elif sect[0] == 'aside':
            print '<blockquote>'
            render_dumb_html(sect[1])
            print '</blockquote>'

def render_fodt(sections):
    fp = file('fodt_head.txt')
    c = fp.read()
    fp.close()
    write = sys.stdout.write
    write(c + '\n')
    def highlight_author_notes(text):
        s = '<text:span text:style-name="red_text">'
        e = '</text:span>'
        start_todo = text.find('[TODO')
        if start_todo == -1:
            return text
        end_todo = text.find(']', start_todo)
        text = (text[:start_todo] + s +
                text[start_todo:end_todo+1]
                + e + text[end_todo+1:])
        return text

    def render_sections(sections, paraStyle="Body"):
        for sect in sections:
            if sect[0] == 'p':
                body = sect[1]
                body = cgi.escape(body)
                body = highlight_author_notes(body)
                write('<text:p text:style-name="%s">' % paraStyle)
                write(body)
                write('</text:p>\n')
            elif sect[0] == 'code':
                body = sect[1]
                body = cgi.escape(body)
                for line in body.splitlines():
                    result = re.split('\S', line, 1)
                    if len(result) > 1:
                        spaces = result[0]
                    else:
                        spaces = ''
                    write('<text:p text:style-name="CodeB">')
                    write('<text:s text:c="%d"/>' % len(spaces))
                    write(line[len(spaces):])
                    write('</text:p>\n')
            elif sect[0] == 'aside':
                #write('<text:p text:style-name="Note">')
                write('\n')
                render_sections(sect[1], 'Note')
                write('\n')
                #write('</text:p>\n')
    render_sections(sections)
    fp = file('fodt_tail.txt')
    c = fp.read()
    fp.close()
    write(c + '\n')


def main():
    chfile = sys.argv[1]
    chfile = file(chfile)
    chapter = chfile.read()
    chfile.close()

    sections = parse(chapter)
    #render_dumb_html(sections)
    render_fodt(sections)

if __name__ == '__main__':
    main()
