import base64, hashlib, json, requests


ARWEAVE_HOST = "https://arweave.net"
HEADER_START = 32
MIN_BINARY_SIZE = 80
MAX_TAG_BYTES = 4096
SIG_TYPES = {
    "ARWEAVE": {
        "sigLength": 512,
        "pubLength": 512,
        "sigName": "arweave",
    },
    "ED25519": {
        "sigLength": 64,
        "pubLength": 32,
        "sigName": "ed25519",
    },
    "ETHEREUM": {
        "sigLength": 65,
        "pubLength": 65,
        "sigName": "ethereum",
    },
    "SOLANA": {
        "sigLength": 64,
        "pubLength": 32,
        "sigName": "solana",
    },
    "INJECTEDAPTOS": {
        "sigLength": 64,
        "pubLength": 32,
        "sigName": "injectedAptos",
    },
    "MULTIAPTOS": {
        "sigLength": 64 * 32 + 4,
        "pubLength": 32 * 32 + 1,
        "sigName": "multiAptos",
    },
    "TYPEDETHEREUM": {
        "sigLength": 65,
        "pubLength": 42,
        "sigName": "typedEthereum",
    }
}



class BundlrTags:
    def __init__(self, buf, pos=0):
        self.buf = buf
        self.pos = pos

    def read_long(self):
        n = 0
        k = 0
        buf = self.buf
        while True:
            b = buf[self.pos]
            self.pos += 1
            h = b & 0x80
            n |= (b & 0x7F) << k
            k += 7
            if not h or k >= 28:
                break

        if h:
            f = n
            fk = 268435456  # 2 ** 28
            while True:
                b = buf[self.pos]
                self.pos += 1
                f += (b & 0x7F) * fk
                fk *= 128
                if not b & 0x80:
                    break

            return (f if f % 2 == 0 else -(f + 1)) / 2

        return (n >> 1) ^ -(n & 1)

    def skip_long(self):
        buf = self.buf;
        while True:
            if not buf[self.pos] & 0x80:
                break
            self.pos += 1

    def read_tags(self):
        val = []
        while True:
            n = self.read_long()
            if n == 0:
                break
            elif n < 0:
                n = -n
                while self.buf[self.pos] & 0x80:
                    self.pos += 1

            while n > 0:
                name = self.read_string()
                value = self.read_string()
                val.append({"name": name, "value": value})
                n -= 1

        return val

    def read_string(self):
        length = self.read_long()
        pos = self.pos
        self.pos += length
        if self.pos > len(self.buf):
            raise ValueError("TAP Position out of range")
        return self.buf[pos : pos + length].decode()


def deserialize_tags(tags_buffer):
    tap = BundlrTags(tags_buffer)
    raw_tags = tap.read_tags()
    tags = {}
    for tag in raw_tags:
        name = tag["name"].lower().replace("-", "_").replace(":", "_")
        tags[name] = tag["value"]
    return tags

def byte_array_to_long(byte_array):
    value = 0
    bytelist = list(range(len(byte_array)-1))
    bytelist.reverse()
    for i in bytelist:
        value = value * 256 + byte_array[i]
    return value

def get_reader(stream):
    for chunk in stream:
        yield chunk

def get_item_count(byte_array):
    return byte_array_to_long(byte_array[:32])

def get_bundle_start(item_count):
    return 32 + 64 * item_count

def get_signature_type(binary):
    signature_config = [None, "ARWEAVE", "ED25519", "ETHEREUM", "SOLANA",
                        "INJECTEDAPTOS", "MULTIAPTOS", "TYPEDETHEREUM"]
    signature_type_val = byte_array_to_long(binary[0:2])
    if signature_type_val > 0 and signature_type_val <= len(signature_config):
        return signature_config[signature_type_val]
    print("Unknown signature type: " + signature_type_val)
    return None

def get_signature_length(signatureType):
    return SIG_TYPES[signatureType]["sigLength"];

