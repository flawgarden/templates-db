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
BODY_LK        : 'body';
FUNCTION       : 'function';
FUNCTIONS      : 'functions';

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

TYPE
    : 'TYPE' -> pushMode(Hole)
    ;

mode Hole;

ESCAPED_OPEN_BRACKET
    : '\\[' -> type(OPEN_BRACKET)
    ;

ESCAPED_CLOSE_BRACKET
    : '\\]' -> type(CLOSE_BRACKET)
    ;

CLOSE_BRACKET
    : ']' -> popMode, popMode
    ;

TYPE_NAME
    : (~[~\n\r[\]_@0123456789\\])+
    ;

REF_MARKER     : '@';
UNDERSCORE     : '_';
HOLE_TYPE
    : 'TYPE' -> type(TYPE)
    ;

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
