# $Id: scanner.py 9f7068449a4b 2010-03-08 mtnyogi $
# coding=utf-8
# 
# Copyright © 2007-2008 Bruce Frederiksen
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

""" See http://www.dabeaz.com/ply/ply.html for syntax of grammer definitions.
"""
from ply.lex import lex

debug = 0

kfb_mode = False
goal_mode = False

states = (
    ('indent', 'exclusive'),
    ('code', 'exclusive'),
    ('checknl', 'exclusive'),
)

kfb_keywords = frozenset((
    'False',
    'None',
    'True',
))

keywords = frozenset((
    'as',
    'assert',
    'bc_extras',
    'check',
    'extending',
    'False',
    'fc_extras',
    'first',
    'forall',
    'foreach',
    'in',
    'None',
    'notany',
    'plan_extras',
    'python',
    'require',
    'step',
    'taking',
    'True',
    'use',
    'when',
    'with',
    'without',
))

base_kfb_tokens = (
    'IDENTIFIER_TOK',
    'LP_TOK',
    'NL_TOK',
    'NUMBER_TOK',
    'RP_TOK',
    'STRING_TOK',
)

base_krb_tokens = base_kfb_tokens + (
    'ANONYMOUS_VAR_TOK',
    'CODE_TOK',
    'DEINDENT_TOK',
    'INDENT_TOK',
    'NOT_NL_TOK',
    'PATTERN_VAR_TOK',
)

kfb_tokens = tuple(x.upper() + '_TOK' for x in kfb_keywords) + base_kfb_tokens

tokens = tuple(x.upper() + '_TOK' for x in keywords) + base_krb_tokens

literals = '*:,!.='

t_ignore = ' \t'

t_ignore_comment = r'\#.*'

def t_continuation(t):
    r'\\(\r)?\n'
    t.lexer.lineno += 1

def t_NL_TOK(t):
    r'(\r)?\n([ \t]*(\#.*)?(\r)?\n)*'
    t.lexer.lineno += t.value.count('\n')
    if kfb_mode:
        return t
    if nesting_level == 0:
        t.lexer.begin('indent')
        t.lexer.skip(-1)
        return t

indent_levels = []

t_indent_ignore = ''

def t_indent_sp(t):
    r'\n[ \t]*'
    indent = count_indent(t.value[1:])[0]
    current_indent = indent_levels[-1] if indent_levels else 0
    if debug:
        print("t_indent_sp: t.value", repr(t.value), "indent", indent, \
              "current_indent", current_indent, \
              "indent_levels", indent_levels, \
              "t.lexpos", t.lexpos, \
              "t.lexer.lexpos", t.lexer.lexpos, \
              "t.lexer.lexdata[]", repr(t.lexer.lexdata[t.lexpos]))
    if indent > current_indent:
        t.type = 'INDENT_TOK'
        indent_levels.append(indent)
        t.lexer.begin('INITIAL')
        if debug:
            print("INDENT_TOK: indent_levels", indent_levels)
        return t
    if indent < current_indent:
        if indent > 0 and indent not in indent_levels:
            raise SyntaxError(
                "deindent doesn't match any previous indent level",
                syntaxerror_params(t.lexpos))
        t.type = 'DEINDENT_TOK'
        del indent_levels[-1]
        if indent < (indent_levels[-1] if indent_levels else 0):
            if debug:
                print(" -- pushing indent back")
            t.lexer.skip(-len(t.value))
        else:
            if debug:
                print(" -- doing begin('INITIAL')")
            t.lexer.begin('INITIAL')
        if debug:
            print("DEINDENT_TOK: indent_levels", indent_levels)
        return t
    t.lexer.begin('INITIAL')
    if debug:
        print("no indent: indent_levels", indent_levels)

t_checknl_ignore = ' \t'

def t_checknl_nl(t):
    r'(\#.*)?(\r)?\n'
    t.lexer.lineno += 1
    t.lexer.begin('indent')
    t.lexer.skip(-1)
    t.type = 'NL_TOK'
    return t

def t_checknl_other(t):
    r'[^\#\r\n]'
    t.lexer.skip(-1)
    t.type = 'NOT_NL_TOK'
    return t

