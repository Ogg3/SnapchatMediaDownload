# SnapchatMediaDownload
A tool to download and decrypt chat media using the file contentManager.db

-i Path to contentManagerDB.db or arroyo.db

-o Output directory where decrypted media will be stored

-k Key to find the correct protobuffer in the database

# How it works
Using a key to to query the database for the wanted media. The protobuffer should contain 1 link and two base64 values. 
The link is used to download a encrypted version of the media and the base64 values are used to decrypt with AES.

# Examples

main -i database.db -o C:\outputpath -k key
