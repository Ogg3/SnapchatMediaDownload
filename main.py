import os.path
import sys
from Crypto.Cipher import AES
import parse3
import base64
import filetype


def get_strings(proto):
    a = []

    def proto2dict(bin):
        messages = parse3.ParseProto(bin)

        def findString(dicti):
            for k, v in dicti.items():
                if isinstance(v, dict):
                    yield k, v
                    yield from findString(v)
                else:
                    yield k, v

        return findString(messages)

    b = proto2dict(proto)

    for k, v in b:
        if "string" in k:
            a.append(v)

    return a

def get_http(a):
    import unicodedata
    import re

    def slugify(value, allow_unicode=False):
        """
        Taken from https://github.com/django/django/blob/master/django/utils/text.py
        Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
        dashes to single dashes. Remove characters that aren't alphanumerics,
        underscores, or hyphens. Convert to lowercase. Also strip leading and
        trailing whitespace, dashes, and underscores.
        """
        value = str(value)
        if allow_unicode:
            value = unicodedata.normalize('NFKC', value)
        else:
            value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub(r'[^\w\s-]', '', value.lower())
        return re.sub(r'[-\s]+', '-', value).strip('-_')

    http_list = []
    for i in a:
        if "https" in i:
            http_list.append(i)

    if len(http_list) != 1:
        print("Found more than one or no link in the protobuffer!")
        return

    print(f"Found URL, {http_list[0]}")
    filename = slugify(os.path.basename(http_list[0]))

    return filename, http_list[0]

def get_keyiv(a):
    import base64

    def isBase64(sb):
        # Not so accurate but need to weed out "Chat" and "image" that where being accepted
        if sb[-1] == "=":
            try:
                if isinstance(sb, str):
                    # If there's any unicode here, an exception will be thrown and the function will return false
                    sb_bytes = bytes(sb, 'ascii')
                elif isinstance(sb, bytes):
                    sb_bytes = sb
                else:
                    raise ValueError("Argument must be string or bytes")
                return base64.b64encode(base64.b64decode(sb_bytes)) == sb_bytes
            except Exception:
                return False
        else:
            return False

    base64_list = []

    for i in a:
        if isBase64(i):
            base64_list.append(i)

    if len(base64_list) != 2:
        print("Found more than two or no base64 values in the protobuf!")
        print(base64_list)
        return

    key = base64_list [0]
    iv = base64_list[1]

    print("Found key and iv!")
    #print((key, iv))

    return key, iv

def download_file(URL):

    import requests

    response = requests.get(URL)

    return response


def get_protobuffer(filename, key):

    import sqlite3
    res = []

    conn = sqlite3.connect(filename)

    if conn:
        if "contentManager" in filename:
            qr = f"""
            SELECT
            CONTENT_DEFINITION
            FROM CONTENT_OBJECT_TABLE
            WHERE KEY LIKE '%{key}%'
            """

            curs = conn.cursor()

            try:
                curs.execute(qr)
            except:
                qr = qr.replace("KEY", "CONTENT_KEY")

            curs.execute(qr)

            for i in curs.fetchall():
                res.append(i[0])

        elif "arroyo" in filename:
            qr = f"""
            SELECT
            message_content
            FROM conversation_message
            WHERE client_conversation_id LIKE '%{key}%' AND content_type NOT LIKE '1'
            """

            curs = conn.cursor()

            curs.execute(qr)

            for i in curs.fetchall():
                res.append(i[0])

    return res

def decryptFile(enc_data, key, iv, output_path, filename):

    import os

    try:
        key = base64.b64decode(key)
        iv = base64.b64decode(iv)
        aes = AES.new(key, AES.MODE_CBC, iv)
        dec_data = aes.decrypt(enc_data)
    except Exception as e:
        print(f"ERROR when decrypting! {e}")
        return
    print("Decrypted file!")

    kind = filetype.guess(dec_data)
    path = os.path.join(output_path, filename+"."+str(kind.extension))

    with open(path, "wb") as f:
        f.write(dec_data)

    print(f"Wrote file {filename}!")

if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description='chatmediadownload: v1')

    # Point to where snapchat dmp is
    parser.add_argument('-i', '--input_path', required=True, action="store", help='Path to contentManager.db.')
    parser.add_argument('-o', '--output_path', required=True, action="store", help='Output folder path.')
    parser.add_argument('-k', '--content_key', required=True, action="store", help='Key to search for.')

    args = parser.parse_args()

    protlist = get_protobuffer(args.input_path, args.content_key)

    if not protlist:
        print("No result for query!")
        sys.exit(0)
    count = 0
    for i in protlist:
        count += 1
        print(f"Checking protobuffer nr{count}")
        a = get_strings(i)

        httpout = get_http(a)

        if httpout is None:
            continue

        key_iv = get_keyiv(a)

        if key_iv is None:
            continue

        respons = download_file(httpout[1])

        if respons.status_code != 200:
            print(f"Got status code {respons.status_code}")
            continue
        print("Downloaded file!")
        decryptFile(respons.content, key_iv[0], key_iv[1], args.output_path, httpout[0])
        print()
