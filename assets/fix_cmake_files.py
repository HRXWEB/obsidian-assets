#!/usr/bin/env python
import os
import re
import sys
import argparse
import logging
import shutil
from datetime import datetime
from typing import List

class PathReplacer:
    def __init__(self, cmake_sysroot_var: str = "${CMAKE_SYSROOT}"):
        self.cmake_sysroot_var = cmake_sysroot_var
        # 利用负向前瞻（negative lookbehind）匹配不包含${CMAKE_SYSROOT}前缀的"/"
        # 使用(?=/|$)确保后面是路径分隔符或字符串结束，防止匹配/usrxxx或/optxxx
        self.pattern_usr = r'(?<!\$\{CMAKE_SYSROOT\})(/usr)(?=/|$)'
        # self.pattern_lib = r'(?<!\$\{CMAKE_SYSROOT\})(/lib)'
        # self.pattern_bin = r'(?<!\$\{CMAKE_SYSROOT\})(/bin)'
        # self.pattern_share = r'(?<!\$\{CMAKE_SYSROOT\})(/share)'
        # self.pattern_etc = r'(?<!\$\{CMAKE_SYSROOT\})(/etc)'
        # self.pattern_include = r'(?<!\$\{CMAKE_SYSROOT\})(/include)'
        self.pattern_opt = r'(?<!\$\{CMAKE_SYSROOT\})(/opt)(?=/|$)'
        # self.patterns = [self.pattern_usr, self.pattern_lib, self.pattern_bin, self.pattern_share, self.pattern_etc, self.pattern_include, self.pattern_opt]
        self.patterns = [self.pattern_usr, self.pattern_opt]

    def replace_paths(self, content: str) -> str:
        """
        替换所有硬编码的/usr, /opt路径为：
        ${CMAKE_SYSROOT}/usr, ${CMAKE_SYSROOT}/opt
        但如果已有前缀则不再替换。
        """
        # re.subn 返回 (new_content, 替换次数)，方便调试
        for pattern in self.patterns:
            new_content, count = re.subn(pattern, f'{self.cmake_sysroot_var}\\1', content)
            if count > 0:
                logging.debug(f"Replaced {count} occurrences.")
                content = new_content
        return content

class CMakeFileProcessor:
    def __init__(self, replacer: PathReplacer, backup: bool = True):
        self.replacer = replacer
        self.backup = backup

    def process_file(self, file_path: str) -> bool:
        """Process a single CMake file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            updated_content = self.replacer.replace_paths(content)
            if updated_content != content:
                if self.backup:
                    self._create_backup(file_path)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                logging.info(f"Modified file: {file_path}")
                return True
        except IOError as e:
            logging.error(f"Error processing file {file_path}: {e}")
        return False

    def _create_backup(self, file_path: str) -> None:
        """Create a backup of the file with .bak extension."""
        backup_path = f"{file_path}.bak"
        try:
            shutil.copy2(file_path, backup_path)
            logging.info(f"Created backup: {backup_path}")
        except IOError as e:
            logging.error(f"Error creating backup for {file_path}: {e}")

class LogWriter:
    def __init__(self, rootfs_dir: str):
        self.rootfs_dir = rootfs_dir
        self.log_file_path = os.path.join(self.rootfs_dir, "fix_cmake_files.log")
        self.modified_files: List[str] = []

    def log_modified_file(self, file_path: str) -> None:
        relative_path = os.path.relpath(file_path, self.rootfs_dir)
        self.modified_files.append(relative_path)

    def write_log(self) -> None:
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"\n--- Run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                for file_path in self.modified_files:
                    log_file.write(f"Modified: {file_path}\n")
            logging.info(f"Log of modified files appended to: {self.log_file_path}")
        except IOError as e:
            logging.error(f"Error writing log file: {e}")

class FixCMakeFilesApp:
    def __init__(self, rootfs_dir: str, backup: bool = True):
        self.rootfs_dir = os.path.abspath(rootfs_dir)
        self.replacer = PathReplacer()
        self.processor = CMakeFileProcessor(self.replacer, backup)
        self.log_writer = LogWriter(self.rootfs_dir)

    def run(self) -> None:
        """Run the CMake file fixing process."""
        for subdir, _, files in os.walk(self.rootfs_dir):
            for file in files:
                if file.endswith(".cmake") or file.endswith(".pc"):
                    file_path = os.path.join(subdir, file)
                    if self.processor.process_file(file_path):
                        self.log_writer.log_modified_file(file_path)
        self.log_writer.write_log()

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fix CMake files in a directory by injecting ${CMAKE_SYSROOT} prefixes where needed."
    )
    parser.add_argument("directory", help="The directory to process")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--no-backup", action="store_true", help="Disable backup creation")
    parser.add_argument("--sysroot", type=str, default="${CMAKE_SYSROOT}",
                        help="Sysroot prefix to use (default: ${CMAKE_SYSROOT})")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    backup = not args.no_backup
    # 根据命令行参数构造 PathReplacer
    replacer = PathReplacer(args.sysroot)
    app = FixCMakeFilesApp(args.directory, backup)
    # 更新App中的replacer实例
    app.replacer = replacer
    app.processor.replacer = replacer
    app.run()

if __name__ == "__main__":
    main()