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
for FILE in "$DIR"/*.mp3; do
	is_postable_file "$FILE" || continue
	BASENAME=$(basename "$FILE")
	MD5=$(openssl dgst -md5 <"$FILE") || die "$0: MD5 failed for file $FILE"
	# TODO handle renamed files
	FILE_IN_DB=$(sqlite3 "$DB" "select count(*) from files where md5 = '$(escape_string "$MD5")'") ||
		die "$0: unable to query db"
	if [[ "$FILE_IN_DB" == "0" ]]; then
		if command -v id3v2 >/dev/null; then
			id3v2 --delete-all "$FILE"
			MD5=$(openssl dgst -md5 <"$FILE") || die "$0: MD5 failed for file $FILE"
		fi
		sqlite3 "$DB" "insert or ignore into files (md5, filename) values ('$(escape_string "$MD5")', '$(escape_string "$BASENAME")')" ||
			die "$0: unable to insert entry into db"
	fi
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
FILE_URLS=$("$BINDIR"/post_file.py ${GOOGLE_SITE:+--site "$GOOGLE_SITE"} ${GOOGLE_DOMAIN:+--domain "$GOOGLE_DOMAIN"} "${FILES_TO_POST[@]}") ||
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

function input_to_lines {
	unset LINES
	while IFS='$\n' read -r LINE; do
		LINES[${#LINES[@]}]=$LINE
	done
}

function announcement_title {
	FILENAME=$1
	PARTS=$2
	if [[ -z "$PARTS" ]]; then
		echo "$FILENAME"
	else
		input_to_lines <<< "$PARTS"
		echo "${LINES[2]} - ${LINES[3]} - ${LINES[0]} ${LINES[1]}"
	fi
}

function announcement_html {
	FILENAME=$1
	FILE_URL=$2
	PARTS=$3
	if [[ -z "$PARTS" ]]; then
		cat <<-EOF
			<p>Post for file <a href="$FILE_URL">$FILENAME</a>.</p>
		EOF
	else
		input_to_lines <<< "$PARTS"
		cat <<-EOF
			<p>
			  Message: ${LINES[3]}<br />
			  Date: ${LINES[0]}<br />
			  Speaker: ${LINES[2]}<br />
			</p>
			<p>Link: <a href="$FILE_URL">$FILE_URL</a></p>
		EOF
	fi
}

# post announcements
for (( IDX=0; IDX < ${#KEYS[@]}; ++IDX )); do
	MD5=${KEYS[IDX]}
	FILENAME=${FILENAMES[IDX]}
	FILE_URL=${FILE_URLS[IDX]}
	PARTS=$("$BINDIR"/split_filename_into_parts.py "$FILENAME")
	TITLE=$(announcement_title "$FILENAME" "$PARTS")
	HTML=$(announcement_html "$FILENAME" "$FILE_URL" "$PARTS")
	ANNOUNCE_URL=$("$BINDIR"/post_announcement.py ${GOOGLE_SITE:+--site "$GOOGLE_SITE"} ${GOOGLE_DOMAIN:+--domain "$GOOGLE_DOMAIN"} "$TITLE" <<< "$HTML") ||
		die "$0: failed to post announcement for $FILENAME"
	sqlite3 "$DB" "update files set announce_url = '$(escape_string "$ANNOUNCE_URL")' where md5 = '$(escape_string "$MD5")'" ||
		die "$0: failed to set announce_url"
done
