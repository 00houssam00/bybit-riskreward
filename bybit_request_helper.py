import pybit.exceptions
from pybit import usdt_perpetual
import api_config
import config


def _create_usdt_perpetual_session():
    return usdt_perpetual.HTTP(
        endpoint="https://api.bybit.com",
        api_key=api_config.api_key,
        api_secret=api_config.api_secret)


def place_limit_order(side, price, qty, stop_loss):
    session_auth = _create_usdt_perpetual_session()
    return session_auth.place_active_order(
        symbol="BTCUSDT",
        side=side,
        order_type="Limit",
        qty=round(qty, 3),
        price=price,
        time_in_force=config.time_in_force,
        reduce_only=False,
        close_on_trigger=False,
        stop_loss=stop_loss)


def place_limit_close_by(side, price, qty):
    session_auth = _create_usdt_perpetual_session()
    return session_auth.place_active_order(
        symbol="BTCUSDT",
        side=side,
        order_type="Limit",
        qty=round(qty, 3),
        price=price,
        time_in_force=config.time_in_force,
        reduce_only=True,
        close_on_trigger=False)


def set_leverage(buy_leverage, sell_leverage):
    session_auth = _create_usdt_perpetual_session()

    try:
        session_auth.set_leverage(
            symbol="BTCUSDT",
            buy_leverage=buy_leverage,
            sell_leverage=sell_leverage)

    # This exception is ok, avoid throwing the exception if "leverage is not modified" because
    # it means that the leverage is already set the same and is not updated by out endpoint
    except pybit.exceptions.InvalidRequestError as ex:
        if ex.status_code != 34036 and ex.message != "Leverage not modified":
            raise


def get_current_balance():
    session_auth = _create_usdt_perpetual_session()
    response = session_auth.get_wallet_balance(coin="USDT")
    return response['result']['USDT']['available_balance']


def get_current_position():
    session_auth = _create_usdt_perpetual_session()
    return session_auth.my_position(symbol="BTCUSDT")