def start_code(plan_name=None, multiline=False,
               var_format="(context['%s'])"):
    global current_line, code, current_plan_name, code__level
    global pattern_var_format, plan_vars_needed, code_nesting_level
    global code_lineno, code_lexpos
    global code_indent_level
    pattern_var_format = var_format
    plan_vars_needed = []
    current_line = ''
    code = []
    if multiline:
        code_indent_level = indent_levels[-1]
    else:
        code_indent_level = 1000000000
    current_plan_name = plan_name
    code_nesting_level = 0
    code_lineno = code_lexpos = None
    lexer.begin('code')

def mark(t):
    global code_lineno, code_lexpos
    if code_lineno is None:
        code_lineno = t.lexer.lineno
        code_lexpos = t.lexpos

t_code_ignore = ''

def t_code_string(t):
    r"'''([^\\]|\\.)*?'''|" \
    r'"""([^\\]|\\.)*?"""|' \
    r"'([^'\\\n\r]|\\.|\\(\r)?\n)*?'|" \
    r'"([^"\\\n\r]|\\.|\\(\r)?\n)*?"'
    global current_line
    current_line += t.value
    mark(t)
    if debug:
        print("scanner saw string:", t.value)
    t.lexer.lineno += t.value.count('\n')

def t_code_comment(t):
    r'[ \t\f\r]*\#.*'
    global current_line
    if debug:
        print("scanner saw comment:", t.value)

def t_code_plan(t):
    r'\$\$'
    global current_line
    mark(t)
    if debug:
        print("scanner saw '$$', current_plan_name is", current_plan_name)
    if not current_plan_name:
        raise SyntaxError("'$$' only allowed in plan_specs within the "
                          "'when' clause",
                          syntaxerror_params(t.lexpos))
    current_line += pattern_var_format % current_plan_name
    plan_vars_needed.append(current_plan_name)

def t_code_paren(t):
    r'[()]'
    global current_line
    current_line += t.value

def t_code_brace(t):
    r'[{]'
    global current_line
    current_line += t.value
    t.lexer.begin('checknl')

def t_code_close_brace(t):
    r'[}]'
    global current_line, code
    current_line += t.value
    code.append(current_line)
    t.lexer.begin('checknl')

def t_code_comma(t):
    r','
    global current_line
    current_line += t.value

def t_code_period(t):
    r'\.'
    global current_line
    current_line += t.value

def t_code_identifier(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    global current_line
    current_line += t.value

def t_code_operator(t):
    r'[=]'
    global current_line
    current_line += t.value

def t_code_newline(t):
    r'\n'
    global code, current_line, current_plan_name, code_nesting_level
    global code_lineno, code_lexpos
    global code_indent_level
    global plan_vars_needed
    global pattern_var_format
    mark(t)
    if debug:
        print("newline in code")
    t.lexer.lineno += 1
    if indent_levels[-1] < code_indent_level:
        if debug:
            print(" -- dedent")
        code_nesting_level -= 1
        if code_nesting_level == 0:
            code_indent_level = 1000000000
            code_lineno = code_lexpos = None
            lexer.begin('indent')
            if debug:
                print("indenting")
            if current_line.strip() != '':
                code.append(current_line)
                current_line = ''
        else:
            if debug:
                print(" -- not ending code yet")
    else:
        if code_lineno is not None:
            lexer.lineno = code_lineno
        if code_lexpos is not None:
            lexer.lexpos = code_lexpos
        if debug:
            print(" -- ending code")
        lexer.begin('INITIAL')
        if debug:
            print("beginning")
        if current_line.strip() != '':
            code.append(current_line)
            current_line = ''
        return t

def t_code_number(t):
    r'\d+'
    global current_line
    current_line += t.value

def t_code_error(t):
    global code_lineno, code_lexpos
    raise SyntaxError("scanner error", syntaxerror_params(t.lexpos))

def count_indent(s):
    return len(s) - len(s.lstrip()), s.lstrip()

def unescape(s):
    return eval('"' + s.replace('"', '\\"') + '"')

def syntaxerror_params(pos):
    return (None, (lexer.lineno, pos - lexer.lexdata.rfind('\n', 0, pos)))

def build(lexer):
    return lex(module=lexer)

lexer = lex()

def tokenize_file(file_name):
    try:
        with open(file_name) as file:
            return tokenize(file.read(), file_name)
    except Exception as e:
        raise type(e)(str(e) + "\n\nScanning file %s" % file_name)

def tokenize(data, file_name='string'):
    lexer.lineno = 1
    lexer.lexpos = 0
    lexer.filename = file_name
    lexer.begin('checknl')
    lexer.input(data)
    while True:
        token = lexer.token()
        if not token:
            break
        yield token
