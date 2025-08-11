import glob
import json
import pathlib
import re
import sys
import zipfile

from typing import Any

from modules.utils import Font, download, eprint, update_hash, validate_json


def main(download_location: str) -> None:
    update_mia(download_location)


def update_mia(download_location: str) -> None:
    """Downloads the latest MIA lists, and parses them into a usable format."""

    local_file: str = str(pathlib.Path('mias').joinpath('mia.zip'))
    local_path: str = f'{pathlib.Path(local_file).parent}'

    # Clear out the MIAs folder
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

                member.filename = pathlib.Path(member.filename).name

                zip_file.extract(member, local_path)

        pathlib.Path(local_file).unlink()

        # Set up the system MIAs
        system_mias: dict[str, list[dict[str, str]]] = {}

        # Get Markdown into a format that's useful for Retool
        md_files = glob.glob(f'{local_path}/*.md')

        # Get DAT file tags to remove
        dat_file_tags: list[str] = []

        try:
            with open('config/internal-config.json', encoding='utf-8') as input_file:
                config_file_content: dict[str, Any] = json.load(input_file)

                if 'datFileTags' in config_file_content:
                    dat_file_tags = config_file_content['datFileTags']
        except Exception:
            eprint('Couldn\'t read internal-config.json', level='error')
            sys.exit(1)

        for md_file in md_files:
            # Get the system name
            system_name: str = re.sub('\\s?MIAs$', '', pathlib.Path(md_file).stem)

            for tag in dat_file_tags:
                system_name = re.sub(rf'\s?\({tag}\)', '', system_name)

            if system_name.startswith('No-Intro - '):
                system_name = system_name.replace('No-Intro - ', '')
                system_name = f'{system_name} (No-Intro)'

            if system_name.startswith('Redump - '):
                system_name = system_name.replace('Redump - ', '')
                system_name = f'{system_name} (Redump)'

            # Rewrite incorrect system names
            system_mapping: dict[str, str] = {
                'Atari - 2600 (No-Intro)': 'Atari - Atari 2600 (No-Intro)',
                'Atari - 5200 (No-Intro)': 'Atari - Atari 5200 (No-Intro)',
                'Atari - 7800 (No-Intro)': 'Atari - Atari 7800 (No-Intro)',
                'Atari - Jaguar (No-Intro)': 'Atari - Atari Jaguar (No-Intro)',
                'Atari - Lynx (No-Intro)': 'Atari - Atari Lynx (No-Intro)',
                'Atari - ST (No-Intro)': 'Atari - Atari ST (No-Intro)',
            }

            for mia_name, proper_name in system_mapping.items():
                if mia_name == system_name:
                    system_name = proper_name

            if system_name not in system_mias:
                system_mias[system_name] = []

            # Extract the MIA titles
            with open(md_file, encoding='utf-8') as md:
                for line in md.readlines():
                    if line.startswith('###'):
                        if 'CRC: ' in line[-14:]:
                            system_mias[system_name].append(
                                {'name': line[4:-16].strip(), 'crc': line[-9:].strip()}
                            )
                    if line.startswith('- '):
                        if 'CRC: ' in line[-14:]:
                            system_mias[system_name].append(
                                {'name': line[2:-16].strip(), 'crc': line[-9:].strip()}
                            )

        # Write the MIA JSON files
        system_mias = dict(sorted(system_mias.items()))

        eprint('• Writing system MIA files...')
        for system, system_files in system_mias.items():
            with open(f'{local_path}/{system}.json', 'w', encoding='utf-8') as mia_file:
                mia_file.writelines('{\n\t"mias": [')

                for system_file in sorted(system_files, key=lambda x: x['name']):
                    system_file_name: str = system_file['name'].replace('\\', '\\\\')
                    system_file_crc: str = system_file['crc']

                    if system_file == sorted(system_files, key=lambda x: x['name'])[-1]:
                        mia_file.writelines(
                            f'\n\t\t{{\n\t\t\t"name": "{system_file_name}",\n\t\t\t"crc": "{system_file_crc}"\n\t\t}}'
                        )
                    else:
                        mia_file.writelines(
                            f'\n\t\t{{\n\t\t\t"name": "{system_file_name}",\n\t\t\t"crc": "{system_file_crc}"\n\t\t}},'
                        )

                mia_file.writelines('\n\t]\n}\n')

            with open(f'{local_path}/{system}.json', 'r', encoding='utf-8') as mia_file:
                validate_json(mia_file.read(), f'{local_path}/{system}.json')

        # Remove unneeded MIA files
        all_mias = glob.glob(f'{local_path}/*.json')
        all_mias_paths = [pathlib.Path(x) for x in all_mias]
        new_mias_paths = [pathlib.Path('mias').joinpath(f'{x}.json') for x in system_mias.keys()]

        old_files = [x for x in all_mias_paths if x not in new_mias_paths]

        for old_file in old_files:
            pathlib.Path(old_file).unlink()

        # Remove the Markdown files
        files = glob.glob(f'{local_path}/*.md')

        for file in files:
            pathlib.Path(file).unlink()

        eprint('• Writing system MIA files... done.', overwrite=True)

        # Update the hash.json file
        eprint(f'• Writing MIA hash.json file...')

        files = list(str(x) for x in pathlib.Path('mias').glob('*.json'))

        update_hash(files, 'mias/hash.json')

        eprint('• Writing MIA hash.json file... done.', overwrite=True)

if __name__ == '__main__':
    main(sys.argv[1])
