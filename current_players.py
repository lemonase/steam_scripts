"""
A quick python script to get a game's current player count
"""
# from concurrent.futures import ThreadPoolExecutor as PoolExecutor
import asyncio
import os
import sys
import json
import requests
from tabulate import tabulate

if sys.version_info[0] < 3:
    raise Exception("Must use Python 3")

# API ENDPOINTS
BASE_URL = "https://api.steampowered.com/"
APP_LIST_URL = BASE_URL + "ISteamApps/GetAppList/v2/"
PLAYER_COUNT_URL = BASE_URL + "ISteamUserStats/GetNumberOfCurrentPlayers/v1/"

# LOCAL FILES
APP_LIST_FILE = "data/app_list.json"


def get_app_list():
    """
    Save app catalog as app_list.json
    """
    res = requests.get(APP_LIST_URL)

    with open(APP_LIST_FILE, "w", encoding="utf-8") as out_file:
        out_file.write(res.text)


async def get_player_counts(app_ids, app_players):
    """
    Asynchronously request player count from a list of app_ids
    """
    loop = asyncio.get_event_loop()

    futures = [
        loop.run_in_executor(None, requests.get,
                             PLAYER_COUNT_URL + "?appid=" + str(app_id))
        for app_id in app_ids
    ]
    for response in await asyncio.gather(*futures):
        try:
            app_players.append(response.json()["response"]["player_count"])
        except KeyError:
            app_players.append(0)


def search_app_list(search_string):
    """
    Search app_list for the search_string and print matches
    """
    with open(APP_LIST_FILE, "r", encoding="utf-8") as list_file:
        json_dict = json.loads(list_file.read())
        app_list = json_dict["applist"]["apps"]

        # initialize parallel lists
        found_app_ids = []
        found_app_names = []
        found_app_players = []

        for game_dict in app_list:
            app_id = game_dict["appid"]
            app_name = game_dict["name"]

            if search_string.lower() in app_name.lower():
                found_app_ids.append(app_id)
                found_app_names.append(app_name)

    # request players asynchronously from steam api
    if sys.version_info[1] >= 7:
        asyncio.run(get_player_counts(found_app_ids, found_app_players))
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            get_player_counts(found_app_ids, found_app_players))

    # print lists with tabulate
    print_player_table(found_app_ids, found_app_names, found_app_players)


def print_player_table(found_app_ids, found_app_names, found_app_players):
    """
    Print table of player stats
    """
    # zip lists for sorting
    zipped = zip(found_app_players, found_app_ids, found_app_names)
    zipped = sorted(zipped)

    # convert back to lists
    found_app_ids = [i for (p, i, n) in zipped]
    found_app_names = [n for (p, i, n) in zipped]
    found_app_players = [p for (p, i, n) in zipped]

    # print out table
    print(
        tabulate(
            {
                "App Id": found_app_ids,
                "App Name": found_app_names,
                "Players": found_app_players
            },
            tablefmt="grid"))


def print_usage():
    """
    Output usage
    """
    print("Usage:\npython3", sys.argv[0], "<name of game>\n")


def main():
    """
    Main function
    """
    try:
        if sys.argv[1] == "-h" or sys.argv[1] == "--help":
            print_usage()
        else:
            # make data dir
            if not os.path.exists("data"):
                os.mkdir("data")

            # download app list
            if not os.path.exists(APP_LIST_FILE):
                get_app_list()

            # search the app list
            for arg in sys.argv:
                search_app_list(arg)

    except IndexError:
        print_usage()


main()
