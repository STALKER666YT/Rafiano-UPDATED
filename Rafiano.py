"""
8888888b.            .d888 d8b
888   Y88b          d88P"  Y8P
888    888          888
888   d88P  8888b.  888888 888  8888b.  88888b.   .d88b.
8888888P"      "88b 888    888     "88b 888 "88b d88""88b
888 T88b   .d888888 888    888 .d888888 888  888 888  888
888  T88b  888  888 888    888 888  888 888  888 Y88..88P
888   T88b "Y888888 888    888 "Y888888 888  888  "Y88P"
"""


import configparser
import curses
import os
import re
import shutil
import time

from pynput.keyboard import Controller, Key
from typing import Dict, List
from collections import defaultdict

CONFIG_FILE_PATH = "config.ini"


def create_default_config():
    """
    Creates a default configuration file with default values.
    """
    config = configparser.ConfigParser()
    config['DEFAULT'] = {'notesheet_paths': 'Notesheet'}
    with open(CONFIG_FILE_PATH, 'w') as configfile:
        config.write(configfile)


def load_config():
    """
    Loads configuration from the config file.
    """
    if not os.path.exists(CONFIG_FILE_PATH):
        create_default_config()

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)
    return config


def validate_notesheet(notesheet: str) -> bool:
    """
    Validates the notesheet by checking if it contains only valid characters.

    Args:
        notesheet (str): The notesheet to be validated.

    Returns:
        bool: True if the notesheet contains only valid characters, False otherwise.

    Raises:
        None: This function does not raise any exceptions.
    """
    # Split the notesheet string into individual lines
    notesheet = notesheet.split("\n")

    # Loop through each line of the notesheet
    for notesheet_line in notesheet:

        # Ignore comment lines, empty lines and song header lines
        if notesheet_line.startswith("#") or notesheet_line == "" or notesheet_line.startswith("|"):
            continue

        # If the line contains invalid characters, return False
        if not bool(re.match(r'([0-9.\s|]|SH|SP)*$', notesheet_line.upper())):
            return False

    # If all lines contain valid characters, return True
    return True



def parse_file(file_path: str) -> List[Dict]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            notesheet_data = f.read()
    except:
        return []

    all_songs = []
    read_notesheet = False
    current_song = {}
    current_song_notes = []
    start_line = 0

    # Validate the notesheet before parsing
    if not validate_notesheet(notesheet_data):
        print(f"Skipping invalid notesheet: {file_path}")
        return []

    # Split the notesheet string into individual lines
    notesheet_lines = notesheet_data.split("\n")

    # Loop through each line of the notesheet
    for i, notesheet_line in enumerate(notesheet_lines):
        # Ignore comment lines and empty lines
        if notesheet_line == "" or notesheet_line.startswith("#"):
            continue

        # If a song header line is found, start a new song
        elif notesheet_line.startswith("|"):
            # If already read song information, append to list
            if read_notesheet:
                current_song["notes"] = current_song_notes
                current_song["Lines"] = [start_line, i]
                all_songs.append(current_song)

            # Set variables for new song
            read_notesheet = True
            song_info = notesheet_line.split("|")
            current_song = {"name": song_info[1], "creator": song_info[2], "version": song_info[3]}
            current_song_notes = []
            start_line = i

        # If reading notes, add note information to current song
        elif read_notesheet:
            # Parse note information
            split_notes = notesheet_line.split(" ")
            if split_notes[1].upper() == "":
                modifier_key = Key.up
            elif split_notes[1].upper() == "SH":
                modifier_key = Key.shift
            elif split_notes[1].upper() == "SP":
                modifier_key = Key.space
            else:
                raise Exception("Invalid modifier value")

            try:
                press_time = float(split_notes[2])
                release_time = float(split_notes[3])
            except ValueError:
                raise Exception("Invalid press/release time value")

            # Add note information to song
            current_song_notes.append({"notes": split_notes[0].split("|"),
                                       "modifier": modifier_key,
                                       "press_time": press_time,
                                       "release_time": release_time
                                       })

    # Add the last song to the list if one was being read
    if read_notesheet:
        current_song["notes"] = current_song_notes
        current_song["Lines"] = [start_line, len(notesheet_lines)]
        all_songs.append(current_song)

    return all_songs

