# Simple Unbundler Script for Arweave Bundles
Simple single-file script for quickly unbundling Arweave bundled transactions. For dev/research use

#### What it is
For quickly investigating bundle contents, research on ANS104, or just working with use cases involving read-only bundle tasks.

#### What it's not
This script does not include TX validation and does not create bundles, transactions or any other write-activity -- It is merely read-only.
This is in no way intended for any type of production use.  This is just a simple tool to quickly and programmatically look up the contents of bundles when needed.

### Example usage
No CLI implemented - use the script on its own within your own.

#### Args
*unbundl(tx_id, block_height=None, timestamp=None)*
<dl>
  <dt>tx_id</dt>
  <dd>Arweave transaction ID for the bundled tx</dd>

  <dt>block_height (optional)</dt>
  <dd>block height of the transaction</dd>
  
  <dt>timestamp (optional)</dt>
  <dd>block timestamp of the transaction</dd>
</dl>

```py
contents = unbundl("vheA1irdCdDqgowoJkLcpAAk5J0KDMJpr783eYrx-jg", block_height=1230139)

json.dumps(contents, indent=4)

# Returns >>

# [
#     {
#         "signatureType": "ARWEAVE",
#         "_id": "vklyH0wLm3Wk6QXEU6_IZGhwj1Vt3bKZeqdSpysCpso",
#         "bundled_in": "vheA1irdCdDqgowoJkLcpAAk5J0KDMJpr783eYrx-jg",
#         "block_height": 1230139,
#         "tx_pos": 0
#         "owner": "I-5rWUehEv-MjdK9gFw09RxfSLQX9DIHxG614Wf8qo0=",
#         "tags": {
#             "type": "redstone-oracles",
#             "timestamp": "1690659770",
#             "dataserviceid": "redstone-avalanche-prod",
#             "signeraddress": "0x83cbA8c619fb629b81A65C2e67fE15cf3E3C9747",
#             "datafeedid": "TJ_AVAX_USDC_LP"
#         }
#     },
#   ...
# ]

```
