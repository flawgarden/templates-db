parser grammar TemplateParser;

options { tokenVocab=TemplateLexer; }

holeKind
    : EXPR_KIND
    | CONST_KIND
    | VAR_KIND
    ;

holeTypeIdent
    : (TYPE_NAME | OPEN_BRACKET | CLOSE_BRACKET)+
    ;

holeProperType
    : TYPE
    | holeTypeIdent
    ;

holeType
    : holeProperType
    | (holeTypeIdent type)+ holeTypeIdent?
    | holeTypeIdent? (type holeTypeIdent)+
    ;

holeRef
    : REF_MARKER NUM
    ;

holeBody
    : holeKind UNDERSCORE holeType holeRef?
    ;

hole
    : TILDA OPEN_BRACKET holeBody CLOSE_BRACKET TILDA
    ;

holeArrow
    : TILDA OPEN_BRACKET holeBody CLOSE_BRACKET ARROW
    ;

macro
    : TILDA OPEN_BRACKET MACRO IDENTIFIER CLOSE_BRACKET TILDA
    ;

macroArrow
    : TILDA OPEN_BRACKET MACRO IDENTIFIER CLOSE_BRACKET ARROW
    ;

body
    : TILDA OPEN_BRACKET BODY CLOSE_BRACKET TILDA
    ;

type
    : TILDA OPEN_BRACKET TYPE holeRef? CLOSE_BRACKET TILDA
    ;

codeString
    : (CODE_LINE_PART | hole | macro | body | type)+
    ;

extensionDefinition
    : holeArrow codeString LINE_BREAK+
    ;

macroDefinition
    : macroArrow codeString LINE_BREAK+
    ;

code
    : (codeString | LINE_BREAK)+
    ;

extensions
    : (macroDefinition | extensionDefinition)*
    ;

extensionImport
    : TILDA EXTENSIONS WHITESPACE IMPORT WHITESPACE IDENTIFIER TILDA LINE_BREAK+
    ;

extensionImports
    : extensionImport*
    ;

extensionsStart
    : TILDA EXTENSIONS WHITESPACE START TILDA LINE_BREAK+
    ;

extensionsEnd
    : TILDA EXTENSIONS WHITESPACE END TILDA LINE_BREAK+
    ;

extensionsBlock
    : extensionsStart extensionImports extensions extensionsEnd
    ;

helperImport
    : TILDA HELPER WHITESPACE IMPORT WHITESPACE IDENTIFIER TILDA LINE_BREAK+
    ;

languageImport
    : TILDA IMPORT WHITESPACE IDENTIFIER TILDA LINE_BREAK+
    ;

templateStart
    : TILDA TEMPLATE WHITESPACE IDENTIFIER WHITESPACE START TILDA
    ;

templateEnd
    : TILDA TEMPLATE WHITESPACE END TILDA LINE_BREAK+
    ;

template
    : templateStart code templateEnd
    ;

helperFunctionsStart
    : TILDA HELPER WHITESPACE FUNCTIONS WHITESPACE START TILDA LINE_BREAK+
    ;

helperFunctionsEnd
    : TILDA HELPER WHITESPACE FUNCTIONS WHITESPACE END TILDA LINE_BREAK+
    ;

helperFunctionStart
    : TILDA FUNCTION WHITESPACE IDENTIFIER WHITESPACE START TILDA
    ;

helperFunctionEnd
    : TILDA FUNCTION WHITESPACE END TILDA LINE_BREAK+
    ;

helperFunction
    : helperFunctionStart code helperFunctionEnd
    ;

helperFunctions
    : helperFunctionsStart helperFunction+ helperFunctionsEnd
    ;

mainClassStart
    : TILDA MAIN WHITESPACE BODY_LK WHITESPACE START TILDA LINE_BREAK+
    ;

mainClassEnd
    : TILDA MAIN WHITESPACE BODY_LK WHITESPACE END TILDA LINE_BREAK+
    ;

mainClass
    : mainClassStart helperFunctions? helperImport* languageImport* template+ mainClassEnd
    ;

helperClassStart
    : TILDA CLASS WHITESPACE IDENTIFIER WHITESPACE START TILDA
    ;

helperClassEnd
    : TILDA CLASS WHITESPACE END TILDA LINE_BREAK+
    ;

helperClass
    : helperClassStart code helperClassEnd
    ;

templateFile
    : extensionsBlock? mainClass
    ;

extensionFile
    : extensions
    ;

helperFile
    : helperClass+
    ;
