"""
    Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>
    Copyright: (C) 2020 CESNET
    Licence: GPL-2.0

    Description: This script provides function for DCPro specific FEC control.
"""

import os
import sys
import subprocess


def _get_card_info():
    """
    Detect board and transceiver type
    """
    get_board_cmd = 'nfb-info -q card' # TODO handle differente devices than default (/dev/nfb0) ?
    output = subprocess.run(get_board_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', shell=True)
    if output.returncode != 0:
        output.check_returncode()
        return None

    board = output.stdout.rstrip('\n')

    get_trnscvr_cmd = "nfb-eth -T | grep 'Compliance' | awk -F ' ' '{print $3}' | head -n 1" # TODO handle differente devices than default (/dev/nfb0) ?
    output = subprocess.run(get_trnscvr_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', shell=True)
    if output.returncode != 0:
        output.check_returncode()
        return None

    transceiver = output.stdout.rstrip('\n')

    return {'board': board, 'transceiver': transceiver}


def dcpro_fec_set():
    """
    Set FEC on the card, return True if FEC is turned on or False if FEC is turned off.
    """
    card_info = _get_card_info()

    if not card_info:
        raise RuntimeError("Unable to retrieve card information.")

    if card_info['board'] == 'NFB-200G2QL':
        output = subprocess.run('nfb-eth -P -c "{}" '.format(card_info['transceiver']), stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', shell=True)
        if output.returncode != 0:
            output.check_returncode()
            raise RuntimeError("Unable to set transceiver.")

    return (card_info['board'] == 'NFB-200G2QL' and card_info['transceiver'] == '100GBASE-SR4')