def parse_notesheet_file(filepath: str) -> List[Dict]:
    """
    Parses a notesheet file or files in a folder and returns a list of dictionaries, where each dictionary represents a song with its name, creator, and notes.

    Args:
        filepath (str): The path to the notesheet file or folder to be parsed.

    Returns:
        list: A list of dictionaries, where each dictionary represents a song with its name, creator, notes, and line numbers.

    Raises:
        Exception: If the notesheet contains invalid modifier, release/press time values, or invalid characters.
    """
    all_songs = []

    if os.path.isdir(filepath):
        for filename in os.listdir(filepath):
            file_path = os.path.join(filepath, filename)
            if os.path.isfile(file_path):
                all_songs.extend(parse_file(file_path))
    elif os.path.isfile(filepath):
        all_songs.extend(parse_file(filepath))
    else:
        raise Exception("Provided path is neither a file nor a directory")

    return all_songs


from collections import defaultdict

def Notesheet_easy_convert(data):
    """
    Process the input data to extract actions with their corresponding times,
    combining actions for press and release times if applicable, and outputting
    a list of lists where each sublist contains a time followed by the actions
    performed at that time.

    Args:
    - data (list of dicts): A list of dictionaries where each dictionary contains
      keys 'Note', 'press_time', and 'release_time'.

    Returns:
    - list of lists: A list where each sublist contains a time followed by the
      actions performed at that time, sorted by time.
    """

    result = []

    # Process each entry in the data
    for entry in data:
        press_time = entry["press_time"]
        release_time = entry["release_time"]
        notes = entry["notes"]

        # Add notes with press time
        for note in notes:
            result.append((press_time, note))

        # Add notes with release time if different from press time
        if press_time != release_time:
            for note in notes:
                result.append((release_time, note))

    # Sort the result based on time (first element of each tuple)
    result.sort()

    # Initialize output list
    output_list = []

    # Use defaultdict to collect notes by time
    notes_by_time = defaultdict(list)

    for time, note in result:
        notes_by_time[time].append(note)

    # Convert defaultdict to the final output format
    output_list = [[time] + notes_by_time[time] for time in sorted(notes_by_time)]

    return output_list



def player_v1(song_notes: List[Dict]) -> bool:
    """
    Plays the notes of a given song by simulating key presses based on relative timings.

    Args:
        song_notes (List[Dict]): A list of dictionaries containing information about the song to be played.

    Returns:
        bool: True, if the song was played successfully.
    """
    # Create a keyboard controller object to simulate key presses
    keyboard = Controller()

    # Iterate through each note in the song notes dictionary
    for note_dic in song_notes:
        # Press the modifier key for the current note
        keyboard.press(note_dic["modifier"])
        # Press each note in the current note's list of notes
        for note in note_dic["notes"]:
            keyboard.press(note)
        # Wait for the specified press time
        time.sleep(note_dic["press_time"])
        # Release each note in the current note's list of notes
        for note in note_dic["notes"]:
            keyboard.release(note)
        # Release the modifier key for the current note
        keyboard.release(note_dic["modifier"])
        # Wait for the specified release time
        time.sleep(note_dic["release_time"])

    # Return True to indicate that the song was played successfully
    return True

def player_v2(song_notes: List[Dict]) -> bool:
    """
    Plays the notes of a given song by simulating key presses based on absolute timings.

    Args:
        song_notes (List[Dict]): A list of dictionaries containing information about the song to be played.

    Returns:
        bool: True, if the song was played successfully.
    """
    keyboard = Controller()
    PressRelease = {Key.shift: False, Key.space: False, "1": False, "2": False, "3": False,
                    "4": False, "5": False, "6": False, "7": False, "8": False,
                    "9": False, "0": False}

    songNotes = Notesheet_easy_convert(song_notes)  # Assuming you have a function to convert song_notes

    start_time = time.time()
    for notes in songNotes:
        while time.time() - start_time < notes[0]:
            time.sleep(0.001)  # Adjust sleep time to avoid excessive CPU usage

        for note in notes[1:]:
            if PressRelease[note]:
                keyboard.release(note)
                PressRelease[note] = False
            else:
                keyboard.press(note)
                PressRelease[note] = True


    return True  # Return True if the song was played successfully

