import json
import math
import config
import bybit_request_helper

available_balance = -1


def print_break_line():
    print("======================================================")


def print_console(result):
    print(json.dumps(result, indent=1))


def calculate_position(entry_price, stop_loss):
    global available_balance
    return (float(get_user_current_risk()) * float(entry_price)) / math.fabs(float(entry_price) - float(stop_loss))


def calculate_leverage(position):
    global available_balance
    return math.ceil(float(position) / float(available_balance))


def calculate_quantity(entry_price, stop_loss):
    return float(get_user_current_risk()) / math.fabs(float(entry_price) - float(stop_loss))


def process_command_order(commands, side):

    if len(commands) == 2:
        stop_loss = commands[1]
        latest_bar = bybit_request_helper.get_latest_bar_info()
        latest_price = latest_bar['result'][0]['high']['close']
        if side == 'Buy':
            entry_price = latest_bar['result'][0]['high'] + 20
        elif side == 'Sell':
            entry_price = latest_bar['result'][0]['low'] - 20
    elif len(commands) == 3:
        entry_price = commands[1]
        stop_loss = commands[2]
        latest_price = bybit_request_helper.get_current_price()

    position = calculate_position(entry_price, stop_loss)
    leverage = calculate_leverage(position)
    qty = calculate_quantity(entry_price, stop_loss)
    try:
        bybit_request_helper.set_leverage(leverage, leverage)

        if side == 'Buy':
            if float(entry_price) > float(latest_price):
                bybit_request_helper.place_limit_conditional_order(side, entry_price, qty, stop_loss)
            else:
                bybit_request_helper.place_limit_order(side, entry_price, qty, stop_loss)
        elif side == 'Sell':
            if float(entry_price) < float(latest_price):
                bybit_request_helper.place_limit_conditional_order(side, entry_price, qty, stop_loss)
            else:
                bybit_request_helper.place_limit_order(side, entry_price, qty, stop_loss)
        else:
            print(">> Order Failed << side not defined")

    except Exception as ex:
        print(f">> Order Failed << [entry: {entry_price} / stopLoss: {stop_loss} / position: {position} / leverage: {leverage} / qty: {qty}]")
        print(ex)


def process_command_closeby(commands):
    if len(commands) == 1:
        closeby_riskreward()
    else:
        closeby_price(commands[1])


def closeby_riskreward():
    my_position = bybit_request_helper.get_current_position()
    position_state = get_current_position_state(my_position)
    entry_price = my_position['result'][position_state['position_index']]['entry_price']
    stop_loss = my_position['result'][position_state['position_index']]['stop_loss']
    fee = my_position['result'][position_state['position_index']]['occ_closing_fee']

    if config.adapt_risk_reward_to_include_fees == "yes":
        risk_reward_after_fees = config.risk_reward + (float(fee) / float(get_user_current_risk()))
    elif config.adapt_risk_reward_to_include_fees == "no":
        risk_reward_after_fees = config.risk_reward

    if risk_reward_after_fees:
        close_by_price_diff = (math.fabs(float(entry_price) - float(stop_loss)) / float(entry_price)) * float(risk_reward_after_fees)

        if position_state['side'] == 'Buy':
            close_by_price = entry_price - (close_by_price_diff * entry_price)
        elif position_state['side'] == 'Sell':
            close_by_price = entry_price + (close_by_price_diff * entry_price)

        if close_by_price:
            bybit_request_helper.place_limit_close_by(
                position_state['side'],
                int(close_by_price),
                my_position['result'][position_state['position_index']]['size'])
        else:
            print(">> Closeby Failed <<")
    else:
        print(">> Error while calculating risk reward <<")


def closeby_price(price):
    my_position = bybit_request_helper.get_current_position()
    position_state = get_current_position_state(my_position)
    bybit_request_helper.place_limit_close_by(
        position_state['side'],
        price,
        my_position['result'][position_state['position_index']]['size'])


def get_current_position_state(position):
    if position['result'][0]['position_value'] > 0:
        return {
            'position_index': 0,
            'side': 'Sell'}
    elif position['result'][1]['position_value'] > 0:
        return {
            'position_index': 1,
            'side': 'Buy'}
    else:
        return None


def show_open_position():
    my_position = bybit_request_helper.get_current_position()
    position_state = get_current_position_state(my_position)

    try:
        if position_state:
            side = my_position['result'][position_state['position_index']]['side']
            realised_pnl = my_position['result'][position_state['position_index']]['realised_pnl']
            unrealised_pnl = my_position['result'][position_state['position_index']]['unrealised_pnl']
            print(f"position: [side: {side} / realised_pnl: {realised_pnl} / unrealised_pnl: {unrealised_pnl}]")
        else:
            print("position: No Open Position")
    except:
        pass


def show_user_current_risk():
    global available_balance

    match config.risk_unit:
        case 'AMOUNT':
            print(f"Your current risk is: {config.risk}$")
        case 'PERCENTAGE':
            print(f"Your current risk is: {config.risk}% -> {get_user_current_risk()}$")


def get_user_current_risk():
    match config.risk_unit:
        case 'AMOUNT':
            return {config.risk}
        case 'PERCENTAGE':
            return (config.risk / 100) * available_balance


while True:
    print_break_line()

    # Show current balance
    available_balance = bybit_request_helper.get_current_balance()
    print(f"Your current available balance is {available_balance}$")

    show_user_current_risk()

    # Show current user risk to reward ratio
    risk = get_user_current_risk();
    print(f"Your current risk to reward is: 1:{config.risk_reward} -> "
          f"{risk}$:{risk * float(config.risk_reward)}$")

    # Show open position if exist
    show_open_position()

    # Get command str from user
    user_command = input('>> ')
    commands = user_command.split()

    # Process command
    if commands:
        match commands[0]:
            case 'long':
                process_command_order(commands, 'Buy')
            case 'short':
                process_command_order(commands, 'Sell')
            case 'closeby':
                process_command_closeby(commands)
