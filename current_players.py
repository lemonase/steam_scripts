#!/usr/bin/env python3
"""
A quick python script to get a game's current player count
"""
import asyncio
import json
import os
import re
import sys
import tempfile
import time

import click
import requests

if sys.version_info[0] < 3:
    raise Exception("Must use Python 3")

# API ENDPOINTS
BASE_URL = "https://api.steampowered.com/"
APP_LIST_URL = BASE_URL + "ISteamApps/GetAppList/v2/"
PLAYER_COUNT_URL = BASE_URL + "ISteamUserStats/GetNumberOfCurrentPlayers/v1/"

# LOCAL FILES
TEMP_DATA_DIR = os.path.join(tempfile.gettempdir(), "steam_scripts", "data")
APP_LIST_FILE = os.path.join(TEMP_DATA_DIR, "app_list.json")

PRINT_LIST = False


def get_app_list():
    """ Save app catalog as app_list.json """
    res = requests.get(APP_LIST_URL)

    res.raise_for_status()
    while res.json() is None:
        time.sleep(1)
        res = requests.get(APP_LIST_URL)

    with open(APP_LIST_FILE, "w", encoding="utf-8") as out_file:
        out_file.write(res.text)


async def get_player_counts(app_ids, app_players):
    """ Asynchronously request player count from a list of app_ids """
    loop = asyncio.get_event_loop()
    futures = []

    for app_id in app_ids:
        futures.append(loop.run_in_executor(None, requests.get,
                                            PLAYER_COUNT_URL + "?appid=" + str(app_id)))

    for response in await asyncio.gather(*futures):
        try:
            app_players.append(response.json()["response"]["player_count"])
        except KeyError:
            app_players.append(0)


def get_apps_info(search_string):
    """
    Search app_list for the search_string and return relevant data in a tuple
    with 3 members
     """
    with open(APP_LIST_FILE, "r", encoding="utf-8") as list_file:
        json_dict = json.loads(list_file.read())
        app_list = json_dict["applist"]["apps"]

        # initialize parallel lists
        found_app_ids = []
        found_app_names = []
        found_app_players = []

        # create regular expression from search string
        pattern = re.compile(re.escape(search_string.lower()))

        for game_dict in app_list:
            app_id = game_dict["appid"]
            app_name = game_dict["name"]

            if pattern.search(app_name.lower()):
                found_app_ids.append(app_id)
                found_app_names.append(app_name)

        print("Number of Apps Matching Search:", len(found_app_ids))

    # request players asynchronously from steam api
    if sys.version_info[1] >= 7:
        asyncio.run(get_player_counts(
            found_app_ids, found_app_players))
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            get_player_counts(found_app_ids, found_app_players))

    return (found_app_ids, found_app_names, found_app_players)


def print_player_table(found_app_ids, found_app_names, found_app_players, num_rows):
    """ Print table of player stats """
    if not found_app_ids:
        print("No App ID's found with search term", file=sys.stderr)
        sys.exit()
    elif not found_app_names:
        print("No App Names found with search term", file=sys.stderr)
        sys.exit()

    # zip lists for sorting
    zipped = zip(found_app_players, found_app_ids, found_app_names)
    zipped = sorted(zipped)

    # convert back to lists
    found_app_ids = [i for (p, i, n) in zipped]
    found_app_names = [n for (p, i, n) in zipped]
    found_app_players = [p for (p, i, n) in zipped]

    display_app_ids = []
    display_app_names = []
    display_app_players = []

    for n in range(len(found_app_ids)):
        if n >= num_rows:
            break
        display_app_ids.append(found_app_ids.pop())
        display_app_names.append(found_app_names.pop())
        display_app_players.append(found_app_players.pop())

    print("Number of Apps Displayed:", num_rows, end="")
    print(" (use -n or --num-rows to show more)")

    w = int(os.get_terminal_size().columns)

    if (PRINT_LIST == True):
        # print in list format
        print("-" * int(w / 3))
        for id, name, players in zip(display_app_ids, display_app_names, display_app_players):
            print("{:10}{id}\n{:10}{name}\n{:10}{players}".format(
                "App ID:", "Name:", "Players:",
                id=id, name=name, players=players))
            print("-" * int(w / 3))
    else:
        # print in table format
        longest_name_width = len(max(display_app_names, key=len))
        # make sure the longest name is not more than 1/3 of the screen width
        if longest_name_width > int(w / 3):
            longest_name_width = int(w / 3)

        # header formatting
        header = "| {id:<10} | {name:<{mid_space}} | {players:<10} |".format(
            id="ID", name="App Name", players="Players", mid_space=longest_name_width)

        # print out table header
        print("-" * len(header))
        print(header)
        print("-" * len(header))

        # print rows
        for id, name, players in zip(display_app_ids, display_app_names, display_app_players):
            row = "| {id:<10} | {name:<{mid_space}} | {players:<10} |".format(
                id=id, name=name[:longest_name_width], players=players, mid_space=longest_name_width)
            print(row)

        # print out table header again (for long output)
        print("-" * len(header))
        print(header)
        print("-" * len(header))


@click.command()
@click.option('--clear-cache', "-c", is_flag=True, required=False, help="Clears the cached appid file")
@click.option("--list-format", "-l", is_flag=True, required=False, help="Output a list instead of a table")
@click.option("--num-rows", "-n", type=click.INT, default=10, required=False)
@click.argument("query")
def main(clear_cache, list_format, num_rows, query):
    if clear_cache:
        os.removedirs(TEMP_DATA_DIR)

    if not os.path.exists(TEMP_DATA_DIR):
        os.makedirs(TEMP_DATA_DIR, exist_ok=True)

    if not os.path.exists(APP_LIST_FILE):
        get_app_list()

    if list_format:
        global PRINT_LIST
        PRINT_LIST = True

    apps_info = get_apps_info(query)
    print_player_table(apps_info[0], apps_info[1], apps_info[2], num_rows)


if __name__ == "__main__":
    main()
