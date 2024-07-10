#!/bin/bash

generate() {
  if ! cd antlr; then
    exit 1
  fi

  java -jar ../libs/antlr-4.13.1-complete.jar -o ../src/generated -Dlanguage=Python3 ./*.g4
  cp ../src/generated/TemplateLexer.tokens ./
}

clean() {
  rm -rf src/generated
  rm antlr/TemplateLexer.tokens
}

case $1 in
  --generate)
    generate
    ;;
  --clean)
    clean
    ;;
  *)
    echo "FIX ERROR DESCRIPTION"
    ;;
esac