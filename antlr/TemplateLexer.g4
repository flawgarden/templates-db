lexer grammar TemplateLexer;

LINE_BREAK
    : '\r' '\n' | '\n' | '\r'
    ;

TILDA
    : '~' -> pushMode(TemplateLanguage)
    ;

COMMENT_START
    : '#' -> pushMode(Comment)
    ;

CODE_LINE_PART
    : (~[~\n\r])+
    ;

mode Comment;

COMMENT_LINE
    : (~[\n\r])+ -> popMode
    ;

mode TemplateLanguage;

T_TILDA
    : '~' -> popMode, type(TILDA)
    ;

ARROW
    : '~ ->' -> popMode
    ;

OPEN_BRACKET
    : '[' -> pushMode(MacrosOrHole)
    ;

WHITESPACE     : ' ';
CLASS          : 'class';
EXTENSIONS     : 'extensions';
HELPER         : 'helper';
IMPORT         : 'import';
START          : 'start';
END            : 'end';
TEMPLATE       : 'template';
MAIN           : 'main';

IDENTIFIER
    : (~[\n\r~[\] ])+
    ;

mode MacrosOrHole;

EXPR_KIND
    : 'EXPR' -> pushMode(Hole)
    ;

CONST_KIND
    : 'CONST' -> pushMode(Hole)
    ;

VAR_KIND
    : 'VAR' -> pushMode(Hole)
    ;

MACRO
    : 'MACRO' -> pushMode(Macro)
    ;

BODY
    : 'BODY' -> pushMode(Hole)
    ;

mode Hole;

CLOSE_BRACKET
    : ']' -> popMode, popMode
    ;

INT_TYPE       : 'Integer';
STRING_TYPE    : 'String';
BOOL_TYPE      : 'Boolean';
GENERIC_START  : '<';
GENERIC_END    : '>';
COMMA          : ',';
DICT_TYPE_NAME : 'Dict';
SET_TYPE_NAME  : 'Set';
LIST_TYPE_NAME : 'List';
REF_MARKER     : '@';
UNDERSCORE     : '_';

NUM
    : [0-9]+
    ;

mode Macro;

MACROS_IDENTIFIER
    : (~[~\n\r[\] ])+ -> type(IDENTIFIER)
    ;

MACROS_CLOSE_BRACKET
    : ']' -> popMode, popMode, type(CLOSE_BRACKET)
    ;
