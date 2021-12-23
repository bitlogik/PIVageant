"""Various SSH and openSSH helpers for encoding and decoding"""

import base64


def pack_reply(reply_msg):
    """Add message length header, as per SSH and agent protocol"""
    uintlen = (len(reply_msg)).to_bytes(4, byteorder="big")
    return uintlen + reply_msg


def read_len(buffer):
    """Return the message length header as integer"""
    return int.from_bytes(buffer[:4], "big")


def encode_pubkey(pubkey, identifier, key_blob_id):
    """Pack a public key in the openssh format"""
    return (
        pack_reply(identifier.encode("ascii"))
        + pack_reply(key_blob_id.encode("ascii"))
        + pack_reply(pubkey)
    )


def parse_datasig(data):
    """Parse and validate the data to be signed"""
    # According to RFC4252 7.
    i = 0
    len_part = read_len(data[i:])
    i += 4
    session_id = data[i : i + len_part]
    i += len_part
    if data[i] != 50:
        # SSH_MSG_USERAUTH_REQUEST
        raise Exception("Bad request for user auth")
    i += 1
    len_part = read_len(data[i:])
    i += 4
    username = data[i : i + len_part].decode("utf8")
    i += len_part
    len_part = read_len(data[i:])
    i += 4
    # Service name
    if data[i : i + len_part] != b"ssh-connection":
        raise Exception("Bad data in ssh message")
    i += len_part
    len_part = read_len(data[i:])
    i += 4
    # Authentication Method Name
    if data[i : i + len_part] != b"publickey":
        raise Exception("Bad pubkey in ssh message")
    i += len_part
    if data[i] != 1:
        # check True
        raise Exception("Bad info in ssh message")
    i += 1
    publickey = data[i:]
    return {"session_id": session_id, "username": username, "publickey": publickey}


def decode_ssh(data):
    """Fast decoding of openssh into binary"""
    ssh_data = data.split(" ")[1]
    return base64.b64decode(ssh_data)


def openssh_to_wire(key_openssh):
    """Serialize an RFC4253 OpenSSH public key from text to binary"""
    key_data = key_openssh.split(" ")
    return pack_reply(base64.b64decode(key_data[1])) + pack_reply(
        bytes(key_data[2], "utf8")
    )


def encode_openssh(pubkey_bytes, comment_text):
    """Encode an EC public key into RFC4253 OpenSSH encoding"""
    if len(pubkey_bytes) == 65:
        curve_id = "256"
    elif len(pubkey_bytes) == 97:
        curve_id = "384"
    else:
        raise ValueError("Invalid public key length.")
    key_id = f"ecdsa-sha2-nistp{curve_id}"
    pubkey_enc = encode_pubkey(pubkey_bytes, key_id, "nistp" + curve_id)
    pubkeyb64 = base64.b64encode(pubkey_enc).decode("ascii")
    return f"{key_id} {pubkeyb64} {comment_text}"


def parse_sign_command(sign_cmd, debug):
    """Parse sign query, and extract the data to sign"""
    idseek = 0
    keyblob_len = read_len(sign_cmd)
    idseek += 4
    key_blob = sign_cmd[idseek : idseek + keyblob_len]
    idseek += keyblob_len
    data_len = read_len(sign_cmd[idseek:])
    idseek += 4
    data_tosign = sign_cmd[idseek : idseek + data_len]
    idseek += data_len
    if debug:
        print("Key blob for signature :", key_blob)
        print("Data to sign :", data_tosign)
    if sign_cmd[idseek:] != b"\0\0\0\0":
        raise Exception("Unvalid signature query, must be compliant for ECC.")
    return data_tosign


def decode_sig(sig):
    """DER to packed mpint blob R|S - RFC5656 3.1.2"""
    if sig[0] != 0x30:
        raise Exception("Wrong signature header")
    if sig[2] != 0x02:
        raise Exception("Wrong signature format")
    rlen = sig[3]
    slen = sig[5 + rlen]
    r_bytes = sig[4 : 4 + rlen]
    s_bytes = sig[6 + rlen : 6 + rlen + slen]
    return pack_reply(r_bytes) + pack_reply(s_bytes)
