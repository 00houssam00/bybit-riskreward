import json
import math
import config
import bybit_request_helper

available_balance = -1
risk = config.default_risk
risk_reward = config.default_risk_reward


def print_break_line():
    print("======================================================")


def print_console(result):
    print(json.dumps(result, indent=1))


def calculate_position(entry_price, stop_loss):
    global risk, available_balance
    return (float(risk) * float(entry_price)) / math.fabs(float(entry_price) - float(stop_loss))


def calculate_leverage(position):
    global available_balance
    return math.ceil(float(position) / float(available_balance)) + 2


def calculate_quantity(entry_price, stop_loss):
    global risk
    return float(risk) / math.fabs(float(entry_price) - float(stop_loss))


def process_command_set(commands):
    if commands[1] == 'risk':
        global risk
        risk = commands[2]
    elif commands[1] == 'riskreward':
        global risk_reward
        risk_reward = commands[2]


def process_command_order(commands, side):
    try:
        entry_price = commands[1]
        stop_loss = commands[2]
        position = calculate_position(entry_price, stop_loss)
        leverage = calculate_leverage(position)
        qty = calculate_quantity(entry_price, stop_loss)
        bybit_request_helper.set_leverage(leverage, leverage)
        bybit_request_helper.place_limit_order(side, entry_price, qty, stop_loss)
    except:
        print(">> Order Failed <<")


def process_command_closeby(commands):
    if len(commands) == 1:
        closeby_riskreward()
    else:
        closeby_price(commands[1])


def closeby_riskreward():
    global risk_reward
    my_position = bybit_request_helper.get_current_position()
    position_state = get_current_position_state(my_position)
    entry_price = my_position['result'][position_state['position_index']]['entry_price']
    stop_loss = my_position['result'][position_state['position_index']]['stop_loss']
    fee = my_position['result'][position_state['position_index']]['occ_closing_fee']

    if config.adapt_risk_reward_to_include_fees == "yes":
        risk_reward_after_fees = risk_reward + (float(fee) / float(risk))
    elif config.adapt_risk_reward_to_include_fees == "no":
        risk_reward_after_fees = risk_reward

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


def process_command_position():
    my_position = bybit_request_helper.get_current_position()
    position_state = get_current_position_state(my_position)

    try:
        if position_state:
            side = my_position['result'][position_state['position_index']]['side']
            realised_pnl = my_position['result'][position_state['position_index']]['realised_pnl']
            unrealised_pnl = my_position['result'][position_state['position_index']]['unrealised_pnl']
            print(f"side -> {side} realised_pnl -> {realised_pnl} - unrealised_pnl {unrealised_pnl}")
        else:
            print(">> No Open Position")
    except:
        pass


while True:
    print_break_line()

    # Show current balance
    available_balance = bybit_request_helper.get_current_balance()
    print(f"Your current available balance is {available_balance}$")

    # Show current user risk
    print(f"Your current risk is: {risk}$")

    # Show current user risk to reward ratio
    print(f"Your current risk to reward is: {risk_reward} -> {float(risk) * float(risk_reward)}$")

    # Get command str from user
    user_command = input('>> ')
    commands = user_command.split()

    # Process command
    if commands:
        match commands[0]:
            case 'set':
                process_command_set(commands)
            case 'long':
                process_command_order(commands, 'Buy')
            case 'short':
                process_command_order(commands, 'Sell')
            case 'closeby':
                process_command_closeby(commands)
            case 'position':
                process_command_position()
