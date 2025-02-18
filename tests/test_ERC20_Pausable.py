import pytest
import asyncio
from starkware.starknet.testing.starknet import Starknet
from starkware.starkware_utils.error_handling import StarkException
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from utils import Signer, uint, str_to_felt, assert_revert

signer = Signer(123456789987654321)


@pytest.fixture(scope='module')
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope='module')
async def token_factory():
    starknet = await Starknet.empty()
    owner = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer.public_key]
    )

    other = await starknet.deploy(
        "contracts/Account.cairo",
        constructor_calldata=[signer.public_key]
    )

    token = await starknet.deploy(
        "contracts/token/ERC20_Pausable.cairo",
        constructor_calldata=[
            str_to_felt("Pausable Token"),
            str_to_felt("PTKN"),
            *uint(1000),
            owner.contract_address,
            owner.contract_address
        ]
    )
    return starknet, token, owner, other


@pytest.mark.asyncio
async def test_constructor(token_factory):
    _, token, owner, _ = token_factory

    execution_info = await token.name().call()
    assert execution_info.result == (str_to_felt("Pausable Token"),)

    execution_info = await token.symbol().call()
    assert execution_info.result == (str_to_felt("PTKN"),)

    execution_info = await token.balanceOf(owner.contract_address).call()
    assert execution_info.result.balance == uint(1000)

    execution_info = await token.paused().call()
    assert execution_info.result.paused == 0


@pytest.mark.asyncio
async def test_pause(token_factory):
    _, token, owner, other = token_factory
    amount = uint(200)

    await signer.send_transaction(owner, token.contract_address, 'pause', [])

    execution_info = await token.paused().call()
    assert execution_info.result.paused == 1

    assert_revert(lambda: signer.send_transaction(
        owner,
        token.contract_address,
        'transfer',
        [other.contract_address, *amount]
    ))

    assert_revert(lambda: signer.send_transaction(
        owner,
        token.contract_address,
        'transferFrom',
        [other.contract_address, other.contract_address, *amount]
    ))

    assert_revert(lambda: signer.send_transaction(
        owner,
        token.contract_address,
        'approve',
        [other.contract_address, *amount]
    ))

    assert_revert(lambda: signer.send_transaction(
        owner,
        token.contract_address,
        'increaseAllowance',
        [other.contract_address, *amount]
    ))

    assert_revert(lambda: signer.send_transaction(
        owner,
        token.contract_address,
        'decreaseAllowance',
        [other.contract_address, *amount]
    ))


@pytest.mark.asyncio
async def test_unpause(token_factory):
    _, token, owner, other = token_factory
    amount = uint(200)

    await signer.send_transaction(owner, token.contract_address, 'unpause', [])
    execution_info = await token.paused().call()
    assert execution_info.result.paused == 0

    success = await signer.send_transaction(
        owner,
        token.contract_address,
        'transfer',
        [other.contract_address, *amount]
    )
    assert success.result.response == [1]  # [1] means true

    success = await signer.send_transaction(
        owner,
        token.contract_address,
        'approve',
        [other.contract_address, *amount]
    )
    assert success.result.response == [1]  # [1] means true

    success = await signer.send_transaction(
        other,
        token.contract_address,
        'transferFrom',
        [owner.contract_address, other.contract_address, *amount]
    )
    assert success.result.response == [1]  # [1] means true

    success = await signer.send_transaction(
        owner,
        token.contract_address,
        'increaseAllowance',
        [other.contract_address, *amount]
    )
    assert success.result.response == [1]  # [1] means true

    success = await signer.send_transaction(
        owner,
        token.contract_address,
        'decreaseAllowance',
        [other.contract_address, *amount]
    )
    assert success.result.response == [1]  # [1] means true


@pytest.mark.asyncio
async def test_only_owner(token_factory):
    _, token, _, other = token_factory

    assert_revert(lambda: signer.send_transaction(
        other, token.contract_address, 'pause', []))

    assert_revert(lambda: signer.send_transaction(
        other, token.contract_address, 'unpause', []))
