from aiogram.fsm.state import State, StatesGroup


class ConnectStates(StatesGroup):
    waiting_username = State()
