import glob
import json
import pathlib
import re
import sys
import zipfile

from lxml import etree
from lxml import html as html_

from modules.parse_dat import TitleData, define_lxml_parser, get_logiqx_header, get_logiqx_titles
from modules.utils import Font, download, eprint, update_hash, validate_json


def main(download_location: str) -> None:
    update_ra(download_location)


def update_ra(download_location: str) -> None:
    """
    Downloads the latest RetroAchievements DAT files, and parses them into a usable
    format.

    Args:
        config (Config): The Retool config object.

        gui_input (UserInput): Used to determine whether the update is being run from the
            GUI. If so, check if a custom download location has been set in
            `user-config.yaml`.

        no_exit (bool): Whether to exit the Retool process after the update has run.

    Raises:
        ExitRetool: Silently exit if run from the GUI, so UI elements can re-enable.

    Returns:
        int: How many successful downloads there were.
    """
    # Download all RetroAchievements details, and get them into a format that Retool
    # understands
    local_file: str = str(pathlib.Path('retroachievements').joinpath('ra.zip'))
    local_path: str = f'{pathlib.Path(local_file).parent}'

    # Clear out the RetroAchievements folder
    files = glob.glob(f'{local_path}/*.*')

    for file in files:
        pathlib.Path(file).unlink()

    eprint()

    failed: bool = False
    failed = download((f'{download_location}', local_file), True)

    if not failed:
        eprint(
            f'• Downloading {Font.b}{pathlib.Path(local_file).name}{Font.be}... done.',
            overwrite=True,
        )

        with zipfile.ZipFile(local_file) as zip_file:
            for member in zip_file.infolist():

                if member.is_dir():
                    continue

                if (
                    'Unofficial-RA-DATs-main/DATs/RetroAchievements (No Subfolders)/'
                    in member.filename
                ):
                    member.filename = re.sub('^RA - ', '', pathlib.Path(member.filename).name)
                    zip_file.extract(member, local_path)

        pathlib.Path(local_file).unlink()

        # Write the RetroAchievements JSON files
        eprint('• Writing system RetroAchievements files...')
        files = glob.glob(f'{local_path}/*.dat')
        title_data: set[TitleData]

        for file in files:
            header_data = get_logiqx_header(pathlib.Path(file))
            title_data = get_logiqx_titles(
                pathlib.Path(file), ('game', 'machine'), ra_digest_only=True
            )

            parser = define_lxml_parser()

            for header_detail in header_data:
                element = etree.XML(
                    html_.tostring(html_.fromstring(header_detail.strip())), parser=parser
                )

                if element.tag == 'name':
                    system_name: str = element.text if element.text is not None else 'Unknown'
                    break

            system_name = re.sub('^RA - ', '', system_name)

            # Remove systems not in No-Intro or Redump
            skip_systems: list[str] = [
                'Arcade',
                'Elektor TV Games Computer',
                'NEC PC-8801',
                'Uzebox',
                'WASM-4',
            ]

            if system_name in skip_systems:
                continue

            # Rewrite incorrect system names
            system_mapping: dict[str, str] = {
                '3DO Interactive Multiplayer': 'Panasonic - 3DO Interactive Multiplayer',
                '3DO Interactive Multiplayer (CHD)': 'Panasonic - 3DO Interactive Multiplayer (CHD)',
                'Amstrad CPC': 'Amstrad - CPC',
                'Apple II': 'Apple - II',
                'Arduboy': 'Arduboy Inc - Arduboy',
                'Atari 2600': 'Atari - Atari 2600',
                'Atari 7800': 'Atari - Atari 7800',
                'Atari Jaguar': 'Atari - Atari Jaguar',
                'Atari Jaguar CD': 'Atari - Jaguar CD Interactive Multimedia System',
                'Atari Lynx': 'Atari - Atari Lynx',
                'Colecovision': 'Coleco - Colecovision',
                'Emerson Arcadia 2001': 'Emerson - Arcadia 2001',
                'Fairchild Channel F': 'Fairchild - Channel F',
                'GCE Vectrex': 'GCE - Vectrex',
                'Interton VC 4000': 'Interton - VC 4000',
                'Magnavox Odyssey 2': 'Magnavox - Odyssey 2',
                'Mattel Intellivision': 'Mattel - Intellivision',
                'Mega Duck': 'Welback - Mega Duck',
                'Microsoft MSX': 'Microsoft - MSX',
                'NEC PC-FX': 'NEC - PC-FX & PC-FXGA',
                'NEC PC-FX (CHD)': 'NEC - PC-FX & PC-FXGA (CHD)',
                'NEC TurboGrafx-16': 'NEC - PC Engine - TurboGrafx-16',
                'NEC TurboGrafx-CD': 'NEC - PC Engine CD & TurboGrafx CD',
                'NEC TurboGrafx-CD (CHD)': 'NEC - PC Engine CD & TurboGrafx CD (CHD)',
                'Nintendo 64': 'Nintendo - Nintendo 64',
                'Nintendo DS': 'Nintendo - Nintendo DS',
                'Nintendo DSi': 'Nintendo - Nintendo DSi',
                'Nintendo Entertainment System': 'Nintendo - Nintendo Entertainment System',
                'Nintendo Game Boy Advance': 'Nintendo - Game Boy Advance',
                'Nintendo Game Boy Color': 'Nintendo - Game Boy Color',
                'Nintendo Game Boy': 'Nintendo - Game Boy',
                'Nintendo GameCube': 'Nintendo - GameCube',
                'Nintendo Pokemon Mini': 'Nintendo - Pokemon Mini',
                'Nintendo Virtual Boy': 'Nintendo - Virtual Boy',
                'Sega 32X': 'Sega - 32X',
                'Sega CD': 'Sega - Mega CD & Sega CD',
                'Sega CD (CHD)': 'Sega - Mega CD & Sega CD (CHD)',
                'Sega Dreamcast': 'Sega - Dreamcast',
                'Sega Dreamcast (CHD)': 'Sega - Dreamcast (CHD)',
                'Sega Game Gear': 'Sega - Game Gear',
                'Sega Genesis': 'Sega - Mega Drive - Genesis',
                'Sega Master System': 'Sega - Master System - Mark III',
                'Sega Saturn': 'Sega - Saturn',
                'Sega Saturn (CHD)': 'Sega - Saturn (CHD)',
                'Sega SG-1000': 'Sega - SG-1000',
                'SNK Neo Geo CD': 'SNK - Neo Geo CD',
                'SNK Neo Geo CD (CHD)': 'SNK - Neo Geo CD (CHD)',
                'SNK Neo Geo Pocket': 'SNK - NeoGeo Pocket',
                'Sony Playstation 2': 'Sony - PlayStation 2',
                'Sony Playstation': 'Sony - PlayStation',
                'Sony PSP': 'Sony - PlayStation Portable',
                'Super Nintendo Entertainment System': 'Nintendo - Super Nintendo Entertainment System',
                'Watara Supervision': 'Watara - Supervision',
                'WonderSwan': 'Bandai - WonderSwan',
            }

            for ra_name, proper_name in system_mapping.items():
                if ra_name == system_name:
                    system_name = proper_name

            retroachievements_titles: list[dict[str, str]] = []

            for title in title_data:
                title_digests: list[dict[str, str]] = [
                    digest
                    for digest in title.files
                    if digest != {'crc': '', 'md5': '', 'sha1': '', 'sha256': ''} and digest != {}
                ]

                for title_digest in title_digests:
                    retroachievements_title: dict[str, str] = {}

                    retroachievements_title['name'] = title.name

                    def populate_digests(
                        digest_type: str,
                        title_digest: dict[str, str] = title_digest,
                        retroachievements_title: dict[str, str] = retroachievements_title,
                    ) -> None:
                        """
                        Assigns a dictionary key to the relevant digest value.

                        Args:
                            digest_type (str): The digest type: crc, md5, sha1, sha256.
                            title_digest: The title digest.
                            retroachievements_title: The RetroAchievements title.
                        """
                        if title_digest[digest_type]:
                            retroachievements_title[digest_type] = title_digest[digest_type]

                    populate_digests('crc')
                    populate_digests('md5')
                    populate_digests('sha1')
                    populate_digests('sha256')

                    retroachievements_titles.append(retroachievements_title)

            # Modify the JSON
            json_file: str = json.dumps(
                json.loads(
                    f'{{\n\t"retroachievements":\n{json.dumps(sorted(retroachievements_titles, key=lambda d: d['name']))}\n\t}}'
                ),
                indent=4,
            )

            # Write the file
            with open(f'{local_path}/{system_name}.json', 'w', encoding='utf-8') as ra_file:
                ra_file.write(f'{json_file}\n')

            with open(f'{local_path}/{system_name}.json', 'r', encoding='utf-8') as ra_file:
                validate_json(ra_file.read(), f'{local_path}/{system_name}.json')

            # We need to duplicate JSON files where systems have been merged
            merged_systems: dict[str, str] = {
                'Bandai - WonderSwan': 'Bandai - WonderSwan Color',
                'Microsoft - MSX': 'Microsoft - MSX2',
                'NEC - PC Engine - TurboGrafx-16': 'NEC - PC Engine SuperGrafx',
            }

            for system, duplicate in merged_systems.items():
                if system == system_name:
                    with open(f'{local_path}/{duplicate}.json', 'w', encoding='utf-8') as ra_file:
                        ra_file.write(f'{json_file}\n')

        # Remove the DAT files
        files = glob.glob(f'{local_path}/*.dat')

        for file in files:
            pathlib.Path(file).unlink()

        eprint('• Writing system RetroAchievements files... done.', overwrite=True)

        # Update the hash.json file
        eprint(f'• Writing RetroAchievements hash.json file...')

        files = list(str(x) for x in pathlib.Path('retroachievements').glob('*.json'))

        update_hash(files, 'retroachievements/hash.json')

        eprint('• Writing RetroAchievements hash.json file... done.', overwrite=True)

if __name__ == '__main__':
    main(sys.argv[1])
