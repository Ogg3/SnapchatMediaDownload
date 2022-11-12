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

    http_list = []
    for i in a:
        if "https" in i:
            http_list.append(i)

    if len(http_list) != 1:
        print("Found more than one or no link in the protobuffer!")
        print("Exiting")
        sys.exit(0)

    print(f"Found URL, {http_list[0]}")
    filename = os.path.basename(http_list[0])

    return filename, http_list[0]

def get_keyiv(a):

    base64_list = []

    for i in a:
        if len(i) > 5:
            try:
                base64.b64decode(i)
                base64_list.append(i)
            except:
                pass

    if len(base64_list) != 2:
        print("Found more than two or no base64 values in the protobuf!")
        print(base64_list)
        print("Exiting")
        sys.exit(0)

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
            qr.replace("KEY", "CONTENT_KEY")

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

    kind = filetype.guess(dec_data)
    path = os.path.join(output_path, filename+"."+str(kind.extension))

    with open(path, "wb") as f:
        f.write(dec_data)

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

        filename, b = get_http(a)

        key, iv = get_keyiv(a)

        respons = download_file(b)

        if respons.status_code != 200:
            print(f"Got status code {respons.status_code}")
            continue
        decryptFile(respons.content, key, iv, args.output_path, filename)