#!/usr/bin/env python

import json
import pathlib
import subprocess
import sys
import traceback
import uuid
from datetime import datetime
from typing import Any

from natsort import natsorted


def main() -> None:
    # Get uncommitted Git changes
    files = (
        subprocess.run(['git', 'diff', '--name-only'], stdout=subprocess.PIPE)
        .stdout.decode('utf-8')
        .split('\n')
    )
    files = [x for x in files if 'clonelists' in x]

    if not files:
        # Compare current commit and previous commit to get files that have changed
        if sys.platform.startswith('win'):
            files = (
                subprocess.run(
                    ['git', 'diff', 'HEAD~', 'HEAD', '--name-only'], stdout=subprocess.PIPE
                )
                .stdout.decode('utf-8')
                .split('\n')
            )
        else:
            files = (
                subprocess.run(
                    ['git', 'diff', 'HEAD^', 'HEAD', '--name-only'], stdout=subprocess.PIPE
                )
                .stdout.decode('utf-8')
                .split('\n')
            )

    files = [x for x in files if 'clonelists' in x]

    for file in files:
        if file != 'hash.json':
            with open(pathlib.Path(file), encoding='utf-8') as clone_list_file:
                clonelist = json.load(clone_list_file)

            # Order description
            description_key_order: list[str] = ['name', 'lastUpdated', 'minimumVersion']

            temp_dict = {}

            for _ in clonelist['description']:
                for k in description_key_order:
                    if k in clonelist['description']:
                        temp_dict[k] = clonelist['description'][k]

            clonelist['description'] = temp_dict

            # Set current datetime
            # TODO: This changes all the dates even if nothing else in the file has changed... that's not the greatest
            if 'lastUpdated' in clonelist['description']:
                clonelist['description']['lastUpdated'] = datetime.now().strftime(  # noqa: DTZ005
                    '%Y-%m-%d %H:%M:%S'
                )

            # Set minimum version of Retool required for a clone list, baseline = 2.4.0
            if 'minimumVersion' in clonelist['description']:
                if clonelist['description']['minimumVersion'] < '2.4.0':
                    clonelist['description']['minimumVersion'] = '2.4.0'

            # Sort variants by group name
            clonelist['variants'] = natsorted(
                clonelist['variants'], key=lambda d: d.get('group', '').lower()
            )

            # Sort titles by priority, then by searchTerm. Enforce top-level key order, and sort
            # keys and lists in substructures.
            def order_variant_keys(
                variant: dict[str, list[dict[str, Any]]], variant_type: str
            ) -> list[dict[str, Any]]:
                """
                Orders and sorts the keys in objects in titles, supersets, or compilations arrays.

                Args:
                    variant (dict[str, list[dict[str, Any]]]): A variant object in the `variants`
                        array in a clone list.
                    variant_type (str): Either `titles`, `supersets`, or `compilations`.

                Returns:
                    list[dict[str, Any]]: An ordered and sorted set of titles, supersets, or
                    compilations.
                """
                key_order: list[str] = [
                    'searchTerm',
                    'nameType',
                    'priority',
                    'titlePosition',
                    'categories',
                    'englishFriendly',
                    'isOldest',
                    'superset',
                    'localNames',
                    'filters',
                ]
                temp_variant = []

                for title in variant[variant_type]:
                    temp_dict = {}

                    if 'categories' in title:
                        title['categories'] = sorted(title['categories'])

                    if 'localNames' in title:
                        title['localNames'] = dict(natsorted(title['localNames'].items()))

                    if 'filters' in title:
                        temp_list = []

                        for filter in title['filters']:
                            if 'conditions' in filter:
                                if 'matchLanguages' in filter['conditions']:
                                    filter['conditions']['matchLanguages'] = sorted(
                                        filter['conditions']['matchLanguages']
                                    )

                                if 'matchRegions' in filter['conditions']:
                                    filter['conditions']['matchRegions'] = sorted(
                                        filter['conditions']['matchRegions']
                                    )

                                if 'regionOrder' in filter['conditions']:
                                    if 'higherRegions' in filter['conditions']['regionOrder']:
                                        filter['conditions']['regionOrder']['higherRegions'] = (
                                            sorted(
                                                filter['conditions']['regionOrder']['higherRegions']
                                            )
                                        )
                                    if 'lowerRegions' in filter['conditions']['regionOrder']:
                                        filter['conditions']['regionOrder']['lowerRegions'] = (
                                            sorted(
                                                filter['conditions']['regionOrder']['lowerRegions']
                                            )
                                        )

                                    filter['conditions']['regionOrder'] = dict(
                                        sorted(filter['conditions']['regionOrder'].items())
                                    )

                                filter['conditions'] = dict(sorted(filter['conditions'].items()))

                            if 'results' in filter:
                                if 'categories' in filter['results']:
                                    filter['results']['categories'] = sorted(
                                        filter['results']['categories']
                                    )

                                filter['results'] = dict(sorted(filter['results'].items()))

                            temp_list.append(dict(sorted(filter.items())))

                        title['filters'] = temp_list

                    for k in key_order:
                        if k in title:
                            temp_dict[k] = title[k]

                    temp_variant.append(temp_dict)

                return temp_variant

            for variant in clonelist['variants']:
                if 'titles' in variant:
                    variant['titles'] = natsorted(
                        variant['titles'],
                        key=lambda d: (d.get('priority', 0), d.get('searchTerm', '').lower()),
                    )
                    variant['titles'] = order_variant_keys(variant, 'titles')

                if 'supersets' in variant:
                    variant['supersets'] = natsorted(
                        variant['supersets'],
                        key=lambda d: (d.get('priority', 0), d.get('searchTerm', '').lower()),
                    )
                    variant['supersets'] = order_variant_keys(variant, 'supersets')

                if 'compilations' in variant:
                    variant['compilations'] = natsorted(
                        variant['compilations'],
                        key=lambda d: (d.get('priority', 0), d.get('searchTerm', '').lower()),
                    )
                    variant['compilations'] = order_variant_keys(variant, 'compilations')

            clonelist, replacements = single_line(clonelist)
            cleaned_json = json.dumps(clonelist, indent='\t', ensure_ascii=False)

            for old, new in replacements:
                cleaned_json = cleaned_json.replace(old, new)

            with open(pathlib.Path(file), 'w', encoding='utf-8') as clone_list_file:
                clone_list_file.write(f'{cleaned_json}\n')


