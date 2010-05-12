#!/usr/bin/env bash

BINDIR=$(dirname "$0")
DIR=$1
[[ -d "$DIR" ]] || { echo "usage: $0 DIR" >&2; exit 1; }

DB="$DIR/.post.db3"
if [[ ! -e "$DB" ]]; then
	sqlite3 "$DB" "create table if not exists files (md5 text primary key, filename not null, file_url, announce_url)" ||
		{ echo "$0: error creating db" >&2; exit 1; }
fi

[[ -r "$DB" ]] || { echo "$0: db not readable" >&2; exit 1; }

function escape_string {
	echo -n "$@" | sed "s/'/''/g"
}

function is_postable_file {
	[[ -f "$1" && -r "$1" && -s "$1" ]]
}

# add files to database
for FILE in "$DIR"/*; do
	is_postable_file "$FILE" || continue
	BASENAME=$(basename "$FILE")
	MD5=$(openssl dgst -md5 <"$FILE") || { echo "$0: MD5 failed for file $FILE" >&2; exit 1; }
	# TODO handle renamed files
	sqlite3 "$DB" "insert or ignore into files (md5, filename) values ('$(escape_string "$MD5")', '$(escape_string "$BASENAME")')" ||
		{ echo "$0: unable to insert entry into db" >&2; exit 1; }
done

# find files that need posting
unset FILES_TO_POST
unset KEYS
SELECT=$(sqlite3 "$DB" "select md5, filename from files where file_url is null") ||
	{ echo "$0: couldn't find files to post" >&2; exit 1; }
while IFS=$'\n' read -r LINE; do
	MD5=${LINE:0:32}
	FILE="$DIR/${LINE:33}"
	is_postable_file "$FILE" || continue
	KEYS[${#KEYS[@]}]=$MD5
	FILES_TO_POST[${#FILES_TO_POST[@]}]=$FILE
done <<< "$SELECT"

# post the files and update db row
FILE_URLS=$("$BINDIR"/post_file.py "${FILES_TO_POST[@]}") ||
	{ echo "$0: failed to post files" >&2; exit 1; }
IDX=0
while IFS=$'\n' read -r FILE_URL; do
	MD5=${KEYS[IDX]}
	sqlite3 "$DB" "update files set file_url = '$(escape_string "$FILE_URL")' where md5 = '$(escape_string "$MD5")'" ||
		{ echo "$0: failed to set file_url" >&2; exit 1; }
	IDX=$((IDX + 1))
done <<< "$FILE_URLS"