def get_raw_signature(binary, signature_length):
    return binary[2:2 + signature_length]

def get_owner_length(signatureType):
    return SIG_TYPES[signatureType]["pubLength"]

def get_raw_owner(binary, signature_length, owner_length):
    raw_owner = binary[2 + signature_length:2 + signature_length + owner_length]
    return base64.urlsafe_b64encode(raw_owner).decode()

def get_ids(binary, item_count):
    ids = []
    for i in range(HEADER_START, HEADER_START + 64 * item_count, 64):
      bundleId = binary[i + 32:i + 64]
      if len(bundleId) == 0:
        print("Invalid bundle, id specified in headers doesn't exist");
      ids += [base64.urlsafe_b64encode(bundleId).rstrip(b"=").decode("utf-8")]
    return ids;

def owner_to_address(owner):
    owner_encoded = base64.urlsafe_b64decode(owner.encode('ascii'))
    owner_digest = hashlib.sha256(owner_encoded).digest()
    return base64.urlsafe_b64encode(owner_digest).decode()

def get_target_start(signature_length, owner_length):
    return 2 + signature_length + owner_length

def get_tags_start(binary, signature_length, owner_length):
    target_start = get_target_start(signature_length, owner_length)
    target_present = binary[target_start] == 1
    tags_start = target_start + (33 if target_present else 1)
    anchor_present = binary[tags_start] == 1
    tags_start += 33 if anchor_present else 1
    return tags_start

def get_tags(binary, signature_length, owner_length):
    tags_start = get_tags_start(binary, signature_length, owner_length)
    target_start = get_target_start(signature_length, owner_length)
    tags_count = byte_array_to_long(binary[tags_start:tags_start + 8]);
    if tags_count == 0:
      return []
    tags_size = byte_array_to_long(binary[tags_start + 8:tags_start + 16]);
    tags = binary[tags_start + 16:tags_start + 16 + tags_size]
    return deserialize_tags(tags);

def get_data_item(binary):
    signatureType = get_signature_type(binary)
    signature_length = get_signature_length(signatureType)
    rawSignature = get_raw_signature(binary, signature_length)
    owner_length = get_owner_length(signatureType)
    raw_owner = get_raw_owner(binary, signature_length, owner_length)
    return {
        "signatureType": signatureType,
        "owner": owner_to_address(raw_owner),
        "tags": get_tags(binary, signature_length, owner_length)
    }

def get_items(binary_data, bundled_in=None, block_height=None, timestamp=None):
    item_count = get_item_count(binary_data)
    items = [None for i in range(item_count)]
    offset = 0
    bundle_start = get_bundle_start(item_count);
    counter = 0
    ids = get_ids(binary_data, item_count)
    for i in range(HEADER_START, HEADER_START + (64 * item_count), 64):
        _offset = byte_array_to_long(binary_data[i:i+32])
        raw_id = byte_array_to_long(binary_data[i+32:i+64])

        if raw_id == 0:
            raise Exception("Invalid bundle, id specified in headers doesn't exist")
        data_item_start = bundle_start + offset
        _bytes = binary_data[data_item_start:data_item_start+_offset]
        offset += _offset
        item = get_data_item(_bytes)
        item["_id"] = ids[counter]
        if bundled_in:
            item["bundled_in"] = bundled_in
        if block_height:
            item["block_height"] = block_height
        if timestamp:
            item["timestamp"] = timestamp
        item["tx_pos"] = counter
        items[counter] = item

        counter += 1

    return items

def unbundl(tx_id, block_height=None, timestamp=None):
    binary_data = requests.get("{}/{}".format(ARWEAVE_HOST, tx_id)).content
    return get_items(
        binary_data,
        bundled_in=tx_id,
        block_height=block_height,
        timestamp=timestamp
    )


contents = unbundl(
    "vheA1irdCdDqgowoJkLcpAAk5J0KDMJpr783eYrx-jg",
    block_height=1230139
)

print(json.dumps(contents, indent=4))