def player(song_notes: List[Dict], version: str) -> bool:
    """
    Plays the notes of a given song by simulating key presses.

    Args:
        song_notes (List[Dict]): A list of dictionaries containing information about the song to be played.
        version (str): The version of the player to use ("1.0" for relative timing, "2.0" for absolute timing).

    Returns:
        bool: True, if the song was played successfully.
    """
    if version == "1.0":
        return player_v1(song_notes)
    elif version == "2.0":
        return player_v2(song_notes)
    else:
        raise ValueError("Unsupported version")


def play_songs_menu(stdscr, notesheet_data):
    curses.curs_set(0)  # Hide the cursor
    stdscr.clear()
    stdscr.refresh()

    menu_indicator = ">>>"
    current_option = 0

    while True:
        title: str = 'Rafiano | Song Selection | Use up and down arrows to navigate'

        song_options = [x["name"] + " by " + x["creator"]+ " " + x["version"] for x in notesheet_data] + ["Go Back"]

        stdscr.addstr(1, 1, title, curses.A_BOLD)

        for i, option in enumerate(song_options):
            if i == current_option:
                stdscr.addstr(i + 3, 1, menu_indicator + " " + option, curses.A_REVERSE)
            else:
                stdscr.addstr(i + 3, 1, "   " + option)

        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP:
            current_option = (current_option - 1) % len(song_options)
        elif key == curses.KEY_DOWN:
            current_option = (current_option + 1) % len(song_options)
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_option == len(song_options) - 1:  # Exit option selected
                break
            else:
                stdscr.addstr(10, 1,
                              f"Playing : {notesheet_data[current_option]['name']} by: {notesheet_data[current_option]['creator']}")
                stdscr.refresh()
                for i in range(5, 0, -1):
                    stdscr.addstr(11, 1, str(i))
                    stdscr.refresh()
                    time.sleep(1)
                player(notesheet_data[current_option]["notes"], notesheet_data[current_option]['version'])


def remove_song_from_notesheet(notesheet_filepath: str, song_name: str):
    """
    Removes a song from the notesheet by its name.

    Args:
        notesheet_filepath (str): The file path to the notesheet.
        song_name (str): The name of the song to be removed.

    Returns:
        None
    """
    # Parse the notesheet file to get song metadata
    notesheet_data = parse_notesheet_file(notesheet_filepath)

    # Initialize variables to track the lines corresponding to the song to be removed
    start_line = None
    end_line = None

    # Find the start and end lines of the song to be removed
    for song in notesheet_data:
        if song["name"] == song_name:
            start_line, end_line = song["Lines"]
            break

    # If the song was found, remove its lines from the notesheet file
    if start_line is not None and end_line is not None:
        # Read the contents of the notesheet file
        with open(notesheet_filepath, 'r', encoding='utf-8') as f:
            notesheet_contents = f.readlines()

        # Remove the lines corresponding to the song to be deleted
        del notesheet_contents[start_line:end_line]

        # Rewrite the notesheet file with the updated contents
        with open(notesheet_filepath, 'w', encoding='utf-8') as f:
            f.writelines(notesheet_contents)


def combine_notesheets(master_filepath: str, secondary_filepath: str, output_filepath: str):
    """
    Combines two notesheets into one, retaining the master notesheet's data
    in case of duplicate song names.

    Args:
        master_filepath (str): The file path to the master notesheet.
        secondary_filepath (str): The file path to the secondary notesheet.
        output_filepath (str): The file path to save the combined notesheet.

    Returns:
        None
    """
    # Read raw lines from master and secondary notesheets
    with open(master_filepath, 'r', encoding='utf-8') as f:
        master_lines = f.readlines()

    with open(secondary_filepath, 'r', encoding='utf-8') as f:
        secondary_lines = f.readlines()

    # Parse the notesheets to get song metadata
    master_data = parse_notesheet_file(master_filepath)
    secondary_data = parse_notesheet_file(secondary_filepath)

    # Dictionary to track song names in the master notesheet
    master_songs = {song["name"]: song for song in master_data}

    # Combine the master notesheet lines with non-duplicate songs from the secondary notesheet
    combined_lines = master_lines.copy()

    for song in secondary_data:
        if song["name"] not in master_songs:
            start_line, end_line = song["Lines"]
            if combined_lines[-1].strip() != "":  # Add a newline if the last line is not empty
                combined_lines.append('\n')
            combined_lines.extend(secondary_lines[start_line:end_line])

    # Write combined notesheet lines to the output file
    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.writelines(combined_lines)


