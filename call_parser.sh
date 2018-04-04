#!/bin/sh

PARSER_DIR="../lib/Finnish-dep-parser/"
cd $PARSER_DIR
cat -|./split_text_with_comments.sh|./parse_conll.sh

