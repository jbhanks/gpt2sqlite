#! /bin/bash

jq '. | .' $1 > /tmp/conversations_array.json

sqlite-utils insert $2 chats /tmp/conversations_array.json --pk=id

rm /tmp/conversations_array.json

python json2sqlite.py $2
