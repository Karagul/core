import sys
from os import path

sys.path.append(path.dirname(path.abspath(__file__)))

from apps.bot.telegram.bot_commands import start, help, tokensale, coins, poloniex, price, exchange, sma

####### EXAMPLE TEST COMMANDS #######
from apps.bot.telegram.utilities import telegram_command


@telegram_command("hello", pass_args=False)
def hello():
    return "hello"


@telegram_command('echo', pass_args=True)
def echo(args):
    return ' '.join(args)


####### EXAMPLE TEST COMMANDS #######


# UKNOWNN COMMAND - CATCHES ALL ELSE
def unknown_command(bot, update):
    """ Unknow command """
    bot.send_message(chat_id=update.message.chat_id,
                     text="Sorry, I didn't understand that command.")


public_commands = [

    start.start,
    help.help_command_list,

    # CONFIG COMMANDS
    coins.coins,

    # INFO COMMANDS
    price.price,

    # TA COMMANDS
    sma.sma,
    # rsi.rsi,

]

commands = public_commands + [

    # TEST EXAMPLE COMMANDS
    hello,
    echo,

]