import os
import pathlib
import re

from lxml import etree
from lxml import html as html_
from typing import Any, Iterator


class TitleData:
    def __init__(
        self,
        name: str = '',
        categories: set[str] | None = None,
        description: str = '',
        tag_name: str = 'game',
        tag_attribs: dict[str, str] | None = None,
        files: list[dict[str, str]] | None = None,
        unrecognized_children: list[str] | None = None,
    ) -> None:
        """
        Creates an object that contains an input DAT's titles.

        Args:
            name (str, optional): The name of the title. Defaults to `''`.

            categories (set[str], optional): The categories of the title. Defaults to
                `None`.

            description (str, optional): The description of the title. Defaults to `''`.

            tag_name (str, optional): Whether the tag around the title is set to `game`
                or `machine`. Defaults to `''`.

            tag_attribs (dict[str, str]): Additional unrecognized attributes set on the
                `game` or `machine` tag. Defaults to `None`.

            files (list[dict[str, str]], optional): The files in the title. Defaults to
                `None`.

            unrecognized_children (list[str]): Child elements not recognized by Retool.
                Defaults to `None`.
        """
        self.name: str = name
        self.categories: set[str] = categories if categories is not None else set()
        self.description: str = description
        self.tag_name: str = tag_name
        self.tag_attribs: dict[str, str] = tag_attribs if tag_attribs is not None else {}
        self.files: list[dict[str, str]] = files if files is not None else []
        self.unrecognized_children: list[str] = (
            unrecognized_children if unrecognized_children is not None else []
        )


def clean_namespaces(element: etree._Element) -> etree._Element:
    """
    Removes unneeded namespaces from XML elements.

    Args:
        element (etree._Element): An element from an XML file.

    Returns:
        etree._Element: The cleaned element with no namespaces.
    """
    for attr in element.attrib:
        if etree.QName(attr).namespace:
            del element.attrib[attr]

    etree.cleanup_namespaces(element)

    return element


def define_lxml_parser() -> etree.XMLParser:
    """Defines the LXML parser."""
    parser = etree.XMLParser(
        encoding='utf-8',
        no_network=True,
        ns_clean=True,
        recover=True,
        remove_comments=True,
        remove_pis=True,
        resolve_entities=False,
        strip_cdata=True,
    )

    return parser


def fast_lxml_iter(context: etree.iterparse, func: Any, *args: Any, **kwargs: Any) -> None:
    """
    Reads through XML without chewing up huge amounts of memory.

    http://lxml.de/parsing.html#modifying-the-tree
    Based on Liza Daly's fast_iter
    https://public.dhe.ibm.com/software/dw/xml/x-hiperfparse/x-hiperfparse-pdf.pdf
    See also http://effbot.org/zone/element-iterparse.htm

    Args:
        context (etree.iterparse): The iterparse context.

        func (Any): The `process_element` function.

        args (Any): Additional arguments.

        kwargs (Any): Additional keyword arguments.
    """
    for _, element in context:
        func(element, *args, **kwargs)
        # It's safe to call clear() here because no descendants will be accessed
        element.clear()
        # Also eliminate now-empty references from the root node to element
        for ancestor in element.xpath('ancestor-or-self::*'):
            while ancestor.getprevious() is not None:
                del ancestor.getparent()[0]
    del context


def get_logiqx_file_details(
    child: etree._Element, file_type: str, digest_only: bool
) -> dict[str, str]:
    """
    Gets the following file details from a LogiqX rom or disk element.

    * name
    * size
    * mia
    * header
    * crc
    * md5
    * sha1
    * sha256

    Args:
        child (etree._Element): The rom or disk element.

        file_type (str): Whether the element has a rom or disk tag.

        digest_only (bool): Whether to only return digests.

    Returns:
        dict[str, str]: The file details.
    """
    if not digest_only:
        file_name = child.attrib.get('name', '')
        file_size = child.attrib.get('size', '')
        file_mia = child.attrib.get('mia', '')
        file_header = child.attrib.get('header', '')

    file_crc: str = child.attrib.get('crc', '')
    file_md5: str = child.attrib.get('md5', '')
    file_sha1: str = child.attrib.get('sha1', '')
    file_sha256: str = child.attrib.get('sha256', '')

    if digest_only:
        file_details = {'crc': file_crc, 'md5': file_md5, 'sha1': file_sha1, 'sha256': file_sha256}
    else:
        file_details = {
            'name': file_name,
            'size': file_size,
            'crc': file_crc,
            'md5': file_md5,
            'sha1': file_sha1,
            'sha256': file_sha256,
            'type': file_type,
            'mia': file_mia,
            'header': file_header,
        }

    return file_details


