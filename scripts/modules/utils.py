
import datetime
import os
import pathlib
import sys
import textwrap
import time
import urllib.parse
import urllib.request

from typing import Any
from urllib.error import HTTPError, URLError


class Font:
    """Console text formatting."""

    success: str = '\033[0m\033[92m'
    success_bold: str = '\033[1m\033[92m'
    warning: str = '\033[0m\033[93m'
    warning_bold: str = '\033[1m\033[93m'
    error: str = '\033[0m\033[91m'
    error_bold: str = '\033[1m\033[91m'
    heading: str = '\033[0m\033[36m'
    heading_bold: str = '\033[1m\033[36m'
    subheading: str = '\033[0m\033[35m'
    subheading_bold: str = '\033[1m\033[35m'
    disabled: str = '\033[90m'
    bold: str = '\033[1m'
    bold_end: str = '\033[22m'
    italic = '\033[3m'
    italic_end = '\033[23m'
    underline: str = '\033[4m'
    underline_end = '\033[24m'
    plain = '\033[22m\033[23m\033[24m'
    end: str = '\033[0m'

    b: str = bold
    be: str = bold_end
    d: str = disabled
    i: str = italic
    ie: str = italic_end
    u: str = underline
    ue: str = underline_end
    overwrite: str = '\033M\033[2K'


