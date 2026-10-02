import importlib.util


TREX_CLIENT = True

trex_client = importlib.util.find_spec("lbr_trex_client")

if trex_client is None:
    TREX_CLIENT = False