def single_line(o: Any) -> Any:
    """
    Puts select JSON structures on a single line.

    From https://stackoverflow.com/questions/58736826/format-some-json-object-with-certain-fields-on-one-line.

    Args:
        o (Any): The JSON object.

    Returns:
        Any: The formatted JSON object and its replacements.
    """
    if isinstance(o, dict):
        if 'searchTerm' in o and 'localNames' not in o and 'filters' not in o:
            replacement = uuid.uuid4().hex
            return replacement, [(f'"{replacement}"', json.dumps(o, ensure_ascii=False))]
        replacements = []
        result_dict = {}
        for key, value in o.items():
            new_value, value_replacements = single_line(value)
            result_dict[key] = new_value
            replacements.extend(value_replacements)
        return result_dict, replacements
    elif isinstance(o, list):
        if all([isinstance(x, str) for x in o]):  # noqa: C419
            replacement = uuid.uuid4().hex
            return replacement, [(f'"{replacement}"', json.dumps(o, ensure_ascii=False))]
        replacements = []
        result_list = []
        for value in o:
            new_value, value_replacements = single_line(value)
            result_list.append(new_value)
            replacements.extend(value_replacements)
        return result_list, replacements
    else:
        return o, []


# TODO: Generate hash.json for all the files in the dir

if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('\n• Unexpected error:\n\n')
        traceback.print_exc()