def download(download_details: tuple[str, ...], report_download: bool = True) -> bool:
    """
    Downloads a file from a given URL.

    Args:
        download_details (tuple[str, ...]): A tuple of the URL to download the file from,
            and the location to write it to.

        report_download (bool): Whether to report the filename being downloaded. Defaults
            to `True`.

    Returns:
        bool: Whether the download has failed.
    """
    download_url: str = download_details[0]
    local_file_path: str = download_details[1]

    if report_download:
        eprint(
            f'• Downloading {Font.b}{pathlib.Path(download_details[1]).name}...{Font.be}',
            wrap=False,
            overwrite=True,
        )

    def get_file(req: urllib.request.Request) -> tuple[bytes, bool]:
        """Error handling for downloading a file."""
        downloaded_file: bytes = b''
        failed: bool = False
        retrieved: bool = False
        retry_count: int = 0

        while not retrieved:
            try:
                with urllib.request.urlopen(req) as response:
                    downloaded_file = response.read()
            except HTTPError as error:
                now = get_datetime()

                if error.code == 404:
                    eprint(
                        f'\n  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: 404, file not found: {Font.b}{download_url}',
                        level='warning',
                    )
                    eprint(
                        f'  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: Skipping...\n',
                        level='warning',
                    )
                    retrieved = True
                else:
                    eprint(
                        f'\n  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: Data not retrieved: {error}',
                        level='warning',
                    )
                    eprint(
                        f'  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: Skipping...\n',
                        level='warning',
                    )
                    retrieved = True

                failed = True
            except URLError as error:
                if retry_count == 5:
                    break

                retry_count += 1
                now = get_datetime()
                eprint(
                    f'\n  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: Something unexpected happened: {error}',
                    level='warning',
                )
                eprint(
                    f'  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: Trying again in 5 seconds ({retry_count}/5)...'
                )
                time.sleep(5)
            except TimeoutError as error:
                if retry_count == 5:
                    break

                retry_count += 1
                now = get_datetime()
                eprint(
                    f'\n  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: Socket timeout: {error}',
                    level='warning',
                )
                eprint(
                    f'  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: Trying again in 5 seconds ({retry_count}/5)...'
                )
                time.sleep(5)
            except OSError as error:
                if retry_count == 5:
                    break

                retry_count += 1
                now = get_datetime()
                eprint(
                    f'\n  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: Socket error: {error}',
                    level='warning',
                )
                eprint(
                    f'  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: Trying again in 5 seconds ({retry_count}/5)...'
                )
                time.sleep(5)
            except Exception:
                if retry_count == 5:
                    break

                retry_count += 1
                now = get_datetime()
                eprint(
                    f'\n  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: Something unexpected happened.',
                    level='warning',
                )
                eprint(
                    f'  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: Trying again in 5 seconds ({retry_count}/5)...'
                )
                time.sleep(5)
            else:
                retrieved = True

        if retry_count == 5:
            failed = True
            now = get_datetime()
            eprint(
                f'\n  • [{now.strftime("%Y/%m/%d, %H:%M:%S")}]: {local_file_path} failed to download.\n\n',
                level='warning',
            )

        # Delete any zero-sized files that have been created
        if failed:
            failed_file: pathlib.Path = pathlib.Path(local_file_path)

            if failed_file.exists() and failed_file.stat().st_size == 0:
                pathlib.Path.unlink(failed_file)

        return (downloaded_file, failed)

    headers: dict[str, str] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36'
    }

    req: urllib.request.Request = urllib.request.Request(
        f'{os.path.dirname(download_url)}/{urllib.parse.quote(os.path.basename(download_url))}',
        None,
        headers,
    )

    downloaded_file: tuple[bytes, bool] = get_file(req)

    file_data: bytes = downloaded_file[0]
    failed: bool = downloaded_file[1]

    if not failed:
        pathlib.Path(local_file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(pathlib.Path(f'{local_file_path}').resolve(), 'wb') as output_file:
            output_file.write(file_data)

    if report_download:
        eprint(Font.overwrite)

    return failed


def eprint(
    text: str = '',
    wrap: bool = True,
    level: str = '',
    indent: int = 2,
    overwrite: bool = False,
    **kwargs: Any,
) -> None:
    """
    Prints to STDERR.

    Args:
        text (str, optional): The content to print. Defaults to `''`.

        wrap (bool, optional): Whether to wrap text. Defaults to `True`.

        level (str, optional): How the text is formatted. Valid values include `warning`,
            `error`, `success`, `disabled`, `heading`, `subheading`. Defaults to `''`.

        indent (int, optional): After the first line, how many spaces to indent whenever
            text wraps to a new line. Defaults to `2`.

        overwrite (bool, optional): Delete the previous line and replace it with this one.
            Defaults to `False`.

        **kwargs (Any): Any other keyword arguments to pass to the `print` function.
    """
    indent_str: str = ''
    new_line: str = ''
    overwrite_str: str = ''

    if text:
        indent_str = ' '

    if overwrite:
        overwrite_str = '\033M\033[2K'

    if level == 'warning':
        color = Font.warning
    elif level == 'error':
        color = Font.error
        new_line = '\n'
    elif level == 'success':
        color = Font.success
    elif level == 'disabled':
        color = Font.disabled
    elif level == 'heading':
        color = Font.heading_bold
    elif level == 'subheading':
        color = Font.subheading
    else:
        color = Font.end

    message: str = f"{overwrite_str}{color}{text}{Font.end}"

    if wrap:
        if level == 'heading':
            print(f'\n\n{Font.heading_bold}{"─"*95}{Font.end}', file=sys.stderr)  # noqa: T201
        if level == 'subheading':
            print(f'\n{Font.subheading}{"─"*60}{Font.end}', file=sys.stderr)  # noqa: T201
        print(  # noqa: T201
            f'{new_line}{textwrap.TextWrapper(width=95, subsequent_indent=indent_str*indent, replace_whitespace=False, break_long_words=False, break_on_hyphens=False).fill(message)}',
            file=sys.stderr,
            **kwargs,
        )
        if level == 'heading':
            print('\n')  # noqa: T201
    else:
        print(message, file=sys.stderr, **kwargs)  # noqa: T201


def get_datetime() -> datetime.datetime:
    """Gets the current datetime and time zone."""
    return (
        datetime.datetime.now(tz=datetime.timezone.utc)
        .replace(tzinfo=datetime.timezone.utc)
        .astimezone(tz=None)
    )