def get_logiqx_header(dat_file: pathlib.Path) -> list[str]:
    """
    Reads in the first bytes of a LogiqX DAT file until the header is retrieved. Much
    lighter on memory than parsing with lxml.

    Args:
        dat_file (pathlib.Path): A pathlib object pointing to the DAT file.

    Returns:
        list[str]: The contents of the node for processing later.
    """
    header: list[str] = []

    with open(pathlib.Path(dat_file), 'rb') as file:
        pos: int = 0

        first_line: bytes = file.readline()
        header_bytes: bytes = b''

        file.seek(0)

        # Basic check to make sure it's a LogiqX file
        if (
            b'<?xml version' in first_line
            or b'<!DOCTYPE datafile' in first_line
            or b'<datafile>"' in first_line
        ):
            while file.read(9) != b'</header>':
                pos += 1
                file.seek(pos, os.SEEK_SET)

            file.seek(0)
            header_bytes = file.read(pos + 9)

            header_str = header_bytes.decode('utf-8')

            regex_search_index_start = re.search('\\s*?<header', header_str)
            regex_search_index_end = re.search('\n*\\s*?</header', header_str)

            if regex_search_index_start and regex_search_index_end:
                header_str = header_str[
                    regex_search_index_start.start() : regex_search_index_end.start()
                ]

            header = [line.replace('\r', '\n') for line in header_str.split('\n') if line != '\r'][
                1:
            ]

    return header


def get_logiqx_titles(
    dat_file: pathlib.Path, tag_names: tuple[str, ...], ra_digest_only: bool = False
) -> set[TitleData]:
    """
    Gets the titles from a LogiqX DAT file.

    Args:
        dat_file (pathlib.Path): The path to the DAT file.

        tag_names (tuple[str, ...]): Which tag names to search for in the DAT file (
            usually `game` and `machine`).

        ra_digest_only (bool, optional): Only return the title name and hashes for
            RetroAchievements

    Returns:
        set[TitleData]: A set of titles.
    """

    titles: set[TitleData] = set()

    def process_element(element: etree._Element) -> None:
        if element is not None:
            title: TitleData = TitleData()

            if not ra_digest_only:
                # Collect the details for each title
                title.tag_name = element.tag
                title.name = element.attrib.get('name', '')

                # Only add the title if there's a name
                if title.name:
                    known_attribs: set[str] = {'name', 'cloneof', 'cloneofid', 'romof'}
                    collected_attribs: dict[str, str] = {}

                    for attrib in element.attrib:
                        if attrib not in known_attribs:
                            collected_attribs[str(attrib)] = str(element.attrib[attrib])

                    title.tag_attribs = collected_attribs

                    if description_element := [
                        x.text for x in element.iterchildren(tag='description')
                    ]:
                        title.description = str(description_element[0])

                    title.categories = {str(x.text) for x in element.iterchildren(tag='category')}

                    files: Iterator[etree._Element] = element.iterchildren(tag=('rom', 'disk'))
                    file_type: str

                    if files:
                        for child in files:
                            file_type = 'rom'

                            if child.tag == 'disk':
                                file_type = 'disk'

                            file_details = get_logiqx_file_details(child, file_type, ra_digest_only)

                            # Check for at least one digest in the file
                            if file_details['name'] and (
                                file_details['crc']
                                or file_details['md5']
                                or file_details['sha1']
                                or file_details['sha256']
                            ):
                                title.files.append(file_details)

                    # Add unrecognized children found in the element
                    unrecognized_children: list[etree._Element] = list(
                        element.xpath(  # type: ignore
                            '*[not(self::category) '
                            'and not(self::description) '
                            'and not(self::disk) '
                            'and not(self::name) '
                            'and not(self::release) '
                            'and not(self::rom)]'
                        )
                    )

                    if unrecognized_children:
                        parser = define_lxml_parser()

                        for child in unrecognized_children:
                            child = etree.XML(html_.tostring(child), parser=parser)
                            title.unrecognized_children.append(
                                etree.tostring(clean_namespaces(child)).decode('utf-8')
                            )
            else:
                title.name = ''

                title.name = element.attrib.get('name', '')

                files = element.iterchildren(tag=('rom', 'disk'))
                file_details = {}

                for child in files:
                    if 'name' in child.attrib:
                        # Exclude CUE or GDI files, which can change digests if the
                        # file name changes
                        if not any(x in child.attrib['name'] for x in ('.cue', '.gdi')):
                            file_details = get_logiqx_file_details(child, '', ra_digest_only)

                    # Check for at least one digest in the file
                    if file_details:
                        if (
                            'crc' in file_details
                            or 'md5' in file_details
                            or 'sha1' in file_details
                            or 'sha256' in file_details
                        ):
                            # RetroAchievements only takes track 0 for multi-track games, so we
                            # only want to return one file anyway
                            if not title.files and file_details:
                                title.files.append(file_details)

            # Add the title if it has files listed
            if title.files:
                titles.add(title)

    context = etree.iterparse(
        source=dat_file,
        events=('end',),
        tag=tag_names,
        attribute_defaults=False,
        encoding='utf-8',
        no_network=True,
        recover=True,
        remove_blank_text=True,
        remove_comments=True,
        remove_pis=True,
        resolve_entities=False,
        strip_cdata=True,
    )

    fast_lxml_iter(context, process_element)

    return titles