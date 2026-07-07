from aiogram.fsm.state import State, StatesGroup


class ConnectStates(StatesGroup):
    waiting_username = State()


class SearchStates(StatesGroup):
    waiting_query = State()


class FollowingStates(StatesGroup):
    waiting_username = State()
