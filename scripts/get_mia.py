import glob
import json
import pathlib
import re
import shutil
import sys
import tempfile
import zipfile
from typing import Any

from modules.utils import Font, download, eprint, update_hash, validate_json


def main(download_location: str) -> None:
    update_mia(download_location)


def update_mia(download_location: str) -> None:
    """Downloads the latest MIA lists, and parses them into a usable format."""
    mias_dir = pathlib.Path('mias')

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        local_file = tmp_path / 'mia.zip'

        eprint()
        failed: bool = False
        failed = download((f'{download_location}', str(local_file)), True)

        if failed:
            eprint(
                '• Download failed, leaving existing MIA files untouched.', level='error'
            )
            return

        eprint(
            f'• Downloading {Font.b}{local_file.name}{Font.be}... done.', overwrite=True
        )

        with zipfile.ZipFile(local_file) as zip_file:
            for member in zip_file.infolist():
                if member.is_dir():
                    continue

                member.filename = pathlib.Path(member.filename).name

                zip_file.extract(member, tmp_path)

        local_file.unlink()

        # Set up the system MIAs.
        system_mias: dict[str, list[dict[str, str]]] = {}

        # Get Markdown into a format that's useful for Retool.
        md_files = glob.glob(f'{tmp_path}/*.md')

        # Get DAT file tags to remove.
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
            with open(f'{tmp_path}/{system}.json', 'w', encoding='utf-8') as mia_file:
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

            with open(f'{tmp_path}/{system}.json', encoding='utf-8') as mia_file:
                validate_json(mia_file.read(), f'{tmp_path}/{system}.json')

        # Remove the Markdown files.
        files = glob.glob(f'{tmp_path}/*.md')

        for file in files:
            pathlib.Path(file).unlink()

        eprint('• Writing system MIA files... done.', overwrite=True)

        # Update the hash.json file.
        eprint('• Writing MIA hash.json file...')

        files = [str(x) for x in tmp_path.glob('*.json')]

        update_hash(files, f'{tmp_path}/hash.json')

        eprint('• Writing MIA hash.json file... done.', overwrite=True)

        for old_file in mias_dir.glob('*.*'):
            old_file.unlink()

        for new_file in tmp_path.glob('*.json'):
            shutil.copy(new_file, mias_dir / new_file.name)


if __name__ == '__main__':
    main(sys.argv[1])