def edit_notesheet_menu(stdscr):
    options = ["Load Song (TODO)", "Combine Notesheets", "Remove Song", "Export Notesheet", "Add MIDI File", "Go Back"]
    current_option = 0

    config = load_config()  # Load the configuration
    master_path = config.get('DEFAULT', 'notesheet_paths')  # Get the notesheet path from the configuration

    while True:
        stdscr.clear()
        for i, option in enumerate(options):
            if i == current_option:
                stdscr.addstr(i + 1, 1, option, curses.A_REVERSE)
            else:
                stdscr.addstr(i + 1, 1, option)

        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP:
            current_option = (current_option - 1) % len(options)
        elif key == curses.KEY_DOWN:
            current_option = (current_option + 1) % len(options)
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_option == 0:
                # Load Song (TODO)
                stdscr.addstr(len(options) + 3, 1, "This feature is under development.")
                stdscr.refresh()
                stdscr.getch()  # Wait for user input to continue
            elif current_option == 1:
                # Combine Notesheets
                stdscr.addstr(len(options) + 3, 1, f"Master notesheet: {master_path}")
                stdscr.addstr(len(options) + 4, 1, "Enter path to secondary notesheet:")
                stdscr.refresh()
                curses.echo()  # Enable text input
                secondary_path = stdscr.getstr(len(options) + 5, 1).decode(encoding="utf-8")
                curses.noecho()  # Disable text input

                try:
                    combine_notesheets(master_path, secondary_path, master_path)
                    stdscr.addstr(len(options) + 8, 1, "Notesheets combined successfully!")
                    stdscr.refresh()
                    stdscr.getch()  # Wait for user input to continue
                except Exception as e:
                    stdscr.addstr(len(options) + 8, 1, f"Error combining notesheets: {str(e)}")
                    stdscr.refresh()
                    stdscr.getch()  # Wait for user input to continue
            elif current_option == 2:
                # Remove Song
                notesheet_data = parse_notesheet_file(master_path)
                delete_song_menu(stdscr, notesheet_data, master_path)
            elif current_option == 3:
                # Export Notesheet
                stdscr.addstr(len(options) + 3, 1, "Enter output path for the exported notesheet:")
                stdscr.refresh()
                curses.echo()  # Enable text input
                output_path = stdscr.getstr(len(options) + 4, 1).decode(encoding="utf-8")
                curses.noecho()  # Disable text input
                try:
                    shutil.copyfile(master_path, output_path)
                    stdscr.addstr(len(options) + 5, 1, "Notesheet exported successfully!")
                    stdscr.refresh()
                    stdscr.getch()  # Wait for user input to continue
                except Exception as e:
                    stdscr.addstr(len(options) + 5, 1, f"Error exporting notesheet: {str(e)}")
                    stdscr.refresh()
                    stdscr.getch()  # Wait for user input to continue
            elif current_option == 4:
                # Add MIDI File (TODO)
                stdscr.addstr(len(options) + 3, 1, "This feature is under development.")
                stdscr.refresh()
                stdscr.getch()  # Wait for user input to continue
            elif current_option == 5:
                # Go Back
                return


def delete_song_menu(stdscr, notesheet_data, master_path):
    curses.curs_set(0)  # Hide the cursor
    stdscr.clear()
    stdscr.addstr(1, 1, "Select song to delete:")

    song_options = [song["name"] + " by " + song["creator"] + " " + song["version"] for song in notesheet_data]
    song_options.append("Go Back")  # Add "Go Back" option
    current_option = 0

    while True:
        stdscr.clear()
        stdscr.addstr(1, 1, "Select song to delete:")

        for i, option in enumerate(song_options):
            if i == current_option:
                stdscr.addstr(i + 3, 1, ">>>" + option, curses.A_REVERSE)
            else:
                stdscr.addstr(i + 3, 1, "   " + option)
        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP:
            current_option = (current_option - 1) % len(song_options)
        elif key == curses.KEY_DOWN:
            current_option = (current_option + 1) % len(song_options)
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_option == len(song_options) - 1:  # Go Back option selected
                return False  # Go back to the previous menu
            else:
                confirmation_text = f"Are you sure you want to delete '{notesheet_data[current_option]['name']}'? Type 'Yes!' to confirm: "
                stdscr.addstr(len(song_options) + 3, 1, confirmation_text)
                stdscr.refresh()
                curses.echo()  # Enable text input
                confirmation = stdscr.getstr(len(song_options) + 4, 1).decode(encoding="utf-8")
                curses.noecho()  # Disable text input

                if confirmation.strip() == "Yes!":
                    song_name = notesheet_data[current_option]["name"]
                    remove_song_from_notesheet(master_path, song_name)
                    stdscr.addstr(len(song_options) + 5, 1, f"Song '{song_name}' deleted successfully!")
                    stdscr.refresh()
                    stdscr.getch()  # Wait for user input to continue
                    return True  # Deletion confirmed
                else:
                    stdscr.addstr(len(song_options) + 5, 1, "Deletion canceled!")
                    stdscr.refresh()
                    stdscr.getch()  # Wait for user input to continue
                    return False  # Deletion canceled


