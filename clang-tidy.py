#! /usr/bin/env python3

import json
import os.path
import subprocess
import sys
from typing import Any

import yaml

CLANG_TIDY_FILE: str = os.path.join(os.path.realpath(os.path.dirname(__file__)), ".clang-tidy")

ALL_CHECKS: str = f"""--config={json.dumps({"Checks": '*'})}"""
CONFIGURED_CHECKS: str = f"--config-file={CLANG_TIDY_FILE}"


def unflatten(check_options: dict[str, Any]) -> dict[str, dict[str, Any]]:
	unflattened: dict[str, dict[str, Any]] = {}

	for key, value in check_options.items():
		check_option: list[str] = key.split('.')
		if len(check_option) != 2:
			raise Exception(f"Unexpected key format '{key}'")

		check: str = check_option[0]
		option: str = check_option[1]

		unflattened.setdefault(check, {})[option] = value

	return unflattened


def clang_tidy_verify() -> None:
	subprocess.call(["clang-tidy", CONFIGURED_CHECKS, "--verify-config"])


def clang_tidy_checks(config: str) -> set[str]:
	return set(yaml.safe_load(subprocess.run(["clang-tidy", config, "--list-checks"], capture_output=True).stdout).get("Enabled checks", "").split(' '))


def clang_tidy_check_options(dump: Any) -> dict[str, dict[str, Any]]:
	return unflatten(yaml.safe_load(dump).get("CheckOptions", {}))


def all_clang_tidy_checks() -> set[str]:
	return clang_tidy_checks(ALL_CHECKS)


def all_clang_tidy_check_options() -> dict[str, dict[str, Any]]:
	return clang_tidy_check_options(subprocess.run(["clang-tidy", ALL_CHECKS, "--dump-config"], capture_output=True).stdout)


def configured_clang_tidy_checks() -> set[str]:
	return clang_tidy_checks(CONFIGURED_CHECKS)


def configured_clang_tidy_check_options() -> dict[str, dict[str, Any]]:
	with open(CLANG_TIDY_FILE, 'r') as configured:
		return clang_tidy_check_options(configured)


def dict_diff(keys: set[str], left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
	diff: dict[str, set[str]] = {}

	for check in keys:
		check_defaults: set[str] = set(left.get(check, [])) - set(right.get(check, []))
		if len(check_defaults) != 0:
			diff[check] = check_defaults

	return {k: sorted(diff[k]) for k in sorted(diff.keys())}


def disabled_checks(all_checks: set[str], configured_checks: set[str]) -> list[str]:
	return sorted(all_checks - configured_checks)


def default_check_options(configured_checks: set[str], all_check_options: dict[str, dict[str, Any]], configured_check_options: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
	defaults: dict[str, set[str]] = {}

	for check in configured_checks:
		check_defaults: set[str] = set(all_check_options.get(check, {}).keys()) - set(configured_check_options.get(check, {}).keys())
		if len(check_defaults) != 0:
			defaults[check] = check_defaults

	return {k: sorted(defaults[k]) for k in sorted(defaults.keys())}


def main() -> int:
	all_checks: set[str] = all_clang_tidy_checks()
	all_check_options: dict[str, dict[str, Any]] = all_clang_tidy_check_options()

	configured_checks: set[str] = configured_clang_tidy_checks()
	configured_check_options: dict[str, dict[str, Any]] = configured_clang_tidy_check_options()

	report: dict[str, Any] = {
		"DisabledChecks": disabled_checks(all_checks, configured_checks),
		"DefaultCheckOptions": default_check_options(configured_checks, all_check_options, configured_check_options),
	}

	print(yaml.dump(report, sort_keys=False))
	clang_tidy_verify()

	return 0


if __name__ == "__main__":
	sys.exit(main())
