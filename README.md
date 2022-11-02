# Substrate CLI Tools

SubTools leverages [py-substrate-interface](https://github.com/polkascan/py-substrate-interface) library to provide a
set of useful CLI commands but also to provide a library that can be reused to build your own commands quickly through
a higher level abstraction than the one provided by the main interface

### Monitor events

Cli supports monitoring substrate events as they happen, output supports:

- Filtering by method or event name,
- EVM events on Moonbeam based parachains (only with hardcoded ABI from pre compiles)
- Decoding balances in human-readable form
- Showing identity instead of address when available

An example output is:

```bash
./python -m subtools moonbeam event-watch
#2209779-5:EVM:ParachainStaking.DelegatorBondMore(from="0x4E43490E74A73C2Af17398405DbBcD0Cfc95acf8",evmTransactionIndex="1",candidate="Foundation-01",more="177.00GLMR",candidateBacking="2788107.37GLMR",candidatePoolSize="68/77",candidateRank="17 selected")
#2209785-4:Substrate:Balances.Transfer(from="0xa86aa530f6ccbd854236ee00ace687a29ad1c062",dest="0x95f545e8526c2e69daa61c5827cd0bf37272f5d2",value="21.57GLMR")
#2209788-4:Substrate:ParachainStaking.ExecuteDelegationRequest(from="0xd302002ce4c669b0f99a359776b657263bf92fb1",delegator="0xd302002ce4c669b0f99a359776b657263bf92fb1",candidate="P2P.ORG/2",amount="249.00GLMR",candidateBacking="2869228.27GLMR",candidatePoolSize="68/77",candidateRank="10 selected")
#2209788-7:EVM:ParachainStaking.DelegatorBondMore(from="0x95F545e8526c2E69Daa61c5827Cd0bF37272f5d2",evmTransactionIndex="2",candidate="0xaA795bB2c69B1419c4e0b56706777e9a68bac42b",more="21.00GLMR",candidateBacking="2439957.22GLMR",candidatePoolSize="68/77",candidateRank="68 selected")
```

It should be very easy to reuse the library to create your own filters, here is an example to filter all staking events
in Moonbeam between two given blocks:

```python
from subclient import get_client
from subclient.extrinsics import SubstrateExtrinsicFilter

client = get_client(chain_id="moonbeam")
ex_filter = SubstrateExtrinsicFilter()
ex_filter.method_pattern = 'ParachainStaking'
extrinsics = client.get_extrinsics(start_block=1234, end_block=1236)
for extrinsic in extrinsics:
    if ex_filter.match(extrinsic):
        print(extrinsic)
```

### Dump Block

You can use the tool to check when a block was done, this command accepts also future blocks and for those it will
provide an estimation on when the block will happen, output is JSON

```bash
./python -m subtools moonbeam block --block 2201234
{
  "block": 2201234,
  "block_current": 2210009,
  "delta_seconds": 107055,
  "delta_time": "1 day, 5 hours, 44 minutes and 15 seconds",
  "delta_date": "2022-11-01 03:50:28.198074"
}
```