def main_menu(stdscr):
    curses.curs_set(0)  # Hide the cursor
    stdscr.clear()
    stdscr.refresh()

    options = ["Play Music", "Edit Notesheet", "Settings", "Exit"]
    current_option = 0

    while True:
        stdscr.clear()
        for i, option in enumerate(options):
            if i == current_option:
                stdscr.addstr(i + 1, 1, option, curses.A_REVERSE)
            else:
                stdscr.addstr(i + 1, 1, option)

        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP:
            current_option = (current_option - 1) % len(options)
        elif key == curses.KEY_DOWN:
            current_option = (current_option + 1) % len(options)
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_option == 0:
                # Play Music
                config = load_config()
                notesheet_paths = config.get('DEFAULT', 'notesheet_paths')
                notesheet_data = parse_notesheet_file(notesheet_paths)
                play_songs_menu(stdscr, notesheet_data)
            elif current_option == 1:
                # Edit Notesheet
                edit_notesheet_menu(stdscr)
            elif current_option == 2:
                # Settings
                settings_menu(stdscr)
            elif current_option == 3:
                # Exit
                break


def settings_menu(stdscr):
    options = ["Change Notesheet Path", "Reset", "Go Back"]
    current_option = 0

    while True:
        stdscr.clear()
        for i, option in enumerate(options):
            if i == current_option:
                stdscr.addstr(i + 1, 1, option, curses.A_REVERSE)
                # Display current notesheet path to the right of "Change Notesheet Path" option
                if i == 0:
                    config = load_config()
                    notesheet_path = config.get('DEFAULT', 'notesheet_paths')
                    stdscr.addstr(i + 1, len(option) + 3, f"Notesheet Path: {notesheet_path}")
            else:
                stdscr.addstr(i + 1, 1, option)

        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP:
            current_option = (current_option - 1) % len(options)
        elif key == curses.KEY_DOWN:
            current_option = (current_option + 1) % len(options)
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_option == 0:
                # Change Notesheet Path
                stdscr.addstr(3, 1, "Enter new notesheet path:")
                stdscr.refresh()
                curses.echo()  # Enable text input
                new_path = stdscr.getstr(4, 1).decode(encoding="utf-8")
                curses.noecho()  # Disable text input
                config.set('DEFAULT', 'notesheet_paths', new_path)
                with open(CONFIG_FILE_PATH, 'w') as configfile:
                    config.write(configfile)
                stdscr.addstr(5, 1, "Notesheet path changed!")
                stdscr.refresh()
                stdscr.getch()  # Wait for user input to continue
            elif current_option == 1:
                # Reset settings with confirmation
                stdscr.addstr(3, 1, "Are you sure you want to reset? Type 'Yes!' to confirm: ")
                stdscr.refresh()
                curses.echo()  # Enable text input
                confirmation = stdscr.getstr(4, 1).decode(encoding="utf-8")
                curses.noecho()  # Disable text input
                if confirmation.strip() == "Yes!":
                    create_default_config()
                    stdscr.addstr(5, 1, "Settings reset!")
                    stdscr.refresh()
                    stdscr.getch()  # Wait for user input to continue
                else:
                    stdscr.addstr(5, 1, "Reset canceled!")
                    stdscr.refresh()
                    stdscr.getch()  # Wait for user input to continue
            elif current_option == 2:
                # Go Back
                return


def main():
    curses.wrapper(main_menu)


if __name__ == "__main__":
    main()
