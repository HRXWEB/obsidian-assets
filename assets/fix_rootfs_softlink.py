#!/usr/bin/env python
import sys
import os
import argparse
import logging
from typing import Generator, Tuple

class SymlinkConverter:
    def __init__(self, topdir: str):
        self.topdir = os.path.abspath(topdir)

    def handle_link(self, filep: str, subdir: str) -> None:
        """
        Convert an absolute symlink to a relative one if necessary.

        Args:
            filep (str): Path to the symlink
            subdir (str): Directory containing the symlink
        """
        link = os.readlink(filep)
        if not link.startswith('/') or link.startswith(self.topdir):
            return

        new_link = os.path.relpath(self.topdir + link, subdir)
        logging.info(f"Replacing {link} with {new_link} for {filep}")

        try:
            os.unlink(filep)
            os.symlink(new_link, filep)
        except OSError as e:
            logging.error(f"Failed to replace symlink {filep}: {e}")

    def walk_directory(self) -> Generator[Tuple[str, str], None, None]:
        """
        Walk through the directory and yield files that are symlinks.

        Yields:
            Tuple[str, str]: A tuple containing the full path to a symlink and its containing directory
        """
        for subdir, _, files in os.walk(self.topdir):
            for f in files:
                filep = os.path.join(subdir, f)
                if os.path.islink(filep):
                    yield filep, subdir

    def convert_symlinks(self) -> None:
        """Convert all absolute symlinks in the directory to relative ones."""
        for filep, subdir in self.walk_directory():
            self.handle_link(filep, subdir)

def main() -> None:
    parser = argparse.ArgumentParser(description="Convert absolute symlinks to relative ones in a sysroot directory.")
    parser.add_argument("directory", help="The sysroot directory to process")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    converter = SymlinkConverter(args.directory)
    converter.convert_symlinks()

if __name__ == "__main__":
    main()