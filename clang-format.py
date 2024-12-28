#! /usr/bin/env python3

import os
import subprocess
import sys
from subprocess import CompletedProcess
from typing import Any

import yaml

CLANG_FORMAT_FILE: str = os.path.join(os.path.realpath(os.path.dirname(__file__)), ".clang-format")

ALL_STYLE_OPTIONS: str = "--style=llvm"
CONFIGURED_STYLE_OPTIONS: str = f"--style=file:{CLANG_FORMAT_FILE}"


def clang_format_verify() -> None:
	result: CompletedProcess[bytes] = subprocess.run(["clang-format", CONFIGURED_STYLE_OPTIONS, "--dump-config"], capture_output=True)
	if result.returncode != 0:
		print(result.stderr.decode(), file=sys.stderr)


def all_clang_format_style_options() -> dict[str, Any]:
	return yaml.safe_load(subprocess.run(["clang-format", "--style=llvm", "--dump-config"], capture_output=True).stdout)


def configured_clang_format_style_options() -> dict[str, Any]:
	with open(CLANG_FORMAT_FILE, 'r') as configured:
		return yaml.safe_load(configured)


def recurse_object(options: Any, keys: dict[str, Any]) -> None:
	if isinstance(options, dict):
		for k, v in options.items():
			if isinstance(v, dict) or isinstance(v, list):
				recurse_object(v, keys.setdefault(k, {}))
			else:
				keys[k] = True
	elif isinstance(options, list):
		for option in options:
			if isinstance(option, dict) or isinstance(option, list):
				recurse_object(option, keys)


def flatten(options: list[Any]) -> dict[str, Any] | None:
	keys: dict[str, Any] = {}
	recurse_object(options, keys)
	return keys


def recurse_options(all_options: dict[str, Any], configured_options: dict[str, Any], default: list[Any]) -> bool:
	modified: bool = False

	for key in sorted(all_options.keys()):
		all_value: Any = all_options[key]
		configured_value: Any = None if configured_options is None else configured_options.get(key, None)
		if configured_value is not None and type(all_value) != type(configured_value):
			continue
		elif isinstance(all_value, dict):
			element: list[Any] = []
			if recurse_options(all_value, configured_value, element):
				default.append({key: element})
				modified = True
		elif isinstance(all_value, list):
			element: list[Any] = []
			if recurse_options(flatten(all_value), flatten(configured_value), element):
				default.append({key: element})
				modified = True
		elif configured_value is None:
			default.append(key)
			modified = True

	return modified


def default_style_options(all_style_options: dict[str, Any], configured_style_options: dict[str, Any]) -> list[Any]:
	defaults: list[Any] = []
	recurse_options(all_style_options, configured_style_options, defaults)
	return defaults


def main() -> int:
	all_style_options: dict[str, Any] = all_clang_format_style_options()
	configured_style_options: dict[str, Any] = configured_clang_format_style_options()

	print(yaml.dump({"DefaultStyleOptions": default_style_options(all_style_options, configured_style_options)}, sort_keys=False))
	clang_format_verify()

	return 0


if __name__ == "__main__":
	sys.exit(main())
