#!/usr/bin/env bash

# check where we've been launched from
BINDIR=$(cd "${0%/*}" && echo $PWD)

# utility function for exiting
function die {
	echo "$@" >&2
	exit 1
}

DIR=$1
[[ -d "$DIR" ]] || die "usage: $0 DIR"

DB="$DIR/.post.db3"
if [[ ! -e "$DB" ]]; then
	sqlite3 "$DB" "create table if not exists files (md5 text primary key, filename not null, file_url, announce_url)" ||
		die "$0: error creating db"
fi

[[ -r "$DB" ]] || die "$0: db not readable"

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
	MD5=$(openssl dgst -md5 <"$FILE") || die "$0: MD5 failed for file $FILE"
	# TODO handle renamed files
	sqlite3 "$DB" "insert or ignore into files (md5, filename) values ('$(escape_string "$MD5")', '$(escape_string "$BASENAME")')" ||
		die "$0: unable to insert entry into db"
done

# find files that need posting
unset KEYS
unset FILES_TO_POST
SELECT=$(sqlite3 "$DB" "select md5, filename from files where file_url is null") ||
	die "$0: couldn't find files to post"
while IFS=$'\n' read -r LINE; do
	[[ -z "$LINE" ]] && continue
	MD5=${LINE:0:32}
	FILE="$DIR/${LINE:33}"
	is_postable_file "$FILE" || continue
	KEYS[${#KEYS[@]}]=$MD5
	FILES_TO_POST[${#FILES_TO_POST[@]}]=$FILE
done <<< "$SELECT"

# post the files and update db row
FILE_URLS=$("$BINDIR"/post_file.py ${GOOGLE_SITE:+--site $GOOGLE_SITE} "${FILES_TO_POST[@]}") ||
	die "$0: failed to post files"
IDX=0
while IFS=$'\n' read -r FILE_URL; do
	[[ -z "$FILE_URL" ]] && continue
	MD5=${KEYS[IDX]}
	sqlite3 "$DB" "update files set file_url = '$(escape_string "$FILE_URL")' where md5 = '$(escape_string "$MD5")'" ||
		die "$0: failed to set file_url"
	IDX=$((IDX + 1))
done <<< "$FILE_URLS"

# find files that haven't got announcements yet
unset KEYS
unset FILENAMES
unset FILE_URLS
SELECT=$(sqlite3 "$DB" "select md5, filename, file_url from files where file_url is not null and announce_url is null") ||
	die "$0: couldn't find announcements to create"
while IFS=$'\n' read -r LINE; do
	[[ -z "$LINE" ]] && continue
	MD5=${LINE:0:32}
	FILENAME=${LINE:33}
	FILE_URL=${FILENAME#*|}
	FILENAME=${FILENAME:0:${#FILENAME} - ${#FILE_URL} - 1}
	KEYS[${#KEYS[@]}]=$MD5
	FILENAMES[${#FILENAMES[@]}]=$FILENAME
	FILE_URLS[${#FILE_URLS[@]}]=$FILE_URL
done <<< "$SELECT"

function title_from_filename {
	FILENAME=$1
	echo "$FILENAME"
}

function html_from_filename_and_url {
	FILENAME=$1
	FILE_URL=$2
	cat <<-EOF
		<p>Post for file <a href="$FILE_URL">$FILENAME</a>.</p>
	EOF
}

# post announcements
for (( IDX=0; IDX < ${#KEYS[@]}; ++IDX )); do
	MD5=${KEYS[IDX]}
	FILENAME=${FILENAMES[IDX]}
	FILE_URL=${FILE_URLS[IDX]}
	TITLE=$(title_from_filename "$FILENAME")
	HTML=$(html_from_filename_and_url "$FILENAME" "$FILE_URL")
	ANNOUNCE_URL=$("$BINDIR"/post_announcement.py ${GOOGLE_SITE:+--site $GOOGLE_SITE} "$TITLE" <<< "$HTML") ||
		die "$0: failed to post announcement for $FILENAME"
	sqlite3 "$DB" "update files set announce_url = '$(escape_string "$ANNOUNCE_URL")' where md5 = '$(escape_string "$MD5")'" ||
		die "$0: failed to set announce_url"
done
