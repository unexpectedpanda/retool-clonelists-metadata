> [!IMPORTANT]
> Retool is no longer maintained. [Read the thread](https://github.com/unexpectedpanda/retool/issues/337)
for more information on what this means.

This is the repository for [Retool's](https://unexpectedpanda.github.io/retool/) clone
list and metadata files. It also hosts `config/internal-config.json`.

## Contributions

### Clone lists

Contributions are welcome. Before submitting a PR, make sure to read about
[how clone lists work and should be structured](https://unexpectedpanda.github.io/retool/contribute-clone-lists/). Make sure your changes are formatted correctly, tested, and
that `clonelists/hash.json` is updated accordingly.

### Metadata files

Metadata files are auto-generated from Redump and No-Intro databases, and shouldn't be
manually updated.

To make a change, don't submit a PR. Instead, report the issue upstream:

### MIA and RetroAchievements files

MIA and RetroAchievements files are pulled from external servers on a weekly basis, and
should not be manually updated. If the sources stop updating, then so will these files.

#### No-Intro

1. Go to [Dat-o-matic](https://datomatic.no-intro.org/).

1. Select the system the title is on.

1. Do a search for the archive name of the title with the issue.

1. Click on the title's name to open its page.

1. Click **New ticket**, fill out the form, and then submit it.

#### Redump

Go to Redump's [**Fixes & additions** forum](http://forum.redump.org/forum/15/fixes-additions/),
and request the issue be fixed